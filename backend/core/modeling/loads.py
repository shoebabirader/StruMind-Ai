"""
Load generation and validation module for StruMind
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np
from pydantic import BaseModel, Field

from .geometry import Point3D, Vector3D


class LoadType(str, Enum):
    """Types of loads"""
    POINT = "point"
    DISTRIBUTED = "distributed"
    AREA = "area"
    WIND = "wind"
    SEISMIC = "seismic"
    THERMAL = "thermal"
    SETTLEMENT = "settlement"


class LoadDirection(str, Enum):
    """Load direction types"""
    GLOBAL_X = "global_x"
    GLOBAL_Y = "global_y"
    GLOBAL_Z = "global_z"
    LOCAL_X = "local_x"
    LOCAL_Y = "local_y"
    LOCAL_Z = "local_z"


class LoadCase(BaseModel):
    """Load case definition"""
    id: str
    name: str
    description: Optional[str] = None
    load_type: str = "static"
    factor: float = 1.0
    is_active: bool = True


class LoadCombination(BaseModel):
    """Load combination definition"""
    id: str
    name: str
    description: Optional[str] = None
    load_cases: Dict[str, float] = Field(default_factory=dict)  # case_id: factor
    combination_type: str = "linear"  # linear, envelope, etc.


class PointLoad(BaseModel):
    """Point load definition"""
    id: str
    node_id: str
    force_x: float = 0.0
    force_y: float = 0.0
    force_z: float = 0.0
    moment_x: float = 0.0
    moment_y: float = 0.0
    moment_z: float = 0.0
    load_case_id: str
    coordinate_system: str = "global"


class DistributedLoad(BaseModel):
    """Distributed load on elements"""
    id: str
    element_id: str
    load_type: str = "uniform"  # uniform, trapezoidal, triangular
    direction: LoadDirection
    magnitude_start: float
    magnitude_end: Optional[float] = None
    position_start: float = 0.0  # relative position along element
    position_end: float = 1.0
    load_case_id: str
    coordinate_system: str = "local"


class AreaLoad(BaseModel):
    """Area load on surfaces"""
    id: str
    surface_ids: List[str]
    pressure: float
    direction: LoadDirection = LoadDirection.GLOBAL_Z
    load_case_id: str
    coordinate_system: str = "global"


class WindLoad(BaseModel):
    """Wind load parameters"""
    id: str
    wind_speed: float  # m/s
    wind_direction: float  # degrees from north
    exposure_category: str = "B"  # A, B, C, D
    importance_factor: float = 1.0
    topographic_factor: float = 1.0
    directionality_factor: float = 0.85
    code_standard: str = "ASCE7"
    load_case_id: str


class SeismicLoad(BaseModel):
    """Seismic load parameters"""
    id: str
    zone_factor: float
    importance_factor: float = 1.0
    response_reduction_factor: float = 5.0
    soil_type: str = "II"
    damping_ratio: float = 0.05
    code_standard: str = "IS1893"
    load_case_id: str


class LoadGenerator:
    """Load generation utilities"""
    
    def __init__(self):
        self.load_cases: Dict[str, LoadCase] = {}
        self.load_combinations: Dict[str, LoadCombination] = {}
        self.point_loads: Dict[str, PointLoad] = {}
        self.distributed_loads: Dict[str, DistributedLoad] = {}
        self.area_loads: Dict[str, AreaLoad] = {}
        self.wind_loads: Dict[str, WindLoad] = {}
        self.seismic_loads: Dict[str, SeismicLoad] = {}
    
    def create_load_case(self, name: str, description: str = None, 
                        load_type: str = "static") -> LoadCase:
        """Create a new load case"""
        case_id = f"LC_{len(self.load_cases) + 1:03d}"
        load_case = LoadCase(
            id=case_id,
            name=name,
            description=description,
            load_type=load_type
        )
        self.load_cases[case_id] = load_case
        return load_case
    
    def create_load_combination(self, name: str, 
                               case_factors: Dict[str, float]) -> LoadCombination:
        """Create a load combination"""
        combo_id = f"COMBO_{len(self.load_combinations) + 1:03d}"
        combination = LoadCombination(
            id=combo_id,
            name=name,
            load_cases=case_factors
        )
        self.load_combinations[combo_id] = combination
        return combination
    
    def add_point_load(self, node_id: str, load_case_id: str,
                      fx: float = 0, fy: float = 0, fz: float = 0,
                      mx: float = 0, my: float = 0, mz: float = 0) -> PointLoad:
        """Add point load to a node"""
        load_id = f"PL_{len(self.point_loads) + 1:04d}"
        point_load = PointLoad(
            id=load_id,
            node_id=node_id,
            force_x=fx,
            force_y=fy,
            force_z=fz,
            moment_x=mx,
            moment_y=my,
            moment_z=mz,
            load_case_id=load_case_id
        )
        self.point_loads[load_id] = point_load
        return point_load
    
    def add_distributed_load(self, element_id: str, load_case_id: str,
                           direction: LoadDirection, magnitude: float,
                           load_type: str = "uniform") -> DistributedLoad:
        """Add distributed load to an element"""
        load_id = f"DL_{len(self.distributed_loads) + 1:04d}"
        dist_load = DistributedLoad(
            id=load_id,
            element_id=element_id,
            load_type=load_type,
            direction=direction,
            magnitude_start=magnitude,
            magnitude_end=magnitude if load_type == "uniform" else None,
            load_case_id=load_case_id
        )
        self.distributed_loads[load_id] = dist_load
        return dist_load
    
    def add_area_load(self, surface_ids: List[str], load_case_id: str,
                     pressure: float, direction: LoadDirection = LoadDirection.GLOBAL_Z) -> AreaLoad:
        """Add area load to surfaces"""
        load_id = f"AL_{len(self.area_loads) + 1:04d}"
        area_load = AreaLoad(
            id=load_id,
            surface_ids=surface_ids,
            pressure=pressure,
            direction=direction,
            load_case_id=load_case_id
        )
        self.area_loads[load_id] = area_load
        return area_load
    
    def generate_wind_loads(self, wind_speed: float, wind_direction: float,
                          structure_height: float, structure_width: float,
                          code_standard: str = "ASCE7") -> List[AreaLoad]:
        """Generate wind loads based on code standards"""
        # Create wind load case
        wind_case = self.create_load_case("Wind Load", "Auto-generated wind loads")
        
        # Basic wind pressure calculation (simplified)
        if code_standard == "ASCE7":
            # qz = 0.613 * Kz * Kzt * Kd * V^2 * I (in Pa)
            Kz = 0.85  # Exposure factor (simplified)
            Kzt = 1.0  # Topographic factor
            Kd = 0.85  # Directionality factor
            I = 1.0    # Importance factor
            
            qz = 0.613 * Kz * Kzt * Kd * (wind_speed ** 2) * I
            
            # Pressure coefficients (simplified)
            Cp_windward = 0.8
            Cp_leeward = -0.5
            
            # Generate loads (this is a simplified example)
            wind_loads = []
            # In practice, this would generate loads on all exposed surfaces
            
        return wind_loads
    
    def generate_seismic_loads(self, zone_factor: float, importance_factor: float,
                             structure_mass: float, fundamental_period: float,
                             code_standard: str = "IS1893") -> List[PointLoad]:
        """Generate seismic loads based on code standards"""
        # Create seismic load case
        seismic_case = self.create_load_case("Seismic Load", "Auto-generated seismic loads")
        
        # Basic seismic force calculation (simplified)
        if code_standard == "IS1893":
            # Base shear: V = Ah * W
            # where Ah = (Z/2) * (I/R) * (Sa/g)
            
            R = 5.0  # Response reduction factor
            Sa_g = 2.5  # Response acceleration coefficient (simplified)
            
            Ah = (zone_factor / 2) * (importance_factor / R) * Sa_g
            base_shear = Ah * structure_mass * 9.81  # Convert to force
            
            # Distribute loads (simplified - would be more complex in practice)
            seismic_loads = []
            
        return seismic_loads
    
    def get_load_summary(self) -> Dict[str, Any]:
        """Get summary of all loads"""
        return {
            "load_cases": len(self.load_cases),
            "load_combinations": len(self.load_combinations),
            "point_loads": len(self.point_loads),
            "distributed_loads": len(self.distributed_loads),
            "area_loads": len(self.area_loads),
            "wind_loads": len(self.wind_loads),
            "seismic_loads": len(self.seismic_loads)
        }


class LoadValidator:
    """Load validation utilities"""
    
    @staticmethod
    def validate_load_case(load_case: LoadCase) -> List[str]:
        """Validate load case definition"""
        errors = []
        
        if not load_case.name.strip():
            errors.append("Load case name cannot be empty")
        
        if load_case.factor <= 0:
            errors.append("Load factor must be positive")
        
        return errors
    
    @staticmethod
    def validate_point_load(point_load: PointLoad) -> List[str]:
        """Validate point load definition"""
        errors = []
        
        # Check if at least one force/moment component is non-zero
        forces = [point_load.force_x, point_load.force_y, point_load.force_z,
                 point_load.moment_x, point_load.moment_y, point_load.moment_z]
        
        if all(abs(f) < 1e-12 for f in forces):
            errors.append("Point load has zero magnitude")
        
        return errors
    
    @staticmethod
    def validate_distributed_load(dist_load: DistributedLoad) -> List[str]:
        """Validate distributed load definition"""
        errors = []
        
        if abs(dist_load.magnitude_start) < 1e-12:
            if dist_load.magnitude_end is None or abs(dist_load.magnitude_end) < 1e-12:
                errors.append("Distributed load has zero magnitude")
        
        if dist_load.position_start < 0 or dist_load.position_start > 1:
            errors.append("Start position must be between 0 and 1")
        
        if dist_load.position_end < 0 or dist_load.position_end > 1:
            errors.append("End position must be between 0 and 1")
        
        if dist_load.position_start >= dist_load.position_end:
            errors.append("Start position must be less than end position")
        
        return errors
    
    @staticmethod
    def validate_load_combination(combination: LoadCombination,
                                available_cases: List[str]) -> List[str]:
        """Validate load combination"""
        errors = []
        
        if not combination.load_cases:
            errors.append("Load combination must include at least one load case")
        
        for case_id in combination.load_cases:
            if case_id not in available_cases:
                errors.append(f"Load case {case_id} not found")
        
        return errors
    
    @staticmethod
    def check_load_equilibrium(point_loads: List[PointLoad],
                             distributed_loads: List[DistributedLoad]) -> Dict[str, float]:
        """Check static equilibrium of loads (simplified)"""
        total_fx = sum(load.force_x for load in point_loads)
        total_fy = sum(load.force_y for load in point_loads)
        total_fz = sum(load.force_z for load in point_loads)
        
        # Add distributed loads (simplified - would need element geometry)
        # This is a placeholder for more complex equilibrium checking
        
        return {
            "sum_fx": total_fx,
            "sum_fy": total_fy,
            "sum_fz": total_fz,
            "is_equilibrium": abs(total_fx) + abs(total_fy) + abs(total_fz) < 1e-6
        }