"""
Celery tasks for structural design
"""

from celery import Celery
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
from datetime import datetime
import traceback

from db.database import SessionLocal
from db.models.design import DesignResult, DesignStatus, DesignCode
from db.models.structural import Element, Material, Section
from db.models.analysis import Analysis, AnalysisStatus
from design.concrete import ConcreteDesigner
from core.exceptions import DesignError

# Import Celery app
from tasks.celery_app import celery_app


@celery_app.task(bind=True)
def run_design_task(self, project_id: str, element_ids: List[str], design_code: str,
                   analysis_id: str = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Background task to run structural design
    """
    db = SessionLocal()
    
    try:
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading design data'})
        
        # Load elements
        elements = db.query(Element).filter(
            Element.id.in_([uuid.UUID(eid) for eid in element_ids]),
            Element.project_id == uuid.UUID(project_id)
        ).all()
        
        if not elements:
            raise DesignError("No elements found for design")
        
        # Load analysis results if provided
        analysis_results = None
        if analysis_id:
            analysis = db.query(Analysis).filter(Analysis.id == uuid.UUID(analysis_id)).first()
            if analysis and analysis.status == AnalysisStatus.COMPLETED:
                analysis_results = analysis.results
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 20, 'status': 'Initializing designer'})
        
        # Initialize designer based on design code
        if design_code in ["ACI_318", "IS_456", "EUROCODE_2"]:
            designer = ConcreteDesigner(design_code)
        else:
            raise DesignError(f"Unsupported design code: {design_code}")
        
        design_results = []
        total_elements = len(elements)
        
        # Design each element
        for i, element in enumerate(elements):
            try:
                # Update progress
                progress = 30 + (i / total_elements) * 60
                self.update_state(state='PROGRESS', meta={
                    'progress': progress,
                    'status': f'Designing element {i+1}/{total_elements}'
                })
                
                # Get element forces from analysis results
                element_forces = _extract_element_forces(element, analysis_results)
                
                # Run design
                design_result = designer.design_element(element, element_forces, parameters or {})
                
                # Create design result record
                db_result = DesignResult(
                    element_id=element.id,
                    design_code=DesignCode(design_code),
                    status=DesignStatus.COMPLETED if design_result['status'] == 'passed' else DesignStatus.FAILED,
                    results=design_result,
                    recommendations=design_result.get('recommendations', []),
                    warnings=design_result.get('warnings', []),
                    errors=design_result.get('errors', []),
                    utilization_ratio=design_result.get('utilization_ratio', 0.0),
                    project_id=uuid.UUID(project_id)
                )
                
                db.add(db_result)
                design_results.append({
                    'element_id': str(element.id),
                    'status': design_result['status'],
                    'utilization_ratio': design_result.get('utilization_ratio', 0.0),
                    'design_result_id': str(db_result.id)
                })
                
            except Exception as e:
                # Create failed design result
                db_result = DesignResult(
                    element_id=element.id,
                    design_code=DesignCode(design_code),
                    status=DesignStatus.FAILED,
                    results={},
                    errors=[str(e)],
                    utilization_ratio=0.0,
                    project_id=uuid.UUID(project_id)
                )
                
                db.add(db_result)
                design_results.append({
                    'element_id': str(element.id),
                    'status': 'failed',
                    'error': str(e),
                    'design_result_id': str(db_result.id)
                })
        
        db.commit()
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 100, 'status': 'Design completed'})
        
        # Create summary
        passed_count = sum(1 for r in design_results if r['status'] == 'passed')
        failed_count = len(design_results) - passed_count
        max_utilization = max((r.get('utilization_ratio', 0.0) for r in design_results), default=0.0)
        
        return {
            'status': 'completed',
            'project_id': project_id,
            'design_code': design_code,
            'total_elements': len(design_results),
            'passed_elements': passed_count,
            'failed_elements': failed_count,
            'max_utilization': max_utilization,
            'results': design_results
        }
        
    except Exception as e:
        # Log error
        error_trace = traceback.format_exc()
        print(f"Design task failed: {error_trace}")
        
        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def run_batch_design(project_id: str, design_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run multiple design configurations in batch
    """
    results = []
    
    try:
        for config in design_configs:
            # Queue individual design task
            task = run_design_task.delay(
                project_id=project_id,
                element_ids=config['element_ids'],
                design_code=config['design_code'],
                analysis_id=config.get('analysis_id'),
                parameters=config.get('parameters', {})
            )
            
            results.append({
                'task_id': task.id,
                'design_code': config['design_code'],
                'element_count': len(config['element_ids'])
            })
        
        return {
            'status': 'queued',
            'batch_size': len(design_configs),
            'tasks': results
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }


@celery_app.task
def optimize_design(project_id: str, element_ids: List[str], design_code: str,
                   optimization_parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize structural design for given elements
    """
    db = SessionLocal()
    
    try:
        # Load elements
        elements = db.query(Element).filter(
            Element.id.in_([uuid.UUID(eid) for eid in element_ids]),
            Element.project_id == uuid.UUID(project_id)
        ).all()
        
        if not elements:
            raise DesignError("No elements found for optimization")
        
        # Initialize designer
        if design_code in ["ACI_318", "IS_456", "EUROCODE_2"]:
            designer = ConcreteDesigner(design_code)
        else:
            raise DesignError(f"Unsupported design code: {design_code}")
        
        optimization_results = []
        
        for element in elements:
            # Run optimization for each element
            result = designer.optimize_element(element, optimization_parameters)
            optimization_results.append({
                'element_id': str(element.id),
                'original_section': result.get('original_section'),
                'optimized_section': result.get('optimized_section'),
                'cost_savings': result.get('cost_savings', 0.0),
                'weight_savings': result.get('weight_savings', 0.0),
                'utilization_improvement': result.get('utilization_improvement', 0.0)
            })
        
        return {
            'status': 'completed',
            'project_id': project_id,
            'optimization_results': optimization_results,
            'total_cost_savings': sum(r['cost_savings'] for r in optimization_results),
            'total_weight_savings': sum(r['weight_savings'] for r in optimization_results)
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def generate_design_report(project_id: str, design_result_ids: List[str],
                          report_format: str = "pdf") -> Dict[str, Any]:
    """
    Generate design report for specified design results
    """
    db = SessionLocal()
    
    try:
        # Load design results
        design_results = db.query(DesignResult).filter(
            DesignResult.id.in_([uuid.UUID(rid) for rid in design_result_ids]),
            DesignResult.project_id == uuid.UUID(project_id)
        ).all()
        
        if not design_results:
            raise DesignError("No design results found for report")
        
        # Generate report content
        report_data = _generate_report_content(design_results)
        
        # Format report based on requested format
        if report_format == "pdf":
            report_file = _generate_pdf_report(report_data)
        elif report_format == "html":
            report_file = _generate_html_report(report_data)
        elif report_format == "json":
            report_file = _generate_json_report(report_data)
        else:
            raise DesignError(f"Unsupported report format: {report_format}")
        
        return {
            'status': 'completed',
            'project_id': project_id,
            'report_format': report_format,
            'report_file': report_file,
            'design_results_count': len(design_results)
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }
        
    finally:
        db.close()


@celery_app.task
def validate_design_codes(project_id: str, element_ids: List[str]) -> Dict[str, Any]:
    """
    Validate elements against multiple design codes
    """
    db = SessionLocal()
    
    try:
        # Load elements
        elements = db.query(Element).filter(
            Element.id.in_([uuid.UUID(eid) for eid in element_ids]),
            Element.project_id == uuid.UUID(project_id)
        ).all()
        
        if not elements:
            raise DesignError("No elements found for validation")
        
        # Design codes to validate against
        design_codes = ["ACI_318", "IS_456", "EUROCODE_2"]
        validation_results = {}
        
        for code in design_codes:
            try:
                designer = ConcreteDesigner(code)
                code_results = []
                
                for element in elements:
                    # Quick validation check
                    validation = designer.validate_element(element)
                    code_results.append({
                        'element_id': str(element.id),
                        'valid': validation['valid'],
                        'issues': validation.get('issues', [])
                    })
                
                validation_results[code] = {
                    'status': 'completed',
                    'results': code_results,
                    'valid_elements': sum(1 for r in code_results if r['valid']),
                    'total_elements': len(code_results)
                }
                
            except Exception as e:
                validation_results[code] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        return {
            'status': 'completed',
            'project_id': project_id,
            'validation_results': validation_results
        }
        
    except Exception as e:
        return {
            'status': 'failed',
            'error': str(e)
        }
        
    finally:
        db.close()


def _extract_element_forces(element: Element, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract element forces from analysis results
    """
    if not analysis_results:
        # Return default forces for design
        return {
            'axial': 100000.0,  # N
            'shear_y': 50000.0,  # N
            'shear_z': 30000.0,  # N
            'moment_y': 150000.0,  # N-m
            'moment_z': 200000.0,  # N-m
            'torsion': 25000.0   # N-m
        }
    
    # Extract forces for this element from analysis results
    element_forces = analysis_results.get('element_forces', {})
    element_id = str(element.id)
    
    if element_id in element_forces:
        return element_forces[element_id]
    
    # Return average forces if specific element not found
    all_forces = list(element_forces.values())
    if all_forces:
        return {
            'axial': sum(f.get('axial', 0) for f in all_forces) / len(all_forces),
            'shear_y': sum(f.get('shear_y', 0) for f in all_forces) / len(all_forces),
            'shear_z': sum(f.get('shear_z', 0) for f in all_forces) / len(all_forces),
            'moment_y': sum(f.get('moment_y', 0) for f in all_forces) / len(all_forces),
            'moment_z': sum(f.get('moment_z', 0) for f in all_forces) / len(all_forces),
            'torsion': sum(f.get('torsion', 0) for f in all_forces) / len(all_forces)
        }
    
    # Default forces
    return {
        'axial': 100000.0,
        'shear_y': 50000.0,
        'shear_z': 30000.0,
        'moment_y': 150000.0,
        'moment_z': 200000.0,
        'torsion': 25000.0
    }


def _generate_report_content(design_results: List[DesignResult]) -> Dict[str, Any]:
    """
    Generate report content from design results
    """
    # Calculate summary statistics
    total_elements = len(design_results)
    passed_elements = sum(1 for r in design_results if r.status == DesignStatus.PASSED)
    failed_elements = total_elements - passed_elements
    
    utilizations = [r.utilization_ratio for r in design_results if r.utilization_ratio is not None]
    max_utilization = max(utilizations) if utilizations else 0.0
    avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0.0
    
    # Group by design code
    code_summary = {}
    for result in design_results:
        code = result.design_code.value
        if code not in code_summary:
            code_summary[code] = {'total': 0, 'passed': 0, 'failed': 0}
        
        code_summary[code]['total'] += 1
        if result.status == DesignStatus.PASSED:
            code_summary[code]['passed'] += 1
        else:
            code_summary[code]['failed'] += 1
    
    return {
        'summary': {
            'total_elements': total_elements,
            'passed_elements': passed_elements,
            'failed_elements': failed_elements,
            'pass_rate': passed_elements / total_elements if total_elements > 0 else 0.0,
            'max_utilization': max_utilization,
            'avg_utilization': avg_utilization
        },
        'code_summary': code_summary,
        'detailed_results': [
            {
                'element_id': str(r.element_id),
                'design_code': r.design_code.value,
                'status': r.status.value,
                'utilization_ratio': r.utilization_ratio,
                'recommendations': r.recommendations,
                'warnings': r.warnings,
                'errors': r.errors,
                'results': r.results
            }
            for r in design_results
        ],
        'generated_at': datetime.utcnow().isoformat()
    }


def _generate_pdf_report(report_data: Dict[str, Any]) -> str:
    """
    Generate PDF report (simplified implementation)
    """
    # In a real implementation, this would use a PDF library like ReportLab
    # For now, return a placeholder
    return f"design_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"


def _generate_html_report(report_data: Dict[str, Any]) -> str:
    """
    Generate HTML report
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Structural Design Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .summary {{ background: #f5f5f5; padding: 15px; margin-bottom: 20px; }}
            .result {{ border: 1px solid #ddd; margin: 10px 0; padding: 10px; }}
            .passed {{ border-left: 5px solid green; }}
            .failed {{ border-left: 5px solid red; }}
        </style>
    </head>
    <body>
        <h1>Structural Design Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Elements: {report_data['summary']['total_elements']}</p>
            <p>Passed: {report_data['summary']['passed_elements']}</p>
            <p>Failed: {report_data['summary']['failed_elements']}</p>
            <p>Pass Rate: {report_data['summary']['pass_rate']:.1%}</p>
            <p>Max Utilization: {report_data['summary']['max_utilization']:.2f}</p>
        </div>
        
        <h2>Detailed Results</h2>
    """
    
    for result in report_data['detailed_results']:
        status_class = 'passed' if result['status'] == 'PASSED' else 'failed'
        html_content += f"""
        <div class="result {status_class}">
            <h3>Element {result['element_id']}</h3>
            <p>Design Code: {result['design_code']}</p>
            <p>Status: {result['status']}</p>
            <p>Utilization: {result['utilization_ratio']:.2f}</p>
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    filename = f"design_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, 'w') as f:
        f.write(html_content)
    
    return filename


def _generate_json_report(report_data: Dict[str, Any]) -> str:
    """
    Generate JSON report
    """
    import json
    
    filename = f"design_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    return filename