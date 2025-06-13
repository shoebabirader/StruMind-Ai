"""
Boundary condition and support generation for structural analysis
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import uuid
import numpy as np

from db.models.structural import BoundaryCondition, Node
from core.exceptions import ValidationError
from core.modeling.geometry import Point3D, Vector3D


class SupportType(Enum):
    """Support type definitions"""
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER = "roller"
    FREE = "free"
    SPRING = "spring"
    DAMPER = "damper"
    CUSTOM = "custom"


class RestraintDirection(Enum):
    """Restraint direction definitions"""
    DX = "dx"  # Translation in X
    DY = "dy"  # Translation in Y
    DZ = "dz"  # Translation in Z
    RX = "rx"  # Rotation about X
    RY = "ry"  # Rotation about Y
    RZ = "rz"  # Rotation about Z


@dataclass
class SupportProperties:
    """Support properties container"""
    support_type: SupportType
    restraints: Dict[str, bool]
    spring_constants: Optional[Dict[str, float]] = None
    damping_constants: Optional[Dict[str, float]] = None
    settlement: Optional[Dict[str, float]] = None
    label: Optional[str] = None


class SupportGenerator:
    """Generator for boundary conditions and supports"""
    
    def __init__(self):
        self.support_counter = 1
    
    def create_fixed_support(self, node: Node, label: Optional[str] = None) -> SupportProperties:
        """Create fixed support (all DOFs restrained)"""
        return SupportProperties(
            support_type=SupportType.FIXED,
            restraints={
                "dx": True,
                "dy": True,
                "dz": True,
                "rx": True,
                "ry": True,
                "rz": True
            },
            label=label or f"FIXED_{self.support_counter}"
        )
    
    def create_pinned_support(self, node: Node, label: Optional[str] = None) -> SupportProperties:
        """Create pinned support (translations restrained, rotations free)"""
        return SupportProperties(
            support_type=SupportType.PINNED,
            restraints={
                "dx": True,
                "dy": True,
                "dz": True,
                "rx": False,
                "ry": False,
                "rz": False
            },
            label=label or f"PINNED_{self.support_counter}"
        )
    
    def create_roller_support(self, node: Node, direction: str = "z", 
                             label: Optional[str] = None) -> SupportProperties:
        """Create roller support (one translation free, others restrained)"""
        restraints = {
            "dx": True,
            "dy": True,
            "dz": True,
            "rx": False,
            "ry": False,
            "rz": False
        }
        
        # Free the specified direction
        if direction.lower() == "x":
            restraints["dx"] = False
        elif direction.lower() == "y":
            restraints["dy"] = False
        elif direction.lower() == "z":
            restraints["dz"] = False
        
        return SupportProperties(
            support_type=SupportType.ROLLER,
            restraints=restraints,
            label=label or f"ROLLER_{direction.upper()}_{self.support_counter}"
        )
    
    def create_spring_support(self, node: Node, spring_constants: Dict[str, float],
                             label: Optional[str] = None) -> SupportProperties:
        """Create spring support with specified spring constants"""
        # Validate spring constants
        valid_directions = ["dx", "dy", "dz", "rx", "ry", "rz"]
        for direction in spring_constants:
            if direction not in valid_directions:
                raise ValidationError(f"Invalid spring direction: {direction}")
            if spring_constants[direction] < 0:
                raise ValidationError(f"Spring constant for {direction} must be non-negative")
        
        # Set restraints based on spring constants (non-zero = restrained)
        restraints = {}
        for direction in valid_directions:
            restraints[direction] = spring_constants.get(direction, 0.0) > 0
        
        return SupportProperties(
            support_type=SupportType.SPRING,
            restraints=restraints,
            spring_constants=spring_constants,
            label=label or f"SPRING_{self.support_counter}"
        )
    
    def create_damper_support(self, node: Node, damping_constants: Dict[str, float],
                             label: Optional[str] = None) -> SupportProperties:
        """Create damper support with specified damping constants"""
        # Validate damping constants
        valid_directions = ["dx", "dy", "dz", "rx", "ry", "rz"]
        for direction in damping_constants:
            if direction not in valid_directions:
                raise ValidationError(f"Invalid damping direction: {direction}")
            if damping_constants[direction] < 0:
                raise ValidationError(f"Damping constant for {direction} must be non-negative")
        
        # Set restraints based on damping constants
        restraints = {}
        for direction in valid_directions:
            restraints[direction] = damping_constants.get(direction, 0.0) > 0
        
        return SupportProperties(
            support_type=SupportType.DAMPER,
            restraints=restraints,
            damping_constants=damping_constants,
            label=label or f"DAMPER_{self.support_counter}"
        )
    
    def create_custom_support(self, node: Node, restraints: Dict[str, bool],
                             spring_constants: Optional[Dict[str, float]] = None,
                             damping_constants: Optional[Dict[str, float]] = None,
                             label: Optional[str] = None) -> SupportProperties:
        """Create custom support with user-defined restraints"""
        # Validate restraints
        valid_directions = ["dx", "dy", "dz", "rx", "ry", "rz"]
        for direction in restraints:
            if direction not in valid_directions:
                raise ValidationError(f"Invalid restraint direction: {direction}")
        
        # Ensure all directions are specified
        complete_restraints = {}
        for direction in valid_directions:
            complete_restraints[direction] = restraints.get(direction, False)
        
        return SupportProperties(
            support_type=SupportType.CUSTOM,
            restraints=complete_restraints,
            spring_constants=spring_constants,
            damping_constants=damping_constants,
            label=label or f"CUSTOM_{self.support_counter}"
        )
    
    def create_settlement_support(self, node: Node, base_support: SupportProperties,
                                 settlement: Dict[str, float],
                                 label: Optional[str] = None) -> SupportProperties:
        """Create support with prescribed settlements"""
        # Validate settlement directions
        valid_directions = ["dx", "dy", "dz", "rx", "ry", "rz"]
        for direction in settlement:
            if direction not in valid_directions:
                raise ValidationError(f"Invalid settlement direction: {direction}")
        
        # Copy base support and add settlement
        support = SupportProperties(
            support_type=base_support.support_type,
            restraints=base_support.restraints.copy(),
            spring_constants=base_support.spring_constants,
            damping_constants=base_support.damping_constants,
            settlement=settlement,
            label=label or f"SETTLEMENT_{self.support_counter}"
        )
        
        return support
    
    def increment_counter(self):
        """Increment support counter"""
        self.support_counter += 1


class FoundationGenerator:
    """Generator for foundation boundary conditions"""
    
    def create_soil_spring_support(self, node: Node, soil_properties: Dict[str, float],
                                  foundation_area: float, foundation_type: str = "isolated",
                                  label: Optional[str] = None) -> SupportProperties:
        """Create soil spring support based on soil properties"""
        
        # Get soil parameters
        elastic_modulus = soil_properties.get("elastic_modulus", 20000)  # kPa
        poisson_ratio = soil_properties.get("poisson_ratio", 0.3)
        bearing_capacity = soil_properties.get("bearing_capacity", 200)  # kPa
        
        # Calculate spring constants based on foundation type
        if foundation_type == "isolated":
            # Isolated footing spring constants
            kz = self._calculate_vertical_spring_constant(
                elastic_modulus, poisson_ratio, foundation_area
            )
            kx = ky = kz * 0.75  # Horizontal springs typically 75% of vertical
            
            # Rotational springs
            foundation_dimension = np.sqrt(foundation_area)
            krx = kry = kz * foundation_dimension ** 2 / 12
            krz = krx * 0.5
            
        elif foundation_type == "mat":
            # Mat foundation spring constants (higher stiffness)
            kz = self._calculate_vertical_spring_constant(
                elastic_modulus, poisson_ratio, foundation_area
            ) * 1.5
            kx = ky = kz * 0.8
            
            # Higher rotational stiffness for mat foundations
            foundation_dimension = np.sqrt(foundation_area)
            krx = kry = kz * foundation_dimension ** 2 / 8
            krz = krx * 0.7
            
        else:
            raise ValidationError(f"Unknown foundation type: {foundation_type}")
        
        spring_constants = {
            "dx": kx,
            "dy": ky,
            "dz": kz,
            "rx": krx,
            "ry": kry,
            "rz": krz
        }
        
        return SupportProperties(
            support_type=SupportType.SPRING,
            restraints={
                "dx": True,
                "dy": True,
                "dz": True,
                "rx": True,
                "ry": True,
                "rz": True
            },
            spring_constants=spring_constants,
            label=label or f"SOIL_SPRING_{foundation_type.upper()}"
        )
    
    def _calculate_vertical_spring_constant(self, elastic_modulus: float,
                                          poisson_ratio: float,
                                          foundation_area: float) -> float:
        """Calculate vertical spring constant for foundation"""
        # Simplified formula based on elastic half-space theory
        equivalent_radius = np.sqrt(foundation_area / np.pi)
        shear_modulus = elastic_modulus / (2 * (1 + poisson_ratio))
        
        # Vertical spring constant
        kz = 4 * shear_modulus * equivalent_radius / (1 - poisson_ratio)
        
        return kz
    
    def create_pile_support(self, node: Node, pile_properties: Dict[str, float],
                           soil_layers: List[Dict[str, Any]],
                           label: Optional[str] = None) -> SupportProperties:
        """Create pile support with layered soil"""
        
        pile_diameter = pile_properties.get("diameter", 0.5)  # m
        pile_length = pile_properties.get("length", 10.0)  # m
        pile_elastic_modulus = pile_properties.get("elastic_modulus", 30000000)  # kPa
        
        # Calculate pile spring constants considering soil layers
        total_lateral_stiffness = 0.0
        total_vertical_stiffness = 0.0
        
        for layer in soil_layers:
            layer_thickness = layer.get("thickness", 1.0)
            layer_modulus = layer.get("elastic_modulus", 20000)
            layer_friction = layer.get("friction_angle", 30)
            
            # Simplified pile-soil interaction
            lateral_stiffness = layer_modulus * pile_diameter * layer_thickness / 10
            vertical_stiffness = layer_modulus * np.pi * pile_diameter * layer_thickness / 5
            
            total_lateral_stiffness += lateral_stiffness
            total_vertical_stiffness += vertical_stiffness
        
        # Add end bearing
        if soil_layers:
            end_layer = soil_layers[-1]
            end_bearing_modulus = end_layer.get("elastic_modulus", 20000)
            pile_area = np.pi * (pile_diameter / 2) ** 2
            end_bearing_stiffness = end_bearing_modulus * pile_area
            total_vertical_stiffness += end_bearing_stiffness
        
        # Rotational stiffness
        rotational_stiffness = total_lateral_stiffness * pile_length ** 2 / 12
        
        spring_constants = {
            "dx": total_lateral_stiffness,
            "dy": total_lateral_stiffness,
            "dz": total_vertical_stiffness,
            "rx": rotational_stiffness,
            "ry": rotational_stiffness,
            "rz": rotational_stiffness * 0.5
        }
        
        return SupportProperties(
            support_type=SupportType.SPRING,
            restraints={
                "dx": True,
                "dy": True,
                "dz": True,
                "rx": True,
                "ry": True,
                "rz": True
            },
            spring_constants=spring_constants,
            label=label or "PILE_SUPPORT"
        )


class BoundaryConditionValidator:
    """Validator for boundary conditions"""
    
    def validate_support_properties(self, support: SupportProperties) -> List[str]:
        """Validate support properties"""
        errors = []
        
        # Check restraints
        if not support.restraints:
            errors.append("Support restraints are required")
        else:
            valid_directions = ["dx", "dy", "dz", "rx", "ry", "rz"]
            for direction in support.restraints:
                if direction not in valid_directions:
                    errors.append(f"Invalid restraint direction: {direction}")
        
        # Validate spring constants if present
        if support.spring_constants:
            for direction, constant in support.spring_constants.items():
                if direction not in ["dx", "dy", "dz", "rx", "ry", "rz"]:
                    errors.append(f"Invalid spring direction: {direction}")
                if constant < 0:
                    errors.append(f"Spring constant for {direction} must be non-negative")
        
        # Validate damping constants if present
        if support.damping_constants:
            for direction, constant in support.damping_constants.items():
                if direction not in ["dx", "dy", "dz", "rx", "ry", "rz"]:
                    errors.append(f"Invalid damping direction: {direction}")
                if constant < 0:
                    errors.append(f"Damping constant for {direction} must be non-negative")
        
        # Check for at least one restraint
        if support.restraints and not any(support.restraints.values()):
            errors.append("Support must have at least one restrained degree of freedom")
        
        return errors
    
    def validate_foundation_properties(self, foundation_props: Dict[str, Any]) -> List[str]:
        """Validate foundation properties"""
        errors = []
        
        if "foundation_area" in foundation_props:
            if foundation_props["foundation_area"] <= 0:
                errors.append("Foundation area must be positive")
        
        if "soil_properties" in foundation_props:
            soil_props = foundation_props["soil_properties"]
            
            if "elastic_modulus" in soil_props:
                if soil_props["elastic_modulus"] <= 0:
                    errors.append("Soil elastic modulus must be positive")
            
            if "poisson_ratio" in soil_props:
                poisson = soil_props["poisson_ratio"]
                if not (0 <= poisson < 0.5):
                    errors.append("Poisson ratio must be between 0 and 0.5")
            
            if "bearing_capacity" in soil_props:
                if soil_props["bearing_capacity"] <= 0:
                    errors.append("Bearing capacity must be positive")
        
        return errors
    
    def check_model_stability(self, supports: List[SupportProperties],
                             nodes: List[Node]) -> List[str]:
        """Check if support configuration provides model stability"""
        warnings = []
        
        # Count total restraints
        total_restraints = {"dx": 0, "dy": 0, "dz": 0, "rx": 0, "ry": 0, "rz": 0}
        
        for support in supports:
            for direction, restrained in support.restraints.items():
                if restrained:
                    total_restraints[direction] += 1
        
        # Check minimum restraints for stability
        if total_restraints["dx"] == 0:
            warnings.append("No X-direction restraints - model may be unstable")
        
        if total_restraints["dy"] == 0:
            warnings.append("No Y-direction restraints - model may be unstable")
        
        if total_restraints["dz"] == 0:
            warnings.append("No Z-direction restraints - model may be unstable")
        
        # Check for rigid body modes
        total_nodes = len(nodes)
        if total_nodes > 1:
            min_restraints_needed = 6  # 3 translations + 3 rotations for 3D
            total_applied = sum(total_restraints.values())
            
            if total_applied < min_restraints_needed:
                warnings.append(f"Insufficient restraints ({total_applied}) for stability. "
                               f"Minimum {min_restraints_needed} needed for 3D structure")
        
        return warnings


class SupportPatternGenerator:
    """Generator for common support patterns"""
    
    def create_building_base_supports(self, base_nodes: List[Node],
                                     support_type: str = "fixed") -> List[SupportProperties]:
        """Create typical building base supports"""
        supports = []
        generator = SupportGenerator()
        
        for i, node in enumerate(base_nodes):
            if support_type == "fixed":
                support = generator.create_fixed_support(node, f"BASE_FIXED_{i+1}")
            elif support_type == "pinned":
                support = generator.create_pinned_support(node, f"BASE_PINNED_{i+1}")
            else:
                raise ValidationError(f"Unknown support type: {support_type}")
            
            supports.append(support)
            generator.increment_counter()
        
        return supports
    
    def create_bridge_supports(self, pier_nodes: List[Node], abutment_nodes: List[Node]) -> List[SupportProperties]:
        """Create typical bridge support pattern"""
        supports = []
        generator = SupportGenerator()
        
        # Abutments - typically fixed or pinned
        for i, node in enumerate(abutment_nodes):
            support = generator.create_fixed_support(node, f"ABUTMENT_{i+1}")
            supports.append(support)
            generator.increment_counter()
        
        # Piers - typically pinned to allow thermal movement
        for i, node in enumerate(pier_nodes):
            support = generator.create_pinned_support(node, f"PIER_{i+1}")
            supports.append(support)
            generator.increment_counter()
        
        return supports
    
    def create_truss_supports(self, support_nodes: List[Node]) -> List[SupportProperties]:
        """Create typical truss support pattern"""
        supports = []
        generator = SupportGenerator()
        
        if len(support_nodes) >= 2:
            # First support - fixed
            support1 = generator.create_fixed_support(support_nodes[0], "TRUSS_FIXED")
            supports.append(support1)
            generator.increment_counter()
            
            # Second support - roller in X direction
            support2 = generator.create_roller_support(support_nodes[1], "x", "TRUSS_ROLLER")
            supports.append(support2)
            generator.increment_counter()
            
            # Additional supports - rollers
            for i, node in enumerate(support_nodes[2:], start=3):
                support = generator.create_roller_support(node, "x", f"TRUSS_ROLLER_{i}")
                supports.append(support)
                generator.increment_counter()
        
        return supports