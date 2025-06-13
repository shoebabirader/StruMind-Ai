"""
Analysis API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from db.database import get_db
from db.models.analysis import AnalysisCase, AnalysisType, AnalysisStatus
from db.models.project import Project
from solver.solver_engine import SolverEngine, AnalysisManager
from core.auth import get_current_user
from core.exceptions import AnalysisError

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run/{project_id}")
async def run_analysis(
    project_id: uuid.UUID,
    analysis_type: AnalysisType,
    parameters: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Run structural analysis"""
    try:
        # Get project and verify access
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Create analysis case
        analysis_case = AnalysisCase(
            name=f"{analysis_type.value}_analysis",
            analysis_type=analysis_type,
            parameters=parameters,
            project_id=project_id,
            created_by_id=current_user.id
        )
        db.add(analysis_case)
        db.commit()
        db.refresh(analysis_case)
        
        # Add to background task queue
        background_tasks.add_task(
            run_analysis_task,
            analysis_case.id,
            project_id
        )
        
        return {
            "analysis_id": analysis_case.id,
            "status": "queued",
            "message": "Analysis started successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{analysis_id}")
async def get_analysis_status(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get analysis status"""
    analysis = db.query(AnalysisCase).filter(AnalysisCase.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "analysis_id": analysis_id,
        "status": analysis.status,
        "progress": analysis.progress_percentage,
        "started_at": analysis.started_at,
        "completed_at": analysis.completed_at,
        "error_message": analysis.error_message
    }


@router.get("/results/{analysis_id}")
async def get_analysis_results(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get analysis results"""
    analysis = db.query(AnalysisCase).filter(AnalysisCase.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis not completed")
    
    # Get results from analysis manager
    analysis_manager = AnalysisManager()
    results = analysis_manager.get_analysis_results(analysis_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    
    return {
        "analysis_id": analysis_id,
        "analysis_type": analysis.analysis_type,
        "results": results,
        "completed_at": analysis.completed_at
    }


async def run_analysis_task(analysis_id: uuid.UUID, project_id: uuid.UUID):
    """Background task to run analysis"""
    try:
        # Initialize solver engine
        solver_engine = SolverEngine()
        
        # Get structural data (simplified)
        structural_data = {
            "nodes": [],
            "elements": [],
            "materials": {},
            "sections": {},
            "loads": [],
            "boundary_conditions": []
        }
        
        # Run analysis
        results = await solver_engine.run_analysis(analysis_id, structural_data)
        
        return results
        
    except Exception as e:
        # Update analysis status to failed
        pass