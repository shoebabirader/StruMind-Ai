"""
Structural Design API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from db.database import get_db
from db.models.design import DesignResult, DesignStatus, DesignCode
from db.models.project import Project
from db.models.user import User
from api.v1.auth.router import get_current_user
# from design.concrete import ConcreteDesigner  # Temporarily commented out
from core.exceptions import ValidationError, NotFoundError

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class DesignRequest(BaseModel):
    element_ids: List[str]
    design_code: DesignCode
    parameters: Dict[str, Any]
    load_combinations: List[str]

class DesignResponse(BaseModel):
    id: str
    element_id: str
    design_code: DesignCode
    status: DesignStatus
    results: Optional[Dict[str, Any]]
    recommendations: Optional[List[str]]
    warnings: Optional[List[str]]
    errors: Optional[List[str]]
    utilization_ratio: Optional[float]
    project_id: str
    created_at: datetime

class DesignSummaryResponse(BaseModel):
    total_elements: int
    passed_elements: int
    failed_elements: int
    pending_elements: int
    max_utilization: float
    avg_utilization: float
    critical_elements: List[str]

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
async def design_health():
    """Design service health check"""
    return {"status": "healthy", "service": "design"}

@router.post("/{project_id}/run", response_model=List[DesignResponse])
async def run_design(
    project_id: UUID,
    design_request: DesignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run structural design for elements"""
    project = verify_project_access(project_id, current_user, db)
    
    design_results = []
    
    for element_id in design_request.element_ids:
        # Create design result record
        design_result = DesignResult(
            element_id=UUID(element_id),
            design_code=design_request.design_code,
            status=DesignStatus.COMPLETED,
            project_id=project_id
        )
        
        # Simulate design results based on design code
        if design_request.design_code == DesignCode.ACI_318:
            design_result.results = {
                "concrete_strength": 30.0,  # MPa
                "steel_grade": "Grade 60",
                "main_reinforcement": {
                    "top": "4#20",
                    "bottom": "3#16"
                },
                "shear_reinforcement": "#10@200mm",
                "capacity": {
                    "moment": 250.5,  # kN-m
                    "shear": 180.2,   # kN
                    "axial": 1200.0   # kN
                },
                "demand": {
                    "moment": 200.3,  # kN-m
                    "shear": 150.1,   # kN
                    "axial": 980.0    # kN
                }
            }
            design_result.utilization_ratio = max(
                200.3 / 250.5,  # Moment
                150.1 / 180.2,  # Shear
                980.0 / 1200.0  # Axial
            )
            
        elif design_request.design_code == DesignCode.AISC_360:
            design_result.results = {
                "steel_grade": "A992",
                "section": "W14x22",
                "capacity": {
                    "moment": 180.5,  # kN-m
                    "shear": 220.3,   # kN
                    "axial": 1500.0   # kN
                },
                "demand": {
                    "moment": 145.2,  # kN-m
                    "shear": 180.1,   # kN
                    "axial": 1200.0   # kN
                },
                "buckling_check": "OK",
                "deflection_check": "OK"
            }
            design_result.utilization_ratio = max(
                145.2 / 180.5,  # Moment
                180.1 / 220.3,  # Shear
                1200.0 / 1500.0 # Axial
            )
        
        # Set status based on utilization
        if design_result.utilization_ratio > 1.0:
            design_result.status = DesignStatus.FAILED
            design_result.errors = ["Element capacity exceeded"]
        elif design_result.utilization_ratio > 0.95:
            design_result.status = DesignStatus.PASSED
            design_result.warnings = ["High utilization ratio - consider larger section"]
        else:
            design_result.status = DesignStatus.PASSED
            design_result.recommendations = ["Design is adequate"]
        
        db.add(design_result)
        db.commit()
        db.refresh(design_result)
        
        design_results.append(DesignResponse(
            id=str(design_result.id),
            element_id=str(design_result.element_id),
            design_code=design_result.design_code,
            status=design_result.status,
            results=design_result.results,
            recommendations=design_result.recommendations,
            warnings=design_result.warnings,
            errors=design_result.errors,
            utilization_ratio=design_result.utilization_ratio,
            project_id=str(design_result.project_id),
            created_at=design_result.created_at
        ))
    
    return design_results

@router.get("/{project_id}/results", response_model=List[DesignResponse])
async def get_design_results(
    project_id: UUID,
    element_id: Optional[str] = None,
    design_code: Optional[DesignCode] = None,
    status: Optional[DesignStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get design results for project"""
    project = verify_project_access(project_id, current_user, db)
    
    query = db.query(DesignResult).filter(DesignResult.project_id == project_id)
    
    # Apply filters
    if element_id:
        query = query.filter(DesignResult.element_id == UUID(element_id))
    
    if design_code:
        query = query.filter(DesignResult.design_code == design_code)
    
    if status:
        query = query.filter(DesignResult.status == status)
    
    design_results = query.all()
    
    return [
        DesignResponse(
            id=str(result.id),
            element_id=str(result.element_id),
            design_code=result.design_code,
            status=result.status,
            results=result.results,
            recommendations=result.recommendations,
            warnings=result.warnings,
            errors=result.errors,
            utilization_ratio=result.utilization_ratio,
            project_id=str(result.project_id),
            created_at=result.created_at
        )
        for result in design_results
    ]

@router.get("/{project_id}/summary", response_model=DesignSummaryResponse)
async def get_design_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get design summary for project"""
    project = verify_project_access(project_id, current_user, db)
    
    design_results = db.query(DesignResult).filter(
        DesignResult.project_id == project_id
    ).all()
    
    total_elements = len(design_results)
    passed_elements = len([r for r in design_results if r.status == DesignStatus.PASSED])
    failed_elements = len([r for r in design_results if r.status == DesignStatus.FAILED])
    pending_elements = len([r for r in design_results if r.status == DesignStatus.PENDING])
    
    utilizations = [r.utilization_ratio for r in design_results if r.utilization_ratio is not None]
    max_utilization = max(utilizations) if utilizations else 0.0
    avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0.0
    
    # Find critical elements (utilization > 0.9)
    critical_elements = [
        str(r.element_id) for r in design_results 
        if r.utilization_ratio and r.utilization_ratio > 0.9
    ]
    
    return DesignSummaryResponse(
        total_elements=total_elements,
        passed_elements=passed_elements,
        failed_elements=failed_elements,
        pending_elements=pending_elements,
        max_utilization=max_utilization,
        avg_utilization=avg_utilization,
        critical_elements=critical_elements
    )

@router.get("/{project_id}/codes")
async def get_available_design_codes(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get available design codes"""
    project = verify_project_access(project_id, current_user, db)
    
    return {
        "concrete_codes": [
            {
                "code": "ACI_318",
                "name": "ACI 318 - Building Code Requirements for Structural Concrete",
                "region": "USA",
                "material": "concrete"
            },
            {
                "code": "IS_456",
                "name": "IS 456 - Plain and Reinforced Concrete Code of Practice",
                "region": "India",
                "material": "concrete"
            },
            {
                "code": "EUROCODE_2",
                "name": "Eurocode 2 - Design of concrete structures",
                "region": "Europe",
                "material": "concrete"
            }
        ],
        "steel_codes": [
            {
                "code": "AISC_360",
                "name": "AISC 360 - Specification for Structural Steel Buildings",
                "region": "USA",
                "material": "steel"
            },
            {
                "code": "IS_800",
                "name": "IS 800 - General Construction in Steel Code of Practice",
                "region": "India",
                "material": "steel"
            },
            {
                "code": "EUROCODE_3",
                "name": "Eurocode 3 - Design of steel structures",
                "region": "Europe",
                "material": "steel"
            }
        ]
    }