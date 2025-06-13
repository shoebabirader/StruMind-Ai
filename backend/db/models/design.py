"""
Design models for structural design results and detailing
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


class DesignType(str, Enum):
    """Design type enumeration"""
    RC_BEAM = "rc_beam"
    RC_COLUMN = "rc_column"
    RC_SLAB = "rc_slab"
    RC_WALL = "rc_wall"
    RC_FOUNDATION = "rc_foundation"
    STEEL_BEAM = "steel_beam"
    STEEL_COLUMN = "steel_column"
    STEEL_BRACE = "steel_brace"
    STEEL_CONNECTION = "steel_connection"
    COMPOSITE_BEAM = "composite_beam"
    COMPOSITE_COLUMN = "composite_column"


class DesignCode(str, Enum):
    """Design code enumeration"""
    ACI_318 = "aci_318"
    IS_456 = "is_456"
    EUROCODE_2 = "eurocode_2"
    BS_8110 = "bs_8110"
    AISC_360 = "aisc_360"
    IS_800 = "is_800"
    EUROCODE_3 = "eurocode_3"
    BS_5950 = "bs_5950"


class DesignStatus(str, Enum):
    """Design status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DesignResult(str, Enum):
    """Design result enumeration"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_CHECKED = "not_checked"


class RebarType(str, Enum):
    """Reinforcement bar type enumeration"""
    MAIN_LONGITUDINAL = "main_longitudinal"
    SECONDARY_LONGITUDINAL = "secondary_longitudinal"
    STIRRUP = "stirrup"
    TIE = "tie"
    SPIRAL = "spiral"
    SHEAR = "shear"
    TORSION = "torsion"
    SKIN = "skin"


class ConnectionType(str, Enum):
    """Steel connection type enumeration"""
    BOLTED_SHEAR = "bolted_shear"
    BOLTED_MOMENT = "bolted_moment"
    WELDED_SHEAR = "welded_shear"
    WELDED_MOMENT = "welded_moment"
    COMPOSITE = "composite"
    BASE_PLATE = "base_plate"


class DesignCase(Base):
    """Design case model for structural design analysis"""
    
    __tablename__ = "design_cases"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Design identification
    name = Column(String(100), nullable=False)
    design_type = Column(SQLEnum(DesignType), nullable=False)
    design_code = Column(SQLEnum(DesignCode), nullable=False)
    description = Column(Text, nullable=True)
    
    # Design parameters (JSON for flexibility)
    parameters = Column(JSON, nullable=True)
    # Example parameters:
    # {
    #   "concrete_grade": "M25",
    #   "steel_grade": "Fe415",
    #   "cover": 25,
    #   "exposure_condition": "moderate",
    #   "load_duration": "long_term",
    #   "importance_factor": 1.0,
    #   "seismic_zone": "III"
    # }
    
    # Analysis cases to use for design
    analysis_case_ids = Column(JSON, nullable=True)  # List of analysis case UUIDs
    load_combination_ids = Column(JSON, nullable=True)  # List of load combination UUIDs
    
    # Element selection criteria
    element_selection = Column(JSON, nullable=True)
    # Example: {"element_types": ["beam", "column"], "material_types": ["concrete"]}
    
    # Design status
    status = Column(SQLEnum(DesignStatus), default=DesignStatus.PENDING, nullable=False)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    
    # Execution details
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Design summary
    total_elements_designed = Column(Integer, nullable=True)
    elements_passed = Column(Integer, nullable=True)
    elements_failed = Column(Integer, nullable=True)
    elements_warning = Column(Integer, nullable=True)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="design_cases")
    created_by = relationship("User")
    design_results = relationship("DesignResult", back_populates="design_case", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<DesignCase(name={self.name}, type={self.design_type})>"


class DesignResult(Base):
    """Design result model for element design results"""
    
    __tablename__ = "design_results"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Design result identification
    result_name = Column(String(100), nullable=False)
    design_result = Column(SQLEnum(DesignResult), nullable=False)
    
    # Design forces (governing load combination)
    governing_load_combination = Column(String(100), nullable=True)
    design_axial_force = Column(Float, nullable=True)
    design_shear_force_y = Column(Float, nullable=True)
    design_shear_force_z = Column(Float, nullable=True)
    design_moment_y = Column(Float, nullable=True)
    design_moment_z = Column(Float, nullable=True)
    design_torsion = Column(Float, nullable=True)
    
    # Design capacities
    capacity_axial = Column(Float, nullable=True)
    capacity_shear_y = Column(Float, nullable=True)
    capacity_shear_z = Column(Float, nullable=True)
    capacity_moment_y = Column(Float, nullable=True)
    capacity_moment_z = Column(Float, nullable=True)
    capacity_torsion = Column(Float, nullable=True)
    
    # Utilization ratios
    utilization_axial = Column(Float, nullable=True)
    utilization_shear_y = Column(Float, nullable=True)
    utilization_shear_z = Column(Float, nullable=True)
    utilization_moment_y = Column(Float, nullable=True)
    utilization_moment_z = Column(Float, nullable=True)
    utilization_torsion = Column(Float, nullable=True)
    utilization_combined = Column(Float, nullable=True)
    
    # Design details (JSON for flexibility)
    design_details = Column(JSON, nullable=True)
    # Example for RC:
    # {
    #   "reinforcement": {
    #     "main_bars": {"top": "4-16mm", "bottom": "2-12mm"},
    #     "stirrups": "8mm@150c/c",
    #     "area_steel": 804.2
    #   },
    #   "concrete": {"grade": "M25", "area": 90000},
    #   "checks": {
    #     "minimum_reinforcement": "pass",
    #     "maximum_reinforcement": "pass",
    #     "deflection": "pass",
    #     "crack_width": "pass"
    #   }
    # }
    
    # Design warnings and notes
    warnings = Column(JSON, nullable=True)  # List of warning messages
    notes = Column(Text, nullable=True)
    
    # Code check details
    code_checks = Column(JSON, nullable=True)
    
    # Foreign Keys
    design_case_id = Column(String(36), ForeignKey("design_cases.id", ondelete="CASCADE"), nullable=False)
    element_id = Column(String(36), ForeignKey("elements.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    design_case = relationship("DesignCase", back_populates="design_results")
    element = relationship("Element")
    reinforcement_details = relationship("ReinforcementDetail", back_populates="design_result", cascade="all, delete-orphan")
    connection_details = relationship("ConnectionDetail", back_populates="design_result", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<DesignResult(element_id={self.element_id}, result={self.design_result})>"


class ReinforcementDetail(Base):
    """Reinforcement detail model for RC design"""
    
    __tablename__ = "reinforcement_details"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Reinforcement identification
    rebar_type = Column(SQLEnum(RebarType), nullable=False)
    location = Column(String(50), nullable=False)  # "top", "bottom", "left", "right", "corner", etc.
    
    # Bar details
    bar_diameter = Column(Float, nullable=False)  # mm
    bar_grade = Column(String(20), nullable=False)  # "Fe415", "Fe500", etc.
    number_of_bars = Column(Integer, nullable=False)
    bar_length = Column(Float, nullable=True)  # mm
    
    # Spacing and arrangement
    spacing = Column(Float, nullable=True)  # mm (for stirrups/ties)
    spacing_type = Column(String(20), nullable=True)  # "uniform", "variable"
    
    # Position details
    start_position = Column(Float, nullable=True)  # mm from element start
    end_position = Column(Float, nullable=True)    # mm from element start
    cover = Column(Float, nullable=False)          # mm
    
    # Development and anchorage
    development_length = Column(Float, nullable=True)  # mm
    anchorage_length = Column(Float, nullable=True)    # mm
    hook_type = Column(String(20), nullable=True)      # "90_degree", "180_degree", "straight"
    
    # Lap splice details
    lap_length = Column(Float, nullable=True)  # mm
    lap_location = Column(String(50), nullable=True)
    
    # Quantities
    total_length = Column(Float, nullable=True)  # mm
    total_weight = Column(Float, nullable=True)  # kg
    area_of_steel = Column(Float, nullable=True)  # mm²
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Drawing details
    drawing_notes = Column(Text, nullable=True)
    bending_schedule_id = Column(String(50), nullable=True)
    
    # Foreign Keys
    design_result_id = Column(String(36), ForeignKey("design_results.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    design_result = relationship("DesignResult", back_populates="reinforcement_details")
    
    def __repr__(self) -> str:
        return f"<ReinforcementDetail(type={self.rebar_type}, bars={self.number_of_bars}-{self.bar_diameter}mm)>"


class ConnectionDetail(Base):
    """Connection detail model for steel connections"""
    
    __tablename__ = "connection_details"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Connection identification
    connection_type = Column(SQLEnum(ConnectionType), nullable=False)
    connection_name = Column(String(100), nullable=True)
    
    # Connected elements
    primary_element_id = Column(String(36), ForeignKey("elements.id"), nullable=False)
    secondary_element_id = Column(String(36), ForeignKey("elements.id"), nullable=True)
    
    # Connection geometry
    connection_location = Column(String(50), nullable=False)  # "start", "end", "intermediate"
    eccentricity_x = Column(Float, default=0.0, nullable=False)  # mm
    eccentricity_y = Column(Float, default=0.0, nullable=False)  # mm
    eccentricity_z = Column(Float, default=0.0, nullable=False)  # mm
    
    # Bolt details (for bolted connections)
    bolt_diameter = Column(Float, nullable=True)  # mm
    bolt_grade = Column(String(20), nullable=True)  # "8.8", "10.9", etc.
    number_of_bolts = Column(Integer, nullable=True)
    bolt_pattern = Column(JSON, nullable=True)  # {"rows": 2, "columns": 3, "spacing_x": 60, "spacing_y": 80}
    bolt_hole_type = Column(String(20), nullable=True)  # "standard", "oversized", "slotted"
    
    # Weld details (for welded connections)
    weld_type = Column(String(20), nullable=True)  # "fillet", "groove", "plug"
    weld_size = Column(Float, nullable=True)  # mm
    weld_length = Column(Float, nullable=True)  # mm
    weld_electrode = Column(String(20), nullable=True)  # "E70XX", etc.
    
    # Plate details
    connection_plates = Column(JSON, nullable=True)
    # Example:
    # [
    #   {"type": "end_plate", "thickness": 12, "width": 200, "height": 300, "grade": "S355"},
    #   {"type": "stiffener", "thickness": 8, "width": 100, "height": 150, "grade": "S355"}
    # ]
    
    # Design forces
    design_shear = Column(Float, nullable=True)    # kN
    design_tension = Column(Float, nullable=True)  # kN
    design_moment = Column(Float, nullable=True)   # kN.m
    
    # Design capacities
    capacity_shear = Column(Float, nullable=True)    # kN
    capacity_tension = Column(Float, nullable=True)  # kN
    capacity_moment = Column(Float, nullable=True)   # kN.m
    
    # Utilization ratios
    utilization_shear = Column(Float, nullable=True)
    utilization_tension = Column(Float, nullable=True)
    utilization_moment = Column(Float, nullable=True)
    utilization_combined = Column(Float, nullable=True)
    
    # Connection checks
    connection_checks = Column(JSON, nullable=True)
    # Example:
    # {
    #   "bolt_shear": {"capacity": 45.2, "demand": 32.1, "ratio": 0.71, "result": "pass"},
    #   "bolt_bearing": {"capacity": 67.8, "demand": 32.1, "ratio": 0.47, "result": "pass"},
    #   "plate_yielding": {"capacity": 156.3, "demand": 32.1, "ratio": 0.21, "result": "pass"}
    # }
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Drawing details
    drawing_notes = Column(Text, nullable=True)
    detail_drawing_id = Column(String(50), nullable=True)
    
    # Foreign Keys
    design_result_id = Column(String(36), ForeignKey("design_results.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    design_result = relationship("DesignResult", back_populates="connection_details")
    primary_element = relationship("Element", foreign_keys=[primary_element_id])
    secondary_element = relationship("Element", foreign_keys=[secondary_element_id])
    
    def __repr__(self) -> str:
        return f"<ConnectionDetail(type={self.connection_type}, primary_element={self.primary_element_id})>"