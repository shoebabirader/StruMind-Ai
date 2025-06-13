"""
Celery tasks for structural analysis
"""

from celery import Celery
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
from datetime import datetime
import traceback

from db.database import SessionLocal
from db.models.analysis import Analysis, AnalysisStatus, AnalysisType
from db.models.structural import Node, Element, Material, Section, Load, BoundaryCondition
from solver.solver_engine import SolverEngine
from solver.linear import LinearStaticSolver
from solver.dynamic import ModalAnalysisSolver
from solver.buckling import BucklingAnalysisSolver
from solver.nonlinear import NonlinearStaticSolver
from core.exceptions import AnalysisError

# Import Celery app
from tasks.celery_app import celery_app


@celery_app.task(bind=True)
def run_analysis_task(self, analysis_id: str) -> Dict[str, Any]:
    """
    Background task to run structural analysis
    """
    db = SessionLocal()
    
    try:
        # Get analysis record
        analysis = db.query(Analysis).filter(Analysis.id == uuid.UUID(analysis_id)).first()
        if not analysis:
            raise AnalysisError(f"Analysis {analysis_id} not found")
        
        # Update status to running
        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.utcnow()
        analysis.progress = 0.0
        db.commit()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading model data'})
        
        # Load model data
        nodes = db.query(Node).filter(Node.project_id == analysis.project_id).all()
        elements = db.query(Element).filter(Element.project_id == analysis.project_id).all()
        materials = db.query(Material).filter(Material.project_id == analysis.project_id).all()
        sections = db.query(Section).filter(Section.project_id == analysis.project_id).all()
        loads = db.query(Load).filter(Load.project_id == analysis.project_id).all()
        boundary_conditions = db.query(BoundaryCondition).filter(
            BoundaryCondition.project_id == analysis.project_id
        ).all()
        
        if not nodes or not elements:
            raise AnalysisError("Model must have nodes and elements")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Initializing solver'})
        
        # Initialize solver based on analysis type
        if analysis.analysis_type == AnalysisType.LINEAR_STATIC:
            solver = LinearStaticSolver()
        elif analysis.analysis_type == AnalysisType.MODAL:
            solver = ModalAnalysisSolver()
        elif analysis.analysis_type == AnalysisType.BUCKLING:
            solver = BucklingAnalysisSolver()
        elif analysis.analysis_type == AnalysisType.NONLINEAR_STATIC:
            solver = NonlinearStaticSolver()
        else:
            raise AnalysisError(f"Unsupported analysis type: {analysis.analysis_type}")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Building model'})
        
        # Build solver model
        solver_model = _build_solver_model(nodes, elements, materials, sections, loads, boundary_conditions)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Running analysis'})
        
        # Run analysis
        results = solver.solve(solver_model, analysis.parameters)
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Processing results'})
        
        # Process and store results
        processed_results = _process_analysis_results(results, analysis.analysis_type)
        
        # Update analysis record
        analysis.status = AnalysisStatus.COMPLETED
        analysis.completed_at = datetime.utcnow()
        analysis.progress = 100.0
        analysis.results = processed_results
        analysis.error_message = None
        
        db.commit()
        
        return {
            'status': 'completed',
            'analysis_id': analysis_id,
            'results_summary': _create_results_summary(processed_results, analysis.analysis_type)
        }
        
    except Exception as e:
        # Update analysis record with error
        analysis.status = AnalysisStatus.FAILED
        analysis.completed_at = datetime.utcnow()
        analysis.error_message = str(e)
        analysis.progress = 0.0
        
        db.commit()
        
        # Log error
        error_trace = traceback.format_exc()
        print(f"Analysis {analysis_id} failed: {error_trace}")
        
        return {
            'status': 'failed',
            'analysis_id': analysis_id,
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def run_batch_analysis(project_id: str, analysis_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run multiple analyses in batch
    """
    db = SessionLocal()
    results = []
    
    try:
        for config in analysis_configs:
            # Create analysis record
            analysis = Analysis(
                analysis_type=AnalysisType(config['analysis_type']),
                status=AnalysisStatus.PENDING,
                parameters=config.get('parameters', {}),
                load_combinations=config.get('load_combinations', []),
                description=config.get('description'),
                progress=0.0,
                project_id=uuid.UUID(project_id)
            )
            
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            
            # Queue individual analysis
            task = run_analysis_task.delay(str(analysis.id))
            
            results.append({
                'analysis_id': str(analysis.id),
                'task_id': task.id,
                'analysis_type': config['analysis_type']
            })
        
        return {
            'status': 'queued',
            'batch_size': len(analysis_configs),
            'analyses': results
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def cleanup_old_analyses(days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old analysis results
    """
    db = SessionLocal()
    
    try:
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Find old analyses
        old_analyses = db.query(Analysis).filter(
            Analysis.created_at < cutoff_date,
            Analysis.status.in_([AnalysisStatus.COMPLETED, AnalysisStatus.FAILED])
        ).all()
        
        deleted_count = 0
        for analysis in old_analyses:
            db.delete(analysis)
            deleted_count += 1
        
        db.commit()
        
        return {
            'status': 'completed',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }
        
    finally:
        db.close()


def _build_solver_model(nodes: List[Node], elements: List[Element], materials: List[Material],
                       sections: List[Section], loads: List[Load], 
                       boundary_conditions: List[BoundaryCondition]) -> Dict[str, Any]:
    """
    Build solver model from database entities
    """
    # Create lookups
    material_lookup = {mat.id: mat for mat in materials}
    section_lookup = {sec.id: sec for sec in sections}
    
    # Convert nodes
    solver_nodes = []
    for node in nodes:
        solver_nodes.append({
            'id': str(node.id),
            'coordinates': [node.x, node.y, node.z],
            'label': node.label
        })
    
    # Convert elements
    solver_elements = []
    for element in elements:
        material = material_lookup.get(element.material_id)
        section = section_lookup.get(element.section_id)
        
        solver_elements.append({
            'id': str(element.id),
            'type': element.element_type,
            'nodes': [str(element.start_node_id), str(element.end_node_id)] if element.end_node_id else [str(element.start_node_id)],
            'material': material.properties if material else {},
            'section': section.properties if section else {},
            'orientation_angle': element.orientation_angle,
            'properties': element.properties or {},
            'label': element.label
        })
    
    # Convert loads
    solver_loads = []
    for load in loads:
        solver_loads.append({
            'id': str(load.id),
            'type': load.load_type,
            'case': load.load_case,
            'values': load.values,
            'node_id': str(load.node_id) if load.node_id else None,
            'element_id': str(load.element_id) if load.element_id else None
        })
    
    # Convert boundary conditions
    solver_bcs = []
    for bc in boundary_conditions:
        solver_bcs.append({
            'id': str(bc.id),
            'node_id': str(bc.node_id),
            'support_type': bc.support_type,
            'restraints': bc.restraints
        })
    
    return {
        'nodes': solver_nodes,
        'elements': solver_elements,
        'loads': solver_loads,
        'boundary_conditions': solver_bcs,
        'materials': [mat.properties for mat in materials],
        'sections': [sec.properties for sec in sections]
    }


def _process_analysis_results(raw_results: Dict[str, Any], analysis_type: AnalysisType) -> Dict[str, Any]:
    """
    Process raw solver results into standardized format
    """
    processed = {
        'analysis_type': analysis_type.value,
        'timestamp': datetime.utcnow().isoformat(),
        'units': {
            'length': 'm',
            'force': 'N',
            'moment': 'N-m',
            'stress': 'Pa',
            'frequency': 'Hz'
        }
    }
    
    if analysis_type == AnalysisType.LINEAR_STATIC:
        processed.update({
            'displacements': raw_results.get('displacements', {}),
            'reactions': raw_results.get('reactions', {}),
            'element_forces': raw_results.get('element_forces', {}),
            'stresses': raw_results.get('stresses', {}),
            'max_displacement': raw_results.get('max_displacement', 0.0),
            'max_stress': raw_results.get('max_stress', 0.0)
        })
    
    elif analysis_type == AnalysisType.MODAL:
        processed.update({
            'frequencies': raw_results.get('frequencies', []),
            'mode_shapes': raw_results.get('mode_shapes', {}),
            'mass_participation': raw_results.get('mass_participation', {}),
            'modal_mass': raw_results.get('modal_mass', {}),
            'num_modes': len(raw_results.get('frequencies', []))
        })
    
    elif analysis_type == AnalysisType.BUCKLING:
        processed.update({
            'buckling_factors': raw_results.get('buckling_factors', []),
            'buckling_modes': raw_results.get('buckling_modes', {}),
            'critical_load_factor': min(raw_results.get('buckling_factors', [1.0]))
        })
    
    elif analysis_type == AnalysisType.NONLINEAR_STATIC:
        processed.update({
            'load_steps': raw_results.get('load_steps', []),
            'displacement_history': raw_results.get('displacement_history', {}),
            'force_history': raw_results.get('force_history', {}),
            'convergence_info': raw_results.get('convergence_info', {}),
            'final_displacements': raw_results.get('final_displacements', {}),
            'plastic_hinges': raw_results.get('plastic_hinges', [])
        })
    
    return processed


def _create_results_summary(results: Dict[str, Any], analysis_type: AnalysisType) -> Dict[str, Any]:
    """
    Create summary of analysis results
    """
    summary = {
        'analysis_type': analysis_type.value,
        'completed_at': results.get('timestamp'),
        'units': results.get('units', {})
    }
    
    if analysis_type == AnalysisType.LINEAR_STATIC:
        summary.update({
            'max_displacement': results.get('max_displacement', 0.0),
            'max_stress': results.get('max_stress', 0.0),
            'num_load_cases': len(results.get('displacements', {})),
            'status': 'completed'
        })
    
    elif analysis_type == AnalysisType.MODAL:
        frequencies = results.get('frequencies', [])
        summary.update({
            'num_modes': len(frequencies),
            'fundamental_frequency': min(frequencies) if frequencies else 0.0,
            'highest_frequency': max(frequencies) if frequencies else 0.0,
            'total_mass_participation': sum(results.get('mass_participation', {}).values()),
            'status': 'completed'
        })
    
    elif analysis_type == AnalysisType.BUCKLING:
        factors = results.get('buckling_factors', [])
        summary.update({
            'num_modes': len(factors),
            'critical_load_factor': min(factors) if factors else 1.0,
            'safety_factor': min(factors) if factors else 1.0,
            'status': 'completed' if factors else 'failed'
        })
    
    elif analysis_type == AnalysisType.NONLINEAR_STATIC:
        summary.update({
            'num_load_steps': len(results.get('load_steps', [])),
            'convergence_achieved': results.get('convergence_info', {}).get('converged', False),
            'final_load_factor': results.get('load_steps', [])[-1] if results.get('load_steps') else 0.0,
            'plastic_hinges_formed': len(results.get('plastic_hinges', [])),
            'status': 'completed'
        })
    
    return summary


@celery_app.task
def validate_model_for_analysis(project_id: str, analysis_type: str) -> Dict[str, Any]:
    """
    Validate model before running analysis
    """
    db = SessionLocal()
    
    try:
        # Load model data
        nodes = db.query(Node).filter(Node.project_id == uuid.UUID(project_id)).all()
        elements = db.query(Element).filter(Element.project_id == uuid.UUID(project_id)).all()
        boundary_conditions = db.query(BoundaryCondition).filter(
            BoundaryCondition.project_id == uuid.UUID(project_id)
        ).all()
        
        errors = []
        warnings = []
        
        # Basic model validation
        if not nodes:
            errors.append("Model has no nodes")
        
        if not elements:
            errors.append("Model has no elements")
        
        if not boundary_conditions:
            errors.append("Model has no boundary conditions")
        
        # Check element connectivity
        node_ids = {node.id for node in nodes}
        for element in elements:
            if element.start_node_id not in node_ids:
                errors.append(f"Element {element.id} references non-existent start node")
            
            if element.end_node_id and element.end_node_id not in node_ids:
                errors.append(f"Element {element.id} references non-existent end node")
        
        # Check boundary conditions
        bc_node_ids = {bc.node_id for bc in boundary_conditions}
        if not bc_node_ids.intersection(node_ids):
            errors.append("No valid boundary conditions found")
        
        # Analysis-specific validation
        if analysis_type == AnalysisType.MODAL.value:
            # Check for mass
            has_mass = any(
                element.properties and element.properties.get('mass_per_length', 0) > 0
                for element in elements
            )
            if not has_mass:
                warnings.append("No mass defined - modal analysis may not be meaningful")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'model_stats': {
                'num_nodes': len(nodes),
                'num_elements': len(elements),
                'num_boundary_conditions': len(boundary_conditions)
            }
        }
        
    except Exception as e:
        return {
            'valid': False,
            'errors': [f"Validation failed: {str(e)}"],
            'warnings': [],
            'model_stats': {}
        }
        
    finally:
        db.close()