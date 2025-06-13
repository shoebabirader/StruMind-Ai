"""
BIM models for Building Information Modeling integration
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
    LargeBinary,
    String,
    Text,
)
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class BIMFormat(str, Enum):
    """BIM format enumeration"""
    IFC = "ifc"
    GLTF = "gltf"
    DXF = "dxf"
    STEP = "step"
    COLLADA = "collada"
    FBX = "fbx"


class BIMElementType(str, Enum):
    """BIM element type enumeration"""
    BEAM = "beam"
    COLUMN = "column"
    SLAB = "slab"
    WALL = "wall"
    FOUNDATION = "foundation"
    STAIR = "stair"
    RAMP = "ramp"
    ROOF = "roof"
    DOOR = "door"
    WINDOW = "window"
    SPACE = "space"
    BUILDING = "building"
    STOREY = "storey"
    SITE = "site"


class BIMStatus(str, Enum):
    """BIM status enumeration"""
    DRAFT = "draft"
    SYNCHRONIZED = "synchronized"
    OUT_OF_SYNC = "out_of_sync"
    ERROR = "error"


class BIMModel(Base):
    """BIM model for 3D building information modeling"""
    
    __tablename__ = "bim_models"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Model identification
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0", nullable=False)
    
    # BIM metadata
    bim_format = Column(SQLEnum(BIMFormat), default=BIMFormat.IFC, nullable=False)
    schema_version = Column(String(20), nullable=True)  # e.g., "IFC4", "IFC2x3"
    
    # Model properties
    model_origin = Column(JSON, nullable=True)  # {"x": 0, "y": 0, "z": 0}
    model_units = Column(JSON, nullable=False)  # {"length": "m", "area": "m2", "volume": "m3"}
    coordinate_system = Column(String(50), default="local", nullable=False)
    
    # Geographic information
    site_location = Column(JSON, nullable=True)
    # Example:
    # {
    #   "latitude": 40.7128,
    #   "longitude": -74.0060,
    #   "elevation": 10.0,
    #   "address": "New York, NY",
    #   "true_north": 0.0
    # }
    
    # Building information
    building_info = Column(JSON, nullable=True)
    # Example:
    # {
    #   "building_name": "Office Tower",
    #   "building_type": "commercial",
    #   "number_of_storeys": 20,
    #   "total_height": 80.0,
    #   "gross_floor_area": 15000.0,
    #   "occupancy_type": "office"
    # }
    
    # Model status
    status = Column(SQLEnum(BIMStatus), default=BIMStatus.DRAFT, nullable=False)
    last_synchronized = Column(DateTime(timezone=True), nullable=True)
    sync_errors = Column(JSON, nullable=True)
    
    # File storage
    model_file_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    file_size_mb = Column(Float, nullable=True)
    
    # Export settings
    export_settings = Column(JSON, nullable=True)
    # Example:
    # {
    #   "include_geometry": true,
    #   "include_materials": true,
    #   "include_properties": true,
    #   "include_analysis_results": false,
    #   "level_of_detail": "medium",
    #   "coordinate_precision": 3
    # }
    
    # Foreign Keys
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="bim_models")
    created_by = relationship("User")
    bim_elements = relationship("BIMElement", back_populates="bim_model", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<BIMModel(name={self.name}, format={self.bim_format})>"


class BIMElement(Base):
    """BIM element for individual building components"""
    
    __tablename__ = "bim_elements"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Element identification
    global_id = Column(String(100), nullable=False)  # IFC GlobalId or similar
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    element_type = Column(SQLEnum(BIMElementType), nullable=False)
    
    # IFC specific
    ifc_type = Column(String(50), nullable=True)  # e.g., "IfcBeam", "IfcColumn"
    ifc_predefined_type = Column(String(50), nullable=True)  # e.g., "BEAM", "COLUMN"
    
    # Geometry
    geometry_representation = Column(JSON, nullable=True)
    # Example:
    # {
    #   "type": "swept_solid",
    #   "profile": {...},
    #   "extrusion_direction": [0, 0, 1],
    #   "extrusion_depth": 3.0,
    #   "placement": {
    #     "location": [0, 0, 0],
    #     "axis": [0, 0, 1],
    #     "ref_direction": [1, 0, 0]
    #   }
    # }
    
    # Bounding box
    bounding_box = Column(JSON, nullable=True)
    # {"min": [x, y, z], "max": [x, y, z]}
    
    # Material assignment
    material_assignments = Column(JSON, nullable=True)
    # [{"material_id": "uuid", "layer_thickness": 0.1, "function": "structural"}]
    
    # Quantities
    quantities = Column(JSON, nullable=True)
    # Example:
    # {
    #   "length": 6.0,
    #   "width": 0.3,
    #   "height": 0.5,
    #   "area": 1.8,
    #   "volume": 0.9,
    #   "weight": 2250.0
    # }
    
    # Relationships to structural model
    structural_element_id = Column(String(36), ForeignKey("elements.id", ondelete="SET NULL"), nullable=True)
    
    # Level/Storey information
    level_name = Column(String(100), nullable=True)
    level_elevation = Column(Float, nullable=True)
    
    # Classification
    classification = Column(JSON, nullable=True)
    # Example:
    # {
    #   "system": "Uniclass2015",
    #   "code": "Pr_20_93_63_05",
    #   "description": "Reinforced concrete beams"
    # }
    
    # Additional properties
    properties = Column(JSON, nullable=True)
    
    # Foreign Keys
    bim_model_id = Column(String(36), ForeignKey("bim_models.id", ondelete="CASCADE"), nullable=False)
    parent_element_id = Column(String(36), ForeignKey("bim_elements.id", ondelete="CASCADE"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bim_model = relationship("BIMModel", back_populates="bim_elements")
    structural_element = relationship("Element")
    parent_element = relationship("BIMElement", remote_side=[id])
    child_elements = relationship("BIMElement", back_populates="parent_element")
    bim_properties = relationship("BIMProperty", back_populates="bim_element", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<BIMElement(global_id={self.global_id}, type={self.element_type})>"


class BIMProperty(Base):
    """BIM property for storing element properties and metadata"""
    
    __tablename__ = "bim_properties"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    
    # Property identification
    property_set_name = Column(String(100), nullable=False)  # e.g., "Pset_BeamCommon"
    property_name = Column(String(100), nullable=False)      # e.g., "LoadBearing"
    property_type = Column(String(50), nullable=False)       # e.g., "IfcBoolean", "IfcReal", "IfcText"
    
    # Property value (stored as JSON for flexibility)
    property_value = Column(JSON, nullable=True)
    
    # Property metadata
    description = Column(Text, nullable=True)
    unit = Column(String(20), nullable=True)
    
    # IFC specific
    ifc_property_type = Column(String(50), nullable=True)  # e.g., "IfcPropertySingleValue"
    
    # Additional metadata
    is_read_only = Column(Boolean, default=False, nullable=False)
    is_calculated = Column(Boolean, default=False, nullable=False)
    calculation_formula = Column(Text, nullable=True)
    
    # Foreign Keys
    bim_element_id = Column(String(36), ForeignKey("bim_elements.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bim_element = relationship("BIMElement", back_populates="bim_properties")
    
    def __repr__(self) -> str:
        return f"<BIMProperty(set={self.property_set_name}, name={self.property_name})>"