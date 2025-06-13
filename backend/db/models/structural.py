"""
Structural engineering models for nodes, elements, materials, sections, loads, and boundary conditions
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


class ElementType(str, Enum):
    """Element type enumeration"""
    BEAM = "beam"
    COLUMN = "column"
    BRACE = "brace"
    TRUSS = "truss"
    SHELL = "shell"
    PLATE = "plate"
    WALL = "wall"
    SLAB = "slab"
    SPRING = "spring"
    DAMPER = "damper"


class MaterialType(str, Enum):
    """Material type enumeration"""
    CONCRETE = "concrete"
    STEEL = "steel"
    TIMBER = "timber"
    ALUMINUM = "aluminum"
    COMPOSITE = "composite"
    MASONRY = "masonry"
    OTHER = "other"


class SectionType(str, Enum):
    """Section type enumeration"""
    I_SECTION = "i_section"
    CHANNEL = "channel"
    ANGLE = "angle"
    TEE = "tee"
    TUBE_RECTANGULAR = "tube_rectangular"
    TUBE_CIRCULAR = "tube_circular"
    RECTANGULAR = "rectangular"
    CIRCULAR = "circular"
    CUSTOM = "custom"


class LoadType(str, Enum):
    """Load type enumeration"""
    POINT = "point"
    DISTRIBUTED = "distributed"
    AREA = "area"
    MOMENT = "moment"
    TEMPERATURE = "temperature"
    SETTLEMENT = "settlement"


class LoadDirection(str, Enum):
    """Load direction enumeration"""
    X = "x"
    Y = "y"
    Z = "z"
    XX = "xx"  # Moment about X
    YY = "yy"  # Moment about Y
    ZZ = "zz"  # Moment about Z


class SupportType(str, Enum):
    """Support type enumeration"""
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER = "roller"
    SPRING = "spring"
    CUSTOM = "custom"


class Node(Base):
    """Node model for structural geometry"""
    
    __tablename__ = "nodes"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Node identification
    node_id = Column(Integer, nullable=False)  # User-defined node number
    label = Column(String(50), nullable=True)
    
    # Coordinates
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    
    # Properties
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="nodes")
    elements_start = relationship("Element", foreign_keys="Element.start_node_id", back_populates="start_node")
    elements_end = relationship("Element", foreign_keys="Element.end_node_id", back_populates="end_node")
    loads = relationship("Load", back_populates="node")
    boundary_conditions = relationship("BoundaryCondition", back_populates="node")
    node_results = relationship("NodeResult", back_populates="node")
    
    def __repr__(self) -> str:
        return f"<Node(id={self.node_id}, x={self.x}, y={self.y}, z={self.z})>"


class Material(Base):
    """Material model for structural materials"""
    
    __tablename__ = "materials"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Material identification
    name = Column(String(100), nullable=False)
    material_type = Column(SQLEnum(MaterialType), nullable=False)
    grade = Column(String(50), nullable=True)
    standard = Column(String(50), nullable=True)
    
    # Mechanical Properties
    elastic_modulus = Column(Float, nullable=False)  # E (Pa)
    poisson_ratio = Column(Float, nullable=False)    # ν
    density = Column(Float, nullable=False)          # ρ (kg/m³)
    
    # Strength Properties
    yield_strength = Column(Float, nullable=True)     # fy (Pa)
    ultimate_strength = Column(Float, nullable=True)  # fu (Pa)
    compressive_strength = Column(Float, nullable=True)  # fc (Pa)
    
    # Thermal Properties
    thermal_expansion = Column(Float, nullable=True)  # α (1/°C)
    thermal_conductivity = Column(Float, nullable=True)  # k (W/m·K)
    
    # Additional Properties (JSON for flexibility)
    properties = Column(JSON, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="materials")
    sections = relationship("Section", back_populates="material")
    elements = relationship("Element", back_populates="material")
    
    def __repr__(self) -> str:
        return f"<Material(name={self.name}, type={self.material_type})>"


class Section(Base):
    """Section model for structural cross-sections"""
    
    __tablename__ = "sections"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Section identification
    name = Column(String(100), nullable=False)
    section_type = Column(SQLEnum(SectionType), nullable=False)
    designation = Column(String(50), nullable=True)  # e.g., "W14x22"
    
    # Geometric Properties
    area = Column(Float, nullable=False)              # A (m²)
    moment_inertia_y = Column(Float, nullable=False)  # Iy (m⁴)
    moment_inertia_z = Column(Float, nullable=False)  # Iz (m⁴)
    moment_inertia_x = Column(Float, nullable=True)   # J (m⁴) - torsional
    section_modulus_y = Column(Float, nullable=True)  # Sy (m³)
    section_modulus_z = Column(Float, nullable=True)  # Sz (m³)
    radius_gyration_y = Column(Float, nullable=True)  # ry (m)
    radius_gyration_z = Column(Float, nullable=True)  # rz (m)
    
    # Dimensions (JSON for flexibility across section types)
    dimensions = Column(JSON, nullable=False)  # e.g., {"depth": 0.35, "width": 0.25, "flange_thickness": 0.015}
    
    # Shear Properties
    shear_area_y = Column(Float, nullable=True)       # Ay (m²)
    shear_area_z = Column(Float, nullable=True)       # Az (m²)
    
    # Additional Properties
    properties = Column(JSON, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(String(36), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="sections")
    material = relationship("Material", back_populates="sections")
    elements = relationship("Element", back_populates="section")
    
    def __repr__(self) -> str:
        return f"<Section(name={self.name}, type={self.section_type})>"


class Element(Base):
    """Element model for structural elements"""
    
    __tablename__ = "elements"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Element identification
    element_id = Column(Integer, nullable=False)  # User-defined element number
    label = Column(String(50), nullable=True)
    element_type = Column(SQLEnum(ElementType), nullable=False)
    
    # Connectivity
    start_node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    end_node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)  # Null for point elements
    
    # Properties
    length = Column(Float, nullable=True)  # Calculated or user-defined
    orientation_angle = Column(Float, default=0.0, nullable=False)  # Rotation about local x-axis (radians)
    
    # Element Properties (JSON for flexibility)
    properties = Column(JSON, nullable=True)  # Element-specific properties
    
    # Analysis Properties
    is_active = Column(Boolean, default=True, nullable=False)
    mesh_size = Column(Float, nullable=True)  # For shell/plate elements
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(String(36), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    section_id = Column(String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="elements")
    material = relationship("Material", back_populates="elements")
    section = relationship("Section", back_populates="elements")
    start_node = relationship("Node", foreign_keys=[start_node_id], back_populates="elements_start")
    end_node = relationship("Node", foreign_keys=[end_node_id], back_populates="elements_end")
    loads = relationship("Load", back_populates="element")
    releases = relationship("Release", back_populates="element")
    element_results = relationship("ElementResult", back_populates="element")
    
    def __repr__(self) -> str:
        return f"<Element(id={self.element_id}, type={self.element_type})>"


class LoadCase(Base):
    """Load case model for organizing loads"""
    
    __tablename__ = "load_cases"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Load case identification
    name = Column(String(100), nullable=False)
    case_type = Column(String(50), nullable=False)  # "dead", "live", "wind", "seismic", "temperature", etc.
    description = Column(Text, nullable=True)
    
    # Load case properties
    self_weight_factor = Column(Float, default=1.0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="load_cases")
    loads = relationship("Load", back_populates="load_case")
    
    def __repr__(self) -> str:
        return f"<LoadCase(name={self.name}, type={self.case_type})>"


class Load(Base):
    """Load model for applied loads"""
    
    __tablename__ = "loads"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Load identification
    name = Column(String(100), nullable=True)
    load_type = Column(SQLEnum(LoadType), nullable=False)
    direction = Column(SQLEnum(LoadDirection), nullable=False)
    
    # Load values
    magnitude = Column(Float, nullable=False)
    magnitude_2 = Column(Float, nullable=True)  # For distributed loads (end value)
    
    # Load position (for element loads)
    position_start = Column(Float, default=0.0, nullable=True)  # Relative position (0.0 to 1.0)
    position_end = Column(Float, default=1.0, nullable=True)    # Relative position (0.0 to 1.0)
    
    # Coordinate system
    coordinate_system = Column(String(20), default="global", nullable=False)  # "global" or "local"
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Foreign Keys
    load_case_id = Column(String(36), ForeignKey("load_cases.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True)
    element_id = Column(String(36), ForeignKey("elements.id", ondelete="CASCADE"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    load_case = relationship("LoadCase", back_populates="loads")
    node = relationship("Node", back_populates="loads")
    element = relationship("Element", back_populates="loads")
    
    def __repr__(self) -> str:
        return f"<Load(type={self.load_type}, magnitude={self.magnitude})>"


class LoadCombination(Base):
    """Load combination model for analysis"""
    
    __tablename__ = "load_combinations"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Combination identification
    name = Column(String(100), nullable=False)
    combination_type = Column(String(50), nullable=False)  # "linear", "envelope", "srss"
    description = Column(Text, nullable=True)
    
    # Combination definition (JSON)
    # Format: [{"load_case_id": "uuid", "factor": 1.4}, ...]
    combination_factors = Column(JSON, nullable=False)
    
    # Properties
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="load_combinations")
    
    def __repr__(self) -> str:
        return f"<LoadCombination(name={self.name}, type={self.combination_type})>"


class BoundaryCondition(Base):
    """Boundary condition model for supports and constraints"""
    
    __tablename__ = "boundary_conditions"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Boundary condition identification
    name = Column(String(100), nullable=True)
    support_type = Column(SQLEnum(SupportType), nullable=False)
    
    # Restraints (True = restrained, False = free)
    restraint_x = Column(Boolean, default=False, nullable=False)
    restraint_y = Column(Boolean, default=False, nullable=False)
    restraint_z = Column(Boolean, default=False, nullable=False)
    restraint_xx = Column(Boolean, default=False, nullable=False)  # Rotation about X
    restraint_yy = Column(Boolean, default=False, nullable=False)  # Rotation about Y
    restraint_zz = Column(Boolean, default=False, nullable=False)  # Rotation about Z
    
    # Spring stiffness (for spring supports)
    spring_stiffness_x = Column(Float, nullable=True)
    spring_stiffness_y = Column(Float, nullable=True)
    spring_stiffness_z = Column(Float, nullable=True)
    spring_stiffness_xx = Column(Float, nullable=True)
    spring_stiffness_yy = Column(Float, nullable=True)
    spring_stiffness_zz = Column(Float, nullable=True)
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(36), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="boundary_conditions")
    node = relationship("Node", back_populates="boundary_conditions")
    
    def __repr__(self) -> str:
        return f"<BoundaryCondition(type={self.support_type}, node_id={self.node_id})>"


class Release(Base):
    """Release model for element end releases"""
    
    __tablename__ = "releases"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Release identification
    name = Column(String(100), nullable=True)
    end = Column(String(10), nullable=False)  # "start" or "end"
    
    # Releases (True = released, False = fixed)
    release_x = Column(Boolean, default=False, nullable=False)
    release_y = Column(Boolean, default=False, nullable=False)
    release_z = Column(Boolean, default=False, nullable=False)
    release_xx = Column(Boolean, default=False, nullable=False)  # Moment about X
    release_yy = Column(Boolean, default=False, nullable=False)  # Moment about Y
    release_zz = Column(Boolean, default=False, nullable=False)  # Moment about Z
    
    # Partial release factors (0.0 = fully released, 1.0 = fully fixed)
    partial_factor_x = Column(Float, default=1.0, nullable=False)
    partial_factor_y = Column(Float, default=1.0, nullable=False)
    partial_factor_z = Column(Float, default=1.0, nullable=False)
    partial_factor_xx = Column(Float, default=1.0, nullable=False)
    partial_factor_yy = Column(Float, default=1.0, nullable=False)
    partial_factor_zz = Column(Float, default=1.0, nullable=False)
    
    # Foreign Keys
    element_id = Column(String(36), ForeignKey("elements.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    element = relationship("Element", back_populates="releases")
    
    def __repr__(self) -> str:
        return f"<Release(element_id={self.element_id}, end={self.end})>"