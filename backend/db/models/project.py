"""
Project models for structural engineering projects
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class ProjectStatus(str, Enum):
    """Project status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ProjectType(str, Enum):
    """Project type enumeration"""
    BUILDING = "building"
    BRIDGE = "bridge"
    INDUSTRIAL = "industrial"
    INFRASTRUCTURE = "infrastructure"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    OTHER = "other"


class ProjectMemberRole(str, Enum):
    """Project member roles"""
    OWNER = "owner"
    LEAD_ENGINEER = "lead_engineer"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Project(Base):
    """Project model for structural engineering projects"""
    
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    project_number = Column(String(50), nullable=True)
    
    # Project Details
    project_type = Column(SQLEnum(ProjectType), default=ProjectType.BUILDING, nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)
    
    # Location
    location = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Client Information
    client_name = Column(String(200), nullable=True)
    client_contact = Column(String(200), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(20), nullable=True)
    
    # Project Dates
    start_date = Column(DateTime(timezone=True), nullable=True)
    target_completion_date = Column(DateTime(timezone=True), nullable=True)
    actual_completion_date = Column(DateTime(timezone=True), nullable=True)
    
    # Design Codes and Standards
    design_code_concrete = Column(String(50), default="ACI 318", nullable=False)
    design_code_steel = Column(String(50), default="AISC 360", nullable=False)
    design_code_seismic = Column(String(50), default="ASCE 7", nullable=False)
    design_code_wind = Column(String(50), default="ASCE 7", nullable=False)
    
    # Units
    length_unit = Column(String(10), default="m", nullable=False)
    force_unit = Column(String(10), default="kN", nullable=False)
    stress_unit = Column(String(10), default="MPa", nullable=False)
    
    # Project Settings
    is_public = Column(Boolean, default=False, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False)
    
    # File Storage
    thumbnail_url = Column(String(500), nullable=True)
    storage_used_mb = Column(Float, default=0.0, nullable=False)
    
    # Foreign Keys
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    created_by = relationship("User")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    
    # Structural Model Components
    nodes = relationship("Node", back_populates="project", cascade="all, delete-orphan")
    elements = relationship("Element", back_populates="project", cascade="all, delete-orphan")
    materials = relationship("Material", back_populates="project", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="project", cascade="all, delete-orphan")
    load_cases = relationship("LoadCase", back_populates="project", cascade="all, delete-orphan")
    load_combinations = relationship("LoadCombination", back_populates="project", cascade="all, delete-orphan")
    boundary_conditions = relationship("BoundaryCondition", back_populates="project", cascade="all, delete-orphan")
    
    # Analysis and Design
    analysis_cases = relationship("AnalysisCase", back_populates="project", cascade="all, delete-orphan")
    design_cases = relationship("DesignCase", back_populates="project", cascade="all, delete-orphan")
    
    # BIM
    bim_models = relationship("BIMModel", back_populates="project", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


class ProjectMember(Base):
    """Project membership with roles"""
    
    __tablename__ = "project_members"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Membership Details
    role = Column(SQLEnum(ProjectMemberRole), default=ProjectMemberRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Permissions
    can_edit_model = Column(Boolean, default=False, nullable=False)
    can_run_analysis = Column(Boolean, default=False, nullable=False)
    can_export_data = Column(Boolean, default=False, nullable=False)
    can_manage_members = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="project_memberships")
    project = relationship("Project", back_populates="members")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="unique_user_project"),
    )
    
    def __repr__(self) -> str:
        return f"<ProjectMember(user_id={self.user_id}, project_id={self.project_id}, role={self.role})>"