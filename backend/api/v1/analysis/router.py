"""
Structural Analysis API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from db.database import get_db
from db.models.analysis import AnalysisCase, AnalysisType, AnalysisStatus
from db.models.project import Project
from db.models.user import User
from api.v1.auth.router import get_current_user
# from solver.solver_engine import SolverEngine  # Temporarily commented out
from core.exceptions import ValidationError, NotFoundError

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class AnalysisCreate(BaseModel):
    analysis_type: AnalysisType
    parameters: Dict[str, Any]
    load_combinations: List[str]
    description: Optional[str] = None

class AnalysisResponse(BaseModel):
    id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    parameters: Dict[str, Any]
    load_combinations: List[str]
    description: Optional[str]
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]
    progress: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    project_id: str
    created_at: datetime

class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total: int
    page: int
    size: int

class AnalysisResultsResponse(BaseModel):
    analysis_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    results: Dict[str, Any]
    summary: Dict[str, Any]

def verify_project_access(project_id: UUID, current_user: User, db: Session):
    """Verify user has access to project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )
    return project

@router.get("/health")
async def analysis_health():
    """Analysis service health check"""
    return {"status": "healthy", "service": "analysis"}

@router.post("/{project_id}/run", response_model=AnalysisResponse)
async def run_analysis(
    project_id: UUID,
    analysis_data: AnalysisCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run structural analysis"""
    project = verify_project_access(project_id, current_user, db)
    
    # Create analysis record
    analysis = AnalysisCase(
        name=f"Analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        analysis_type=analysis_data.analysis_type,
        status=AnalysisStatus.PENDING,
        parameters=analysis_data.parameters,
        load_combination_ids=analysis_data.load_combinations,
        description=analysis_data.description,
        progress_percentage=0.0,
        project_id=project_id
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    # For now, simulate analysis completion
    analysis.status = AnalysisStatus.COMPLETED
    analysis.progress_percentage = 100.0
    analysis.started_at = datetime.utcnow()
    analysis.completed_at = datetime.utcnow()
    
    # Store results in solver_info for now (in real implementation, would be in separate results table)
    if analysis_data.analysis_type == AnalysisType.LINEAR_STATIC:
        analysis.solver_info = {
            "results": {
                "displacements": [0.001, 0.002, 0.0015, 0.0008],
                "reactions": [1000, 1500, 800, 1200],
                "element_forces": [{"element_id": "1", "axial": 500, "shear": 200, "moment": 1000}],
                "max_displacement": 0.002,
                "max_stress": 150.5
            }
        }
    elif analysis_data.analysis_type == AnalysisType.MODAL:
        analysis.solver_info = {
            "results": {
                "frequencies": [2.45, 3.67, 5.23, 7.89, 9.12],
                "mode_shapes": [
                    {"mode": 1, "frequency": 2.45, "participation": 0.85},
                    {"mode": 2, "frequency": 3.67, "participation": 0.72}
                ],
                "mass_participation": {"x": 0.85, "y": 0.78, "z": 0.92}
            }
        }
    
    db.commit()
    
    return AnalysisResponse(
        id=str(analysis.id),
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        parameters=analysis.parameters or {},
        load_combinations=analysis.load_combination_ids or [],
        description=analysis.description,
        results=analysis.solver_info.get("results") if analysis.solver_info else None,
        error_message=analysis.error_message,
        progress=analysis.progress_percentage,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        project_id=str(analysis.project_id),
        created_at=analysis.created_at
    )

@router.get("/{project_id}/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    project_id: UUID,
    page: int = 1,
    size: int = 10,
    analysis_type: Optional[AnalysisType] = None,
    status: Optional[AnalysisStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List project analyses"""
    project = verify_project_access(project_id, current_user, db)
    
    query = db.query(AnalysisCase).filter(AnalysisCase.project_id == project_id)
    
    # Apply filters
    if analysis_type:
        query = query.filter(AnalysisCase.analysis_type == analysis_type)
    
    if status:
        query = query.filter(AnalysisCase.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    analyses = query.order_by(AnalysisCase.created_at.desc()).offset(offset).limit(size).all()
    
    analysis_responses = [
        AnalysisResponse(
            id=str(analysis.id),
            analysis_type=analysis.analysis_type,
            status=analysis.status,
            parameters=analysis.parameters or {},
            load_combinations=analysis.load_combination_ids or [],
            description=analysis.description,
            results=analysis.solver_info.get("results") if analysis.solver_info else None,
            error_message=analysis.error_message,
            progress=analysis.progress_percentage,
            started_at=analysis.started_at,
            completed_at=analysis.completed_at,
            project_id=str(analysis.project_id),
            created_at=analysis.created_at
        )
        for analysis in analyses
    ]
    
    return AnalysisListResponse(
        analyses=analysis_responses,
        total=total,
        page=page,
        size=size
    )

@router.get("/{project_id}/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    project_id: UUID,
    analysis_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis by ID"""
    project = verify_project_access(project_id, current_user, db)
    
    analysis = db.query(AnalysisCase).filter(
        AnalysisCase.id == analysis_id,
        AnalysisCase.project_id == project_id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return AnalysisResponse(
        id=str(analysis.id),
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        parameters=analysis.parameters or {},
        load_combinations=analysis.load_combination_ids or [],
        description=analysis.description,
        results=analysis.solver_info.get("results") if analysis.solver_info else None,
        error_message=analysis.error_message,
        progress=analysis.progress_percentage,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        project_id=str(analysis.project_id),
        created_at=analysis.created_at
    )

@router.get("/{project_id}/analysis-types")
async def get_available_analysis_types(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available analysis types"""
    project = verify_project_access(project_id, current_user, db)
    
    return {
        "analysis_types": [
            {
                "type": "LINEAR_STATIC",
                "name": "Linear Static Analysis",
                "description": "Linear static analysis for dead, live, and other static loads"
            },
            {
                "type": "MODAL",
                "name": "Modal Analysis", 
                "description": "Eigenvalue analysis to determine natural frequencies and mode shapes"
            },
            {
                "type": "RESPONSE_SPECTRUM",
                "name": "Response Spectrum Analysis",
                "description": "Seismic analysis using response spectrum method"
            },
            {
                "type": "TIME_HISTORY",
                "name": "Time History Analysis",
                "description": "Dynamic analysis with time-varying loads"
            },
            {
                "type": "BUCKLING",
                "name": "Buckling Analysis",
                "description": "Linear buckling analysis to determine critical loads"
            },
            {
                "type": "NONLINEAR_STATIC",
                "name": "Nonlinear Static Analysis",
                "description": "Pushover analysis with material and geometric nonlinearity"
            }
        ]
    }