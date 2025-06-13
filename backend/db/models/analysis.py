"""
Analysis models for structural analysis results and cases
"""

import uuid
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class AnalysisType(str, Enum):
    """Analysis type enumeration"""
    LINEAR_STATIC = "linear_static"
    NONLINEAR_STATIC = "nonlinear_static"
    MODAL = "modal"
    RESPONSE_SPECTRUM = "response_spectrum"
    TIME_HISTORY = "time_history"
    BUCKLING = "buckling"
    P_DELTA = "p_delta"


class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResultType(str, Enum):
    """Result type enumeration"""
    DISPLACEMENT = "displacement"
    REACTION = "reaction"
    FORCE = "force"
    MOMENT = "moment"
    STRESS = "stress"
    STRAIN = "strain"
    MODE_SHAPE = "mode_shape"
    FREQUENCY = "frequency"


class AnalysisCase(Base):
    """Analysis case model for different types of structural analysis"""
    
    __tablename__ = "analysis_cases"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Analysis identification
    name = Column(String(100), nullable=False)
    analysis_type = Column(SQLEnum(AnalysisType), nullable=False)
    description = Column(Text, nullable=True)
    
    # Analysis parameters (JSON for flexibility)
    parameters = Column(JSON, nullable=True)
    # Example parameters:
    # {
    #   "max_iterations": 100,
    #   "convergence_tolerance": 1e-6,
    #   "load_steps": 10,
    #   "damping_ratio": 0.05,
    #   "frequency_range": [0, 100],
    #   "number_of_modes": 10
    # }
    
    # Load combinations to analyze
    load_combination_ids = Column(JSON, nullable=True)  # List of load combination UUIDs
    
    # Analysis status
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    
    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Computational details
    total_nodes = Column(Integer, nullable=True)
    total_elements = Column(Integer, nullable=True)
    total_dof = Column(Integer, nullable=True)  # Degrees of freedom
    solver_info = Column(JSON, nullable=True)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="analysis_cases")
    created_by = relationship("User")
    analysis_results = relationship("AnalysisResult", back_populates="analysis_case", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AnalysisCase(name={self.name}, type={self.analysis_type})>"


class AnalysisResult(Base):
    """Analysis result model for storing analysis outputs"""
    
    __tablename__ = "analysis_results"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Result identification
    result_name = Column(String(100), nullable=False)
    result_type = Column(SQLEnum(ResultType), nullable=False)
    load_combination_name = Column(String(100), nullable=True)
    
    # Result metadata
    units = Column(JSON, nullable=True)  # {"force": "kN", "length": "m", "stress": "MPa"}
    time_step = Column(Float, nullable=True)  # For time history analysis
    mode_number = Column(Integer, nullable=True)  # For modal analysis
    frequency = Column(Float, nullable=True)  # For modal analysis (Hz)
    
    # Summary statistics
    max_value = Column(Float, nullable=True)
    min_value = Column(Float, nullable=True)
    max_location = Column(JSON, nullable=True)  # {"node_id": "uuid", "element_id": "uuid", "position": 0.5}
    min_location = Column(JSON, nullable=True)
    
    # Result data storage path (for large datasets)
    data_file_path = Column(String(500), nullable=True)
    data_size_mb = Column(Float, nullable=True)
    
    # Foreign Keys
    analysis_case_id = Column(String(36), ForeignKey("analysis_cases.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    analysis_case = relationship("AnalysisCase", back_populates="analysis_results")
    node_results = relationship("NodeResult", back_populates="analysis_result", cascade="all, delete-orphan")
    element_results = relationship("ElementResult", back_populates="analysis_result", cascade="all, delete-orphan")
    modal_results = relationship("ModalResult", back_populates="analysis_result", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AnalysisResult(name={self.result_name}, type={self.result_type})>"


class NodeResult(Base):
    """Node result model for nodal analysis results"""
    
    __tablename__ = "node_results"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Displacement results
    displacement_x = Column(Float, nullable=True)
    displacement_y = Column(Float, nullable=True)
    displacement_z = Column(Float, nullable=True)
    rotation_x = Column(Float, nullable=True)
    rotation_y = Column(Float, nullable=True)
    rotation_z = Column(Float, nullable=True)
    
    # Reaction results
    reaction_x = Column(Float, nullable=True)
    reaction_y = Column(Float, nullable=True)
    reaction_z = Column(Float, nullable=True)
    moment_x = Column(Float, nullable=True)
    moment_y = Column(Float, nullable=True)
    moment_z = Column(Float, nullable=True)
    
    # Additional results (JSON for flexibility)
    additional_results = Column(JSON, nullable=True)
    
    # Foreign Keys
    analysis_result_id = Column(String(36), ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    analysis_result = relationship("AnalysisResult", back_populates="node_results")
    node = relationship("Node", back_populates="node_results")
    
    def __repr__(self) -> str:
        return f"<NodeResult(node_id={self.node_id}, dx={self.displacement_x})>"


class ElementResult(Base):
    """Element result model for element analysis results"""
    
    __tablename__ = "element_results"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Position along element (0.0 to 1.0)
    position = Column(Float, default=0.0, nullable=False)
    
    # Force results
    axial_force = Column(Float, nullable=True)      # N
    shear_force_y = Column(Float, nullable=True)    # Vy
    shear_force_z = Column(Float, nullable=True)    # Vz
    torsion = Column(Float, nullable=True)          # T
    moment_y = Column(Float, nullable=True)         # My
    moment_z = Column(Float, nullable=True)         # Mz
    
    # Stress results
    axial_stress = Column(Float, nullable=True)
    shear_stress_y = Column(Float, nullable=True)
    shear_stress_z = Column(Float, nullable=True)
    bending_stress_y = Column(Float, nullable=True)
    bending_stress_z = Column(Float, nullable=True)
    von_mises_stress = Column(Float, nullable=True)
    
    # Strain results
    axial_strain = Column(Float, nullable=True)
    shear_strain_y = Column(Float, nullable=True)
    shear_strain_z = Column(Float, nullable=True)
    
    # Displacement results
    displacement_x = Column(Float, nullable=True)
    displacement_y = Column(Float, nullable=True)
    displacement_z = Column(Float, nullable=True)
    rotation_x = Column(Float, nullable=True)
    rotation_y = Column(Float, nullable=True)
    rotation_z = Column(Float, nullable=True)
    
    # Additional results (JSON for flexibility)
    additional_results = Column(JSON, nullable=True)
    
    # Foreign Keys
    analysis_result_id = Column(String(36), ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False)
    element_id = Column(String(36), ForeignKey("elements.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    analysis_result = relationship("AnalysisResult", back_populates="element_results")
    element = relationship("Element", back_populates="element_results")
    
    def __repr__(self) -> str:
        return f"<ElementResult(element_id={self.element_id}, position={self.position})>"


class ModalResult(Base):
    """Modal result model for modal analysis results"""
    
    __tablename__ = "modal_results"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Modal properties
    mode_number = Column(Integer, nullable=False)
    frequency = Column(Float, nullable=False)  # Hz
    period = Column(Float, nullable=False)     # seconds
    circular_frequency = Column(Float, nullable=False)  # rad/s
    
    # Modal participation factors
    participation_factor_x = Column(Float, nullable=True)
    participation_factor_y = Column(Float, nullable=True)
    participation_factor_z = Column(Float, nullable=True)
    participation_factor_rx = Column(Float, nullable=True)
    participation_factor_ry = Column(Float, nullable=True)
    participation_factor_rz = Column(Float, nullable=True)
    
    # Modal mass ratios
    mass_ratio_x = Column(Float, nullable=True)
    mass_ratio_y = Column(Float, nullable=True)
    mass_ratio_z = Column(Float, nullable=True)
    mass_ratio_rx = Column(Float, nullable=True)
    mass_ratio_ry = Column(Float, nullable=True)
    mass_ratio_rz = Column(Float, nullable=True)
    
    # Cumulative mass ratios
    cumulative_mass_ratio_x = Column(Float, nullable=True)
    cumulative_mass_ratio_y = Column(Float, nullable=True)
    cumulative_mass_ratio_z = Column(Float, nullable=True)
    
    # Mode shape data storage path
    mode_shape_file_path = Column(String(500), nullable=True)
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Foreign Keys
    analysis_result_id = Column(String(36), ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    analysis_result = relationship("AnalysisResult", back_populates="modal_results")
    
    def __repr__(self) -> str:
        return f"<ModalResult(mode={self.mode_number}, freq={self.frequency:.2f}Hz)>"