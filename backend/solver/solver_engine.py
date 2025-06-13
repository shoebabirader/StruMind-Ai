"""
Main solver engine and analysis manager
"""

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio
from datetime import datetime

from db.models.structural import Node, Element, Material, Section, Load, LoadCase, BoundaryCondition
from db.models.analysis import AnalysisCase, AnalysisType, AnalysisStatus
from core.exceptions import AnalysisError, ComputationError
from .linear import LinearStaticAnalysis
from .dynamic import DynamicSolver
from .nonlinear import NonlinearStaticAnalysis
from .buckling import BucklingAnalysis


class SolverEngine:
    """Main structural analysis solver engine"""
    
    def __init__(self):
        self.linear_solver = LinearStaticAnalysis()
        self.dynamic_solver = DynamicSolver()
        self.nonlinear_solver = NonlinearStaticAnalysis()
        self.buckling_solver = BucklingAnalysis()
        self.active_analyses = {}
    
    async def run_analysis(self, analysis_case: AnalysisCase,
                          structural_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run structural analysis based on analysis type"""
        try:
            # Update analysis status
            analysis_case.status = AnalysisStatus.RUNNING
            analysis_case.started_at = datetime.utcnow()
            
            # Extract structural data
            nodes = structural_data['nodes']
            elements = structural_data['elements']
            materials = structural_data['materials']
            sections = structural_data['sections']
            loads = structural_data.get('loads', [])
            boundary_conditions = structural_data.get('boundary_conditions', [])
            
            # Route to appropriate solver
            if analysis_case.analysis_type == AnalysisType.LINEAR_STATIC:
                results = self.linear_solver.run_analysis(
                    analysis_case, nodes, elements, materials, sections,
                    loads, boundary_conditions
                )
            
            elif analysis_case.analysis_type == AnalysisType.MODAL:
                results = self.dynamic_solver.run_analysis(
                    'modal', analysis_case, nodes, elements, materials, sections,
                    boundary_conditions, **analysis_case.parameters
                )
            
            elif analysis_case.analysis_type == AnalysisType.RESPONSE_SPECTRUM:
                results = self.dynamic_solver.run_analysis(
                    'response_spectrum', analysis_case, nodes, elements, materials, sections,
                    boundary_conditions, **analysis_case.parameters
                )
            
            elif analysis_case.analysis_type == AnalysisType.TIME_HISTORY:
                results = self.dynamic_solver.run_analysis(
                    'time_history', analysis_case, nodes, elements, materials, sections,
                    boundary_conditions, **analysis_case.parameters
                )
            
            elif analysis_case.analysis_type == AnalysisType.NONLINEAR_STATIC:
                results = self.nonlinear_solver.run_analysis(
                    analysis_case, nodes, elements, materials, sections,
                    loads, boundary_conditions
                )
            
            elif analysis_case.analysis_type == AnalysisType.BUCKLING:
                results = self.buckling_solver.run_analysis(
                    analysis_case, nodes, elements, materials, sections,
                    loads, boundary_conditions
                )
            
            else:
                raise AnalysisError(f"Unsupported analysis type: {analysis_case.analysis_type}")
            
            # Update analysis status
            analysis_case.status = AnalysisStatus.COMPLETED
            analysis_case.completed_at = datetime.utcnow()
            analysis_case.execution_time_seconds = (
                analysis_case.completed_at - analysis_case.started_at
            ).total_seconds()
            
            return results
            
        except Exception as e:
            analysis_case.status = AnalysisStatus.FAILED
            analysis_case.error_message = str(e)
            analysis_case.completed_at = datetime.utcnow()
            raise AnalysisError(f"Analysis failed: {str(e)}")


class AnalysisManager:
    """Manager for multiple analysis cases and batch processing"""
    
    def __init__(self):
        self.solver_engine = SolverEngine()
        self.analysis_queue = []
        self.completed_analyses = {}
        self.failed_analyses = {}
    
    def add_analysis(self, analysis_case: AnalysisCase, structural_data: Dict[str, Any]):
        """Add analysis to queue"""
        self.analysis_queue.append({
            'analysis_case': analysis_case,
            'structural_data': structural_data
        })
    
    async def run_all_analyses(self) -> Dict[str, Any]:
        """Run all queued analyses"""
        results = {}
        
        for analysis_item in self.analysis_queue:
            analysis_case = analysis_item['analysis_case']
            structural_data = analysis_item['structural_data']
            
            try:
                result = await self.solver_engine.run_analysis(analysis_case, structural_data)
                results[analysis_case.id] = result
                self.completed_analyses[analysis_case.id] = result
                
            except Exception as e:
                self.failed_analyses[analysis_case.id] = str(e)
                results[analysis_case.id] = {'error': str(e)}
        
        # Clear queue after processing
        self.analysis_queue.clear()
        
        return results
    
    def get_analysis_status(self, analysis_case_id: uuid.UUID) -> Optional[str]:
        """Get status of specific analysis"""
        if analysis_case_id in self.completed_analyses:
            return "completed"
        elif analysis_case_id in self.failed_analyses:
            return "failed"
        else:
            return "pending"
    
    def get_analysis_results(self, analysis_case_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get results of completed analysis"""
        return self.completed_analyses.get(analysis_case_id)
    
    def clear_results(self):
        """Clear all stored results"""
        self.completed_analyses.clear()
        self.failed_analyses.clear()
        self.analysis_queue.clear()