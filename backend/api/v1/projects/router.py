"""
Projects API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime

from db.database import get_db
from db.models.project import Project, ProjectStatus
from db.models.user import User
from api.v1.auth.router import get_current_user
from core.exceptions import ValidationError, NotFoundError

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    project_type: str = "commercial"
    design_code_concrete: str = "ACI_318"
    design_code_steel: str = "AISC_360"
    design_code_seismic: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    project_type: Optional[str] = None
    design_code_concrete: Optional[str] = None
    design_code_steel: Optional[str] = None
    design_code_seismic: Optional[str] = None
    status: Optional[ProjectStatus] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    location: Optional[str]
    project_type: str
    design_code_concrete: str
    design_code_steel: str
    design_code_seismic: Optional[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    owner_id: str
    organization_id: Optional[str]

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int

@router.get("/health")
async def projects_health():
    """Projects service health check"""
    return {"status": "healthy", "service": "projects"}

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new project"""
    # Get user's organization
    organization_id = None
    if current_user.organization_memberships:
        organization_id = str(current_user.organization_memberships[0].organization_id)
    
    project = Project(
        id=str(uuid.uuid4()),
        name=project_data.name,
        description=project_data.description,
        location=project_data.location,
        project_type=project_data.project_type,
        design_code_concrete=project_data.design_code_concrete,
        design_code_steel=project_data.design_code_steel,
        design_code_seismic=project_data.design_code_seismic,
        status=ProjectStatus.DRAFT,
        created_by_id=str(current_user.id),
        organization_id=organization_id
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        location=project.location,
        project_type=project.project_type,
        design_code_concrete=project.design_code_concrete,
        design_code_steel=project.design_code_steel,
        design_code_seismic=project.design_code_seismic,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_id=str(project.created_by_id),
        organization_id=str(project.organization_id) if project.organization_id else None
    )

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[ProjectStatus] = None,
    project_type: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's projects with pagination and filtering"""
    query = db.query(Project).filter(Project.created_by_id == str(current_user.id))
    
    # Apply filters
    if status:
        query = query.filter(Project.status == status)
    
    if project_type:
        query = query.filter(Project.project_type == project_type)
    
    if search:
        query = query.filter(
            Project.name.contains(search) | 
            Project.description.contains(search) |
            Project.location.contains(search)
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * size
    projects = query.offset(offset).limit(size).all()
    
    project_responses = [
        ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            location=project.location,
            project_type=project.project_type,
            design_code_concrete=project.design_code_concrete,
            design_code_steel=project.design_code_steel,
            design_code_seismic=project.design_code_seismic,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            owner_id=str(project.created_by_id),
            organization_id=str(project.organization_id) if project.organization_id else None
        )
        for project in projects
    ]
    
    return ProjectListResponse(
        projects=project_responses,
        total=total,
        page=page,
        size=size
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project by ID"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        location=project.location,
        project_type=project.project_type,
        design_code_concrete=project.design_code_concrete,
        design_code_steel=project.design_code_steel,
        design_code_seismic=project.design_code_seismic,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_id=str(project.created_by_id),
        organization_id=str(project.organization_id) if project.organization_id else None
    )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        location=project.location,
        project_type=project.project_type,
        design_code_concrete=project.design_code_concrete,
        design_code_steel=project.design_code_steel,
        design_code_seismic=project.design_code_seismic,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_id=str(project.created_by_id),
        organization_id=str(project.organization_id) if project.organization_id else None
    )

@router.delete("/{project_id}")
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete project"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}

@router.post("/{project_id}/duplicate", response_model=ProjectResponse)
async def duplicate_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate existing project"""
    original_project = db.query(Project).filter(
        Project.id == project_id,
        Project.created_by_id == current_user.id
    ).first()
    
    if not original_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create duplicate
    duplicate_project = Project(
        name=f"{original_project.name} (Copy)",
        description=original_project.description,
        location=original_project.location,
        project_type=original_project.project_type,
        design_code_concrete=original_project.design_code_concrete,
        design_code_steel=original_project.design_code_steel,
        design_code_seismic=original_project.design_code_seismic,
        status=ProjectStatus.DRAFT,
        created_by_id=current_user.id,
        organization_id=current_user.organization_memberships[0].organization_id if current_user.organization_memberships else None
    )
    
    db.add(duplicate_project)
    db.commit()
    db.refresh(duplicate_project)
    
    return ProjectResponse(
        id=str(duplicate_project.id),
        name=duplicate_project.name,
        description=duplicate_project.description,
        location=duplicate_project.location,
        project_type=duplicate_project.project_type,
        design_code_concrete=duplicate_project.design_code_concrete,
        design_code_steel=duplicate_project.design_code_steel,
        design_code_seismic=duplicate_project.design_code_seismic,
        status=duplicate_project.status,
        created_at=duplicate_project.created_at,
        updated_at=duplicate_project.updated_at,
        owner_id=str(duplicate_project.created_by_id),
        organization_id=str(duplicate_project.organization_id) if duplicate_project.organization_id else None
    )