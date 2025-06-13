"""
Load generation and application for structural analysis
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import uuid
import numpy as np

from db.models.structural import Load, LoadType, Node, Element
from core.exceptions import ValidationError
from core.modeling.geometry import Point3D, Vector3D


class LoadPattern(Enum):
    """Load pattern types"""
    DEAD = "dead"
    LIVE = "live"
    WIND = "wind"
    SEISMIC = "seismic"
    SNOW = "snow"
    TEMPERATURE = "temperature"
    CONSTRUCTION = "construction"


class LoadDirection(Enum):
    """Load direction types"""
    GLOBAL_X = "global_x"
    GLOBAL_Y = "global_y"
    GLOBAL_Z = "global_z"
    LOCAL_X = "local_x"
    LOCAL_Y = "local_y"
    LOCAL_Z = "local_z"


@dataclass
class LoadCase:
    """Load case definition"""
    name: str
    pattern: LoadPattern
    factor: float = 1.0
    description: Optional[str] = None


@dataclass
class LoadCombination:
    """Load combination definition"""
    name: str
    load_cases: List[Tuple[str, float]]  # (load_case_name, factor)
    combination_type: str = "linear"  # linear, envelope, etc.
    description: Optional[str] = None


class PointLoadGenerator:
    """Generator for point loads"""
    
    def create_nodal_load(self, node: Node, force_x: float = 0.0, force_y: float = 0.0, 
                         force_z: float = 0.0, moment_x: float = 0.0, moment_y: float = 0.0, 
                         moment_z: float = 0.0, load_case: str = "DEAD") -> Dict[str, Any]:
        """Create nodal point load"""
        return {
            "load_type": LoadType.POINT,
            "load_case": load_case,
            "node_id": node.id,
            "values": {
                "fx": force_x,
                "fy": force_y,
                "fz": force_z,
                "mx": moment_x,
                "my": moment_y,
                "mz": moment_z,
                "coordinate_system": "global"
            }
        }
    
    def create_element_point_load(self, element: Element, force_x: float = 0.0, 
                                 force_y: float = 0.0, force_z: float = 0.0,
                                 position: float = 0.5, load_case: str = "LIVE",
                                 coordinate_system: str = "local") -> Dict[str, Any]:
        """Create point load on element"""
        if not (0.0 <= position <= 1.0):
            raise ValidationError("Position must be between 0.0 and 1.0")
        
        return {
            "load_type": LoadType.POINT,
            "load_case": load_case,
            "element_id": element.id,
            "values": {
                "fx": force_x,
                "fy": force_y,
                "fz": force_z,
                "position": position,
                "coordinate_system": coordinate_system
            }
        }


class DistributedLoadGenerator:
    """Generator for distributed loads"""
    
    def create_uniform_load(self, element: Element, load_x: float = 0.0, 
                           load_y: float = 0.0, load_z: float = 0.0,
                           load_case: str = "DEAD", coordinate_system: str = "local") -> Dict[str, Any]:
        """Create uniform distributed load"""
        return {
            "load_type": LoadType.DISTRIBUTED,
            "load_case": load_case,
            "element_id": element.id,
            "values": {
                "wx": load_x,
                "wy": load_y,
                "wz": load_z,
                "distribution": "uniform",
                "coordinate_system": coordinate_system
            }
        }
    
    def create_trapezoidal_load(self, element: Element, start_load_x: float = 0.0,
                               start_load_y: float = 0.0, start_load_z: float = 0.0,
                               end_load_x: float = 0.0, end_load_y: float = 0.0,
                               end_load_z: float = 0.0, load_case: str = "LIVE",
                               coordinate_system: str = "local") -> Dict[str, Any]:
        """Create trapezoidal distributed load"""
        return {
            "load_type": LoadType.DISTRIBUTED,
            "load_case": load_case,
            "element_id": element.id,
            "values": {
                "wx_start": start_load_x,
                "wy_start": start_load_y,
                "wz_start": start_load_z,
                "wx_end": end_load_x,
                "wy_end": end_load_y,
                "wz_end": end_load_z,
                "distribution": "trapezoidal",
                "coordinate_system": coordinate_system
            }
        }
    
    def create_triangular_load(self, element: Element, peak_load_x: float = 0.0,
                              peak_load_y: float = 0.0, peak_load_z: float = 0.0,
                              peak_position: float = 0.5, load_case: str = "LIVE",
                              coordinate_system: str = "local") -> Dict[str, Any]:
        """Create triangular distributed load"""
        if not (0.0 <= peak_position <= 1.0):
            raise ValidationError("Peak position must be between 0.0 and 1.0")
        
        return {
            "load_type": LoadType.DISTRIBUTED,
            "load_case": load_case,
            "element_id": element.id,
            "values": {
                "wx_peak": peak_load_x,
                "wy_peak": peak_load_y,
                "wz_peak": peak_load_z,
                "peak_position": peak_position,
                "distribution": "triangular",
                "coordinate_system": coordinate_system
            }
        }


class AreaLoadGenerator:
    """Generator for area loads"""
    
    def create_uniform_area_load(self, elements: List[Element], pressure: float,
                                direction: LoadDirection = LoadDirection.GLOBAL_Z,
                                load_case: str = "DEAD") -> List[Dict[str, Any]]:
        """Create uniform area load on shell/plate elements"""
        loads = []
        
        for element in elements:
            if element.element_type not in ["SHELL", "PLATE", "WALL", "SLAB"]:
                raise ValidationError(f"Area loads can only be applied to area elements, not {element.element_type}")
            
            loads.append({
                "load_type": LoadType.AREA,
                "load_case": load_case,
                "element_id": element.id,
                "values": {
                    "pressure": pressure,
                    "direction": direction.value,
                    "distribution": "uniform"
                }
            })
        
        return loads
    
    def create_hydrostatic_load(self, elements: List[Element], fluid_density: float,
                               water_level: float, gravity: float = 9.81,
                               load_case: str = "HYDROSTATIC") -> List[Dict[str, Any]]:
        """Create hydrostatic pressure load"""
        loads = []
        
        for element in elements:
            loads.append({
                "load_type": LoadType.AREA,
                "load_case": load_case,
                "element_id": element.id,
                "values": {
                    "fluid_density": fluid_density,
                    "water_level": water_level,
                    "gravity": gravity,
                    "distribution": "hydrostatic"
                }
            })
        
        return loads


class WindLoadGenerator:
    """Generator for wind loads based on building codes"""
    
    def __init__(self, wind_speed: float, exposure_category: str = "C",
                 importance_factor: float = 1.0, topographic_factor: float = 1.0):
        self.wind_speed = wind_speed  # m/s
        self.exposure_category = exposure_category
        self.importance_factor = importance_factor
        self.topographic_factor = topographic_factor
    
    def calculate_wind_pressure(self, height: float, gust_factor: float = 0.85) -> float:
        """Calculate wind pressure based on ASCE 7"""
        # Simplified wind pressure calculation
        velocity_pressure = 0.613 * (self.wind_speed ** 2)  # Pa
        exposure_coefficient = self._get_exposure_coefficient(height)
        
        wind_pressure = velocity_pressure * exposure_coefficient * gust_factor * \
                       self.importance_factor * self.topographic_factor
        
        return wind_pressure / 1000.0  # Convert to kPa
    
    def _get_exposure_coefficient(self, height: float) -> float:
        """Get exposure coefficient based on height and exposure category"""
        if self.exposure_category == "B":
            return min(1.0, 0.7 * (height / 10.0) ** 0.3)
        elif self.exposure_category == "C":
            return min(1.2, 0.85 * (height / 10.0) ** 0.22)
        elif self.exposure_category == "D":
            return min(1.4, 1.0 * (height / 10.0) ** 0.15)
        else:
            return 1.0
    
    def generate_wind_loads(self, elements: List[Element], building_height: float,
                           building_width: float, wind_direction: float = 0.0,
                           load_case: str = "WIND") -> List[Dict[str, Any]]:
        """Generate wind loads on building elements"""
        loads = []
        
        for element in elements:
            # Get element centroid height (simplified)
            element_height = building_height / 2.0  # Simplified assumption
            
            wind_pressure = self.calculate_wind_pressure(element_height)
            
            # Apply pressure coefficient based on element location
            pressure_coefficient = self._get_pressure_coefficient(element, wind_direction)
            final_pressure = wind_pressure * pressure_coefficient
            
            loads.append({
                "load_type": LoadType.WIND,
                "load_case": load_case,
                "element_id": element.id,
                "values": {
                    "pressure": final_pressure,
                    "wind_speed": self.wind_speed,
                    "wind_direction": wind_direction,
                    "height": element_height,
                    "pressure_coefficient": pressure_coefficient
                }
            })
        
        return loads
    
    def _get_pressure_coefficient(self, element: Element, wind_direction: float) -> float:
        """Get pressure coefficient based on element location and wind direction"""
        # Simplified pressure coefficients
        # In practice, this would be much more complex based on building geometry
        return 0.8  # Windward face coefficient


class SeismicLoadGenerator:
    """Generator for seismic loads based on building codes"""
    
    def __init__(self, seismic_zone: str, soil_type: str = "II",
                 importance_factor: float = 1.0, response_reduction_factor: float = 5.0):
        self.seismic_zone = seismic_zone
        self.soil_type = soil_type
        self.importance_factor = importance_factor
        self.response_reduction_factor = response_reduction_factor
    
    def calculate_base_shear(self, total_weight: float, fundamental_period: float) -> float:
        """Calculate seismic base shear"""
        # Simplified base shear calculation (IS 1893 approach)
        zone_factor = self._get_zone_factor()
        soil_factor = self._get_soil_factor()
        
        # Response acceleration coefficient
        if fundamental_period <= 0.1:
            sa_g = 2.5
        elif fundamental_period <= 0.4:
            sa_g = 2.5
        elif fundamental_period <= 4.0:
            sa_g = 1.0 / fundamental_period
        else:
            sa_g = 0.25
        
        base_shear = (zone_factor * self.importance_factor * sa_g * total_weight) / \
                    (self.response_reduction_factor * soil_factor)
        
        return base_shear
    
    def _get_zone_factor(self) -> float:
        """Get seismic zone factor"""
        zone_factors = {
            "II": 0.10,
            "III": 0.16,
            "IV": 0.24,
            "V": 0.36
        }
        return zone_factors.get(self.seismic_zone, 0.16)
    
    def _get_soil_factor(self) -> float:
        """Get soil factor"""
        soil_factors = {
            "I": 1.0,
            "II": 1.2,
            "III": 1.5
        }
        return soil_factors.get(self.soil_type, 1.2)
    
    def generate_seismic_loads(self, nodes: List[Node], floor_weights: Dict[float, float],
                              fundamental_period: float, load_case: str = "SEISMIC") -> List[Dict[str, Any]]:
        """Generate seismic loads distributed to nodes"""
        loads = []
        
        # Calculate total weight
        total_weight = sum(floor_weights.values())
        base_shear = self.calculate_base_shear(total_weight, fundamental_period)
        
        # Distribute base shear to floors based on height and weight
        for node in nodes:
            node_height = node.z
            if node_height in floor_weights:
                floor_weight = floor_weights[node_height]
                
                # Calculate floor force using inverted triangle distribution
                numerator = floor_weight * node_height
                denominator = sum(w * h for h, w in floor_weights.items())
                
                if denominator > 0:
                    floor_force = base_shear * numerator / denominator
                    
                    loads.append({
                        "load_type": LoadType.SEISMIC,
                        "load_case": load_case,
                        "node_id": node.id,
                        "values": {
                            "fx": floor_force,  # Assuming X-direction seismic
                            "fy": 0.0,
                            "fz": 0.0,
                            "height": node_height,
                            "floor_weight": floor_weight,
                            "base_shear": base_shear
                        }
                    })
        
        return loads


class LoadCombinationGenerator:
    """Generator for load combinations based on building codes"""
    
    def generate_asce_combinations(self, load_cases: List[str]) -> List[LoadCombination]:
        """Generate ASCE 7 load combinations"""
        combinations = []
        
        # Basic combinations
        if "DEAD" in load_cases:
            combinations.append(LoadCombination(
                name="1.4D",
                load_cases=[("DEAD", 1.4)],
                description="1.4 times dead load"
            ))
        
        if "DEAD" in load_cases and "LIVE" in load_cases:
            combinations.append(LoadCombination(
                name="1.2D + 1.6L",
                load_cases=[("DEAD", 1.2), ("LIVE", 1.6)],
                description="1.2 times dead plus 1.6 times live"
            ))
        
        if "DEAD" in load_cases and "WIND" in load_cases:
            combinations.append(LoadCombination(
                name="1.2D + 1.0W",
                load_cases=[("DEAD", 1.2), ("WIND", 1.0)],
                description="1.2 times dead plus wind"
            ))
        
        if "DEAD" in load_cases and "LIVE" in load_cases and "WIND" in load_cases:
            combinations.append(LoadCombination(
                name="1.2D + 1.0L + 1.0W",
                load_cases=[("DEAD", 1.2), ("LIVE", 1.0), ("WIND", 1.0)],
                description="1.2 times dead plus live plus wind"
            ))
        
        if "DEAD" in load_cases and "SEISMIC" in load_cases:
            combinations.append(LoadCombination(
                name="1.2D + 1.0E",
                load_cases=[("DEAD", 1.2), ("SEISMIC", 1.0)],
                description="1.2 times dead plus seismic"
            ))
        
        return combinations
    
    def generate_is_combinations(self, load_cases: List[str]) -> List[LoadCombination]:
        """Generate IS 456/IS 1893 load combinations"""
        combinations = []
        
        # Basic combinations for IS codes
        if "DEAD" in load_cases:
            combinations.append(LoadCombination(
                name="1.5DL",
                load_cases=[("DEAD", 1.5)],
                description="1.5 times dead load"
            ))
        
        if "DEAD" in load_cases and "LIVE" in load_cases:
            combinations.append(LoadCombination(
                name="1.5(DL + LL)",
                load_cases=[("DEAD", 1.5), ("LIVE", 1.5)],
                description="1.5 times (dead plus live)"
            ))
        
        if "DEAD" in load_cases and "WIND" in load_cases:
            combinations.append(LoadCombination(
                name="1.2(DL + WL)",
                load_cases=[("DEAD", 1.2), ("WIND", 1.2)],
                description="1.2 times (dead plus wind)"
            ))
        
        if "DEAD" in load_cases and "SEISMIC" in load_cases:
            combinations.append(LoadCombination(
                name="1.2(DL + EL)",
                load_cases=[("DEAD", 1.2), ("SEISMIC", 1.2)],
                description="1.2 times (dead plus seismic)"
            ))
        
        return combinations


class LoadValidator:
    """Validator for load definitions"""
    
    def validate_load(self, load_data: Dict[str, Any]) -> List[str]:
        """Validate load data"""
        errors = []
        
        # Check required fields
        if "load_type" not in load_data:
            errors.append("Load type is required")
        
        if "load_case" not in load_data:
            errors.append("Load case is required")
        
        if "values" not in load_data:
            errors.append("Load values are required")
        
        # Validate load values
        if "values" in load_data:
            values = load_data["values"]
            
            # Check for numeric values
            for key, value in values.items():
                if key in ["fx", "fy", "fz", "mx", "my", "mz", "wx", "wy", "wz", "pressure"]:
                    if not isinstance(value, (int, float)):
                        errors.append(f"Load value {key} must be numeric")
        
        # Validate load type specific requirements
        load_type = load_data.get("load_type")
        if load_type == LoadType.POINT:
            if "node_id" not in load_data and "element_id" not in load_data:
                errors.append("Point loads require either node_id or element_id")
        
        elif load_type == LoadType.DISTRIBUTED:
            if "element_id" not in load_data:
                errors.append("Distributed loads require element_id")
        
        elif load_type == LoadType.AREA:
            if "element_id" not in load_data:
                errors.append("Area loads require element_id")
        
        return errors
    
    def validate_load_combination(self, combination: LoadCombination,
                                 available_cases: List[str]) -> List[str]:
        """Validate load combination"""
        errors = []
        
        if not combination.name:
            errors.append("Load combination name is required")
        
        if not combination.load_cases:
            errors.append("Load combination must include at least one load case")
        
        for case_name, factor in combination.load_cases:
            if case_name not in available_cases:
                errors.append(f"Load case '{case_name}' not found in available cases")
            
            if not isinstance(factor, (int, float)):
                errors.append(f"Load factor for case '{case_name}' must be numeric")
        
        return errors