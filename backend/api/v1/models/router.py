"""
Structural Models API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from db.database import get_db
from db.models.structural import Node, Element, Material, Section, Load, BoundaryCondition
from db.models.project import Project
from db.models.user import User
from api.v1.auth.router import get_current_user
from core.modeling.elements import ElementFactory, ElementProperties
from core.modeling.geometry import Point3D, GeometryEngine
from core.exceptions import ValidationError, NotFoundError

router = APIRouter()

# Pydantic models
from pydantic import BaseModel

class NodeCreate(BaseModel):
    x: float
    y: float
    z: float
    label: Optional[str] = None

class NodeResponse(BaseModel):
    id: str
    x: float
    y: float
    z: float
    label: Optional[str]
    project_id: str
    created_at: datetime

class ElementCreate(BaseModel):
    element_type: str
    start_node_id: str
    end_node_id: Optional[str] = None
    material_id: Optional[str] = None
    section_id: Optional[str] = None
    orientation_angle: float = 0.0
    properties: Optional[Dict[str, Any]] = None
    label: Optional[str] = None

class ElementResponse(BaseModel):
    id: str
    element_type: str
    start_node_id: str
    end_node_id: Optional[str]
    material_id: Optional[str]
    section_id: Optional[str]
    orientation_angle: float
    properties: Optional[Dict[str, Any]]
    label: Optional[str]
    project_id: str
    created_at: datetime

class MaterialCreate(BaseModel):
    name: str
    material_type: str  # steel, concrete, timber, composite
    properties: Dict[str, Any]
    grade: Optional[str] = None
    standard: Optional[str] = None

class MaterialResponse(BaseModel):
    id: str
    name: str
    material_type: str
    properties: Dict[str, Any]
    grade: Optional[str]
    standard: Optional[str]
    project_id: str
    created_at: datetime

class SectionCreate(BaseModel):
    name: str
    section_type: str  # i_section, rectangular, circular, etc.
    properties: Dict[str, Any]
    standard: Optional[str] = None

class SectionResponse(BaseModel):
    id: str
    name: str
    section_type: str
    properties: Dict[str, Any]
    standard: Optional[str]
    project_id: str
    created_at: datetime

class LoadCreate(BaseModel):
    load_type: str  # point, distributed, area, wind, seismic
    load_case: str
    values: Dict[str, Any]
    element_id: Optional[str] = None
    node_id: Optional[str] = None

class LoadResponse(BaseModel):
    id: str
    load_type: str
    load_case: str
    values: Dict[str, Any]
    element_id: Optional[str]
    node_id: Optional[str]
    project_id: str
    created_at: datetime

class BoundaryConditionCreate(BaseModel):
    node_id: str
    support_type: str  # fixed, pinned, roller, free
    restraints: Dict[str, bool]  # {dx: True, dy: True, dz: False, rx: True, ry: True, rz: False}

class BoundaryConditionResponse(BaseModel):
    id: str
    node_id: str
    support_type: str
    restraints: Dict[str, bool]
    project_id: str
    created_at: datetime

class ModelSummary(BaseModel):
    nodes_count: int
    elements_count: int
    materials_count: int
    sections_count: int
    loads_count: int
    boundary_conditions_count: int
    model_bounds: Dict[str, float]  # {min_x, max_x, min_y, max_y, min_z, max_z}

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
async def models_health():
    """Models service health check"""
    return {"status": "healthy", "service": "models"}

# Node endpoints
@router.post("/{project_id}/nodes", response_model=NodeResponse)
async def create_node(
    project_id: UUID,
    node_data: NodeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new node in project"""
    project = verify_project_access(project_id, current_user, db)
    
    node = Node(
        x=node_data.x,
        y=node_data.y,
        z=node_data.z,
        label=node_data.label,
        project_id=project_id
    )
    
    db.add(node)
    db.commit()
    db.refresh(node)
    
    return NodeResponse(
        id=str(node.id),
        x=node.x,
        y=node.y,
        z=node.z,
        label=node.label,
        project_id=str(node.project_id),
        created_at=node.created_at
    )

@router.get("/{project_id}/nodes", response_model=List[NodeResponse])
async def list_nodes(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all nodes in project"""
    project = verify_project_access(project_id, current_user, db)
    
    nodes = db.query(Node).filter(Node.project_id == project_id).all()
    
    return [
        NodeResponse(
            id=str(node.id),
            x=node.x,
            y=node.y,
            z=node.z,
            label=node.label,
            project_id=str(node.project_id),
            created_at=node.created_at
        )
        for node in nodes
    ]

@router.delete("/{project_id}/nodes/{node_id}")
async def delete_node(
    project_id: UUID,
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete node"""
    project = verify_project_access(project_id, current_user, db)
    
    node = db.query(Node).filter(
        Node.id == node_id,
        Node.project_id == project_id
    ).first()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Node not found"
        )
    
    # Check if node is used by elements
    elements_using_node = db.query(Element).filter(
        (Element.start_node_id == node_id) | (Element.end_node_id == node_id)
    ).count()
    
    if elements_using_node > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete node: it is used by elements"
        )
    
    db.delete(node)
    db.commit()
    
    return {"message": "Node deleted successfully"}

# Element endpoints
@router.post("/{project_id}/elements", response_model=ElementResponse)
async def create_element(
    project_id: UUID,
    element_data: ElementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new element in project"""
    project = verify_project_access(project_id, current_user, db)
    
    # Validate nodes exist
    start_node = db.query(Node).filter(
        Node.id == element_data.start_node_id,
        Node.project_id == project_id
    ).first()
    
    if not start_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Start node not found"
        )
    
    end_node = None
    if element_data.end_node_id:
        end_node = db.query(Node).filter(
            Node.id == element_data.end_node_id,
            Node.project_id == project_id
        ).first()
        
        if not end_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="End node not found"
            )
    
    element = Element(
        element_type=element_data.element_type,
        start_node_id=UUID(element_data.start_node_id),
        end_node_id=UUID(element_data.end_node_id) if element_data.end_node_id else None,
        material_id=UUID(element_data.material_id) if element_data.material_id else None,
        section_id=UUID(element_data.section_id) if element_data.section_id else None,
        orientation_angle=element_data.orientation_angle,
        properties=element_data.properties,
        label=element_data.label,
        project_id=project_id
    )
    
    db.add(element)
    db.commit()
    db.refresh(element)
    
    return ElementResponse(
        id=str(element.id),
        element_type=element.element_type,
        start_node_id=str(element.start_node_id),
        end_node_id=str(element.end_node_id) if element.end_node_id else None,
        material_id=str(element.material_id) if element.material_id else None,
        section_id=str(element.section_id) if element.section_id else None,
        orientation_angle=element.orientation_angle,
        properties=element.properties,
        label=element.label,
        project_id=str(element.project_id),
        created_at=element.created_at
    )

@router.get("/{project_id}/elements", response_model=List[ElementResponse])
async def list_elements(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all elements in project"""
    project = verify_project_access(project_id, current_user, db)
    
    elements = db.query(Element).filter(Element.project_id == project_id).all()
    
    return [
        ElementResponse(
            id=str(element.id),
            element_type=element.element_type,
            start_node_id=str(element.start_node_id),
            end_node_id=str(element.end_node_id) if element.end_node_id else None,
            material_id=str(element.material_id) if element.material_id else None,
            section_id=str(element.section_id) if element.section_id else None,
            orientation_angle=element.orientation_angle,
            properties=element.properties,
            label=element.label,
            project_id=str(element.project_id),
            created_at=element.created_at
        )
        for element in elements
    ]

# Material endpoints
@router.post("/{project_id}/materials", response_model=MaterialResponse)
async def create_material(
    project_id: UUID,
    material_data: MaterialCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new material in project"""
    project = verify_project_access(project_id, current_user, db)
    
    material = Material(
        name=material_data.name,
        material_type=material_data.material_type,
        properties=material_data.properties,
        grade=material_data.grade,
        standard=material_data.standard,
        project_id=project_id
    )
    
    db.add(material)
    db.commit()
    db.refresh(material)
    
    return MaterialResponse(
        id=str(material.id),
        name=material.name,
        material_type=material.material_type,
        properties=material.properties,
        grade=material.grade,
        standard=material.standard,
        project_id=str(material.project_id),
        created_at=material.created_at
    )

@router.get("/{project_id}/materials", response_model=List[MaterialResponse])
async def list_materials(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all materials in project"""
    project = verify_project_access(project_id, current_user, db)
    
    materials = db.query(Material).filter(Material.project_id == project_id).all()
    
    return [
        MaterialResponse(
            id=str(material.id),
            name=material.name,
            material_type=material.material_type,
            properties=material.properties,
            grade=material.grade,
            standard=material.standard,
            project_id=str(material.project_id),
            created_at=material.created_at
        )
        for material in materials
    ]

# Section endpoints
@router.post("/{project_id}/sections", response_model=SectionResponse)
async def create_section(
    project_id: UUID,
    section_data: SectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new section in project"""
    project = verify_project_access(project_id, current_user, db)
    
    section = Section(
        name=section_data.name,
        section_type=section_data.section_type,
        properties=section_data.properties,
        standard=section_data.standard,
        project_id=project_id
    )
    
    db.add(section)
    db.commit()
    db.refresh(section)
    
    return SectionResponse(
        id=str(section.id),
        name=section.name,
        section_type=section.section_type,
        properties=section.properties,
        standard=section.standard,
        project_id=str(section.project_id),
        created_at=section.created_at
    )

@router.get("/{project_id}/sections", response_model=List[SectionResponse])
async def list_sections(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all sections in project"""
    project = verify_project_access(project_id, current_user, db)
    
    sections = db.query(Section).filter(Section.project_id == project_id).all()
    
    return [
        SectionResponse(
            id=str(section.id),
            name=section.name,
            section_type=section.section_type,
            properties=section.properties,
            standard=section.standard,
            project_id=str(section.project_id),
            created_at=section.created_at
        )
        for section in sections
    ]

# Load endpoints
@router.post("/{project_id}/loads", response_model=LoadResponse)
async def create_load(
    project_id: UUID,
    load_data: LoadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new load in project"""
    project = verify_project_access(project_id, current_user, db)
    
    load = Load(
        load_type=load_data.load_type,
        load_case=load_data.load_case,
        values=load_data.values,
        element_id=UUID(load_data.element_id) if load_data.element_id else None,
        node_id=UUID(load_data.node_id) if load_data.node_id else None,
        project_id=project_id
    )
    
    db.add(load)
    db.commit()
    db.refresh(load)
    
    return LoadResponse(
        id=str(load.id),
        load_type=load.load_type,
        load_case=load.load_case,
        values=load.values,
        element_id=str(load.element_id) if load.element_id else None,
        node_id=str(load.node_id) if load.node_id else None,
        project_id=str(load.project_id),
        created_at=load.created_at
    )

@router.get("/{project_id}/loads", response_model=List[LoadResponse])
async def list_loads(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all loads in project"""
    project = verify_project_access(project_id, current_user, db)
    
    loads = db.query(Load).filter(Load.project_id == project_id).all()
    
    return [
        LoadResponse(
            id=str(load.id),
            load_type=load.load_type,
            load_case=load.load_case,
            values=load.values,
            element_id=str(load.element_id) if load.element_id else None,
            node_id=str(load.node_id) if load.node_id else None,
            project_id=str(load.project_id),
            created_at=load.created_at
        )
        for load in loads
    ]

# Boundary condition endpoints
@router.post("/{project_id}/boundary-conditions", response_model=BoundaryConditionResponse)
async def create_boundary_condition(
    project_id: UUID,
    bc_data: BoundaryConditionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new boundary condition in project"""
    project = verify_project_access(project_id, current_user, db)
    
    boundary_condition = BoundaryCondition(
        node_id=UUID(bc_data.node_id),
        support_type=bc_data.support_type,
        restraints=bc_data.restraints,
        project_id=project_id
    )
    
    db.add(boundary_condition)
    db.commit()
    db.refresh(boundary_condition)
    
    return BoundaryConditionResponse(
        id=str(boundary_condition.id),
        node_id=str(boundary_condition.node_id),
        support_type=boundary_condition.support_type,
        restraints=boundary_condition.restraints,
        project_id=str(boundary_condition.project_id),
        created_at=boundary_condition.created_at
    )

@router.get("/{project_id}/boundary-conditions", response_model=List[BoundaryConditionResponse])
async def list_boundary_conditions(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all boundary conditions in project"""
    project = verify_project_access(project_id, current_user, db)
    
    boundary_conditions = db.query(BoundaryCondition).filter(
        BoundaryCondition.project_id == project_id
    ).all()
    
    return [
        BoundaryConditionResponse(
            id=str(bc.id),
            node_id=str(bc.node_id),
            support_type=bc.support_type,
            restraints=bc.restraints,
            project_id=str(bc.project_id),
            created_at=bc.created_at
        )
        for bc in boundary_conditions
    ]

@router.get("/{project_id}/summary", response_model=ModelSummary)
async def get_model_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get model summary statistics"""
    project = verify_project_access(project_id, current_user, db)
    
    # Count entities
    nodes_count = db.query(Node).filter(Node.project_id == project_id).count()
    elements_count = db.query(Element).filter(Element.project_id == project_id).count()
    materials_count = db.query(Material).filter(Material.project_id == project_id).count()
    sections_count = db.query(Section).filter(Section.project_id == project_id).count()
    loads_count = db.query(Load).filter(Load.project_id == project_id).count()
    boundary_conditions_count = db.query(BoundaryCondition).filter(
        BoundaryCondition.project_id == project_id
    ).count()
    
    # Calculate model bounds
    nodes = db.query(Node).filter(Node.project_id == project_id).all()
    if nodes:
        x_coords = [node.x for node in nodes]
        y_coords = [node.y for node in nodes]
        z_coords = [node.z for node in nodes]
        
        model_bounds = {
            "min_x": min(x_coords),
            "max_x": max(x_coords),
            "min_y": min(y_coords),
            "max_y": max(y_coords),
            "min_z": min(z_coords),
            "max_z": max(z_coords)
        }
    else:
        model_bounds = {
            "min_x": 0.0, "max_x": 0.0,
            "min_y": 0.0, "max_y": 0.0,
            "min_z": 0.0, "max_z": 0.0
        }
    
    return ModelSummary(
        nodes_count=nodes_count,
        elements_count=elements_count,
        materials_count=materials_count,
        sections_count=sections_count,
        loads_count=loads_count,
        boundary_conditions_count=boundary_conditions_count,
        model_bounds=model_bounds
    )