"""
Element factory and validation for structural elements
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
from dataclasses import dataclass

from db.models.structural import Element, ElementType, Node
from core.exceptions import ModelError, ValidationError
from .geometry import Point3D, Vector3D, GeometryEngine


class ElementValidationRule(Enum):
    """Element validation rules"""
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    CONNECTIVITY = "connectivity"
    MATERIAL_COMPATIBILITY = "material_compatibility"
    SECTION_COMPATIBILITY = "section_compatibility"
    ORIENTATION = "orientation"


@dataclass
class ElementProperties:
    """Element properties container"""
    element_type: ElementType
    start_node_id: uuid.UUID
    end_node_id: Optional[uuid.UUID] = None
    material_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    orientation_angle: float = 0.0
    properties: Optional[Dict[str, Any]] = None
    label: Optional[str] = None


class ElementValidator:
    """Validator for structural elements"""
    
    def __init__(self):
        self.validation_rules = {
            ElementValidationRule.MIN_LENGTH: 1e-6,  # Minimum element length (m)
            ElementValidationRule.MAX_LENGTH: 1000.0,  # Maximum element length (m)
        }
    
    def set_validation_rule(self, rule: ElementValidationRule, value: Any) -> None:
        """Set validation rule value"""
        self.validation_rules[rule] = value
    
    def validate_element_geometry(self, start_node: Node, end_node: Optional[Node]) -> List[str]:
        """Validate element geometry"""
        errors = []
        
        if end_node is None:
            # Point element (no geometry validation needed)
            return errors
        
        # Check if nodes are the same
        if start_node.id == end_node.id:
            errors.append("Start and end nodes cannot be the same")
            return errors
        
        # Calculate element length
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        length = GeometryEngine.calculate_element_length(start_point, end_point)
        
        # Check minimum length
        min_length = self.validation_rules.get(ElementValidationRule.MIN_LENGTH, 1e-6)
        if length < min_length:
            errors.append(f"Element length ({length:.6f}m) is below minimum ({min_length}m)")
        
        # Check maximum length
        max_length = self.validation_rules.get(ElementValidationRule.MAX_LENGTH, 1000.0)
        if length > max_length:
            errors.append(f"Element length ({length:.2f}m) exceeds maximum ({max_length}m)")
        
        return errors
    
    def validate_element_type_compatibility(self, element_type: ElementType, 
                                          start_node: Node, end_node: Optional[Node]) -> List[str]:
        """Validate element type compatibility with connectivity"""
        errors = []
        
        # Point elements (springs, dampers) should not have end nodes
        point_elements = {ElementType.SPRING, ElementType.DAMPER}
        if element_type in point_elements and end_node is not None:
            errors.append(f"{element_type.value} elements should not have end nodes")
        
        # Line elements should have both start and end nodes
        line_elements = {ElementType.BEAM, ElementType.COLUMN, ElementType.BRACE, ElementType.TRUSS}
        if element_type in line_elements and end_node is None:
            errors.append(f"{element_type.value} elements must have both start and end nodes")
        
        # Area elements (shells, plates, walls, slabs) validation would require additional nodes
        area_elements = {ElementType.SHELL, ElementType.PLATE, ElementType.WALL, ElementType.SLAB}
        if element_type in area_elements:
            # For now, treat as line elements, but in full implementation would need corner nodes
            if end_node is None:
                errors.append(f"{element_type.value} elements require proper connectivity definition")
        
        return errors
    
    def validate_material_section_compatibility(self, element_type: ElementType,
                                              material_type: Optional[str],
                                              section_type: Optional[str]) -> List[str]:
        """Validate material and section compatibility"""
        errors = []
        
        if material_type is None or section_type is None:
            return errors  # Skip validation if not provided
        
        # Steel elements should use steel sections
        if material_type == "steel":
            steel_sections = {"i_section", "channel", "angle", "tee", "tube_rectangular", "tube_circular"}
            if section_type not in steel_sections:
                errors.append(f"Steel material incompatible with {section_type} section")
        
        # Concrete elements should use concrete sections
        elif material_type == "concrete":
            concrete_sections = {"rectangular", "circular", "custom"}
            if section_type not in concrete_sections:
                errors.append(f"Concrete material incompatible with {section_type} section")
        
        # Beam elements should not use circular sections (typically)
        if element_type == ElementType.BEAM and section_type == "circular":
            errors.append("Warning: Circular sections are uncommon for beam elements")
        
        return errors
    
    def validate_element_properties(self, properties: ElementProperties) -> List[str]:
        """Validate complete element properties"""
        errors = []
        
        # Validate orientation angle
        if not (-2 * 3.14159 <= properties.orientation_angle <= 2 * 3.14159):
            errors.append("Orientation angle should be between -2π and 2π radians")
        
        # Validate element-specific properties
        if properties.properties:
            errors.extend(self._validate_element_specific_properties(
                properties.element_type, properties.properties
            ))
        
        return errors
    
    def _validate_element_specific_properties(self, element_type: ElementType, 
                                            properties: Dict[str, Any]) -> List[str]:
        """Validate element-specific properties"""
        errors = []
        
        if element_type == ElementType.SPRING:
            if "stiffness" in properties:
                stiffness = properties["stiffness"]
                if not isinstance(stiffness, (int, float)) or stiffness <= 0:
                    errors.append("Spring stiffness must be a positive number")
        
        elif element_type == ElementType.DAMPER:
            if "damping_coefficient" in properties:
                damping = properties["damping_coefficient"]
                if not isinstance(damping, (int, float)) or damping < 0:
                    errors.append("Damping coefficient must be non-negative")
        
        elif element_type in {ElementType.SHELL, ElementType.PLATE, ElementType.WALL, ElementType.SLAB}:
            if "thickness" in properties:
                thickness = properties["thickness"]
                if not isinstance(thickness, (int, float)) or thickness <= 0:
                    errors.append("Element thickness must be positive")
        
        return errors


class ElementFactory:
    """Factory for creating structural elements"""
    
    def __init__(self):
        self.validator = ElementValidator()
        self.element_counter = 1
    
    def create_beam(self, start_node: Node, end_node: Node,
                   material_id: Optional[uuid.UUID] = None,
                   section_id: Optional[uuid.UUID] = None,
                   orientation_angle: float = 0.0,
                   label: Optional[str] = None) -> ElementProperties:
        """Create beam element"""
        return ElementProperties(
            element_type=ElementType.BEAM,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material_id,
            section_id=section_id,
            orientation_angle=orientation_angle,
            label=label or f"B{self.element_counter}"
        )
    
    def create_column(self, start_node: Node, end_node: Node,
                     material_id: Optional[uuid.UUID] = None,
                     section_id: Optional[uuid.UUID] = None,
                     orientation_angle: float = 0.0,
                     label: Optional[str] = None) -> ElementProperties:
        """Create column element"""
        return ElementProperties(
            element_type=ElementType.COLUMN,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material_id,
            section_id=section_id,
            orientation_angle=orientation_angle,
            label=label or f"C{self.element_counter}"
        )
    
    def create_brace(self, start_node: Node, end_node: Node,
                    material_id: Optional[uuid.UUID] = None,
                    section_id: Optional[uuid.UUID] = None,
                    orientation_angle: float = 0.0,
                    label: Optional[str] = None) -> ElementProperties:
        """Create brace element"""
        return ElementProperties(
            element_type=ElementType.BRACE,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material_id,
            section_id=section_id,
            orientation_angle=orientation_angle,
            label=label or f"BR{self.element_counter}"
        )
    
    def create_truss(self, start_node: Node, end_node: Node,
                    material_id: Optional[uuid.UUID] = None,
                    section_id: Optional[uuid.UUID] = None,
                    label: Optional[str] = None) -> ElementProperties:
        """Create truss element (pin-pin connections)"""
        return ElementProperties(
            element_type=ElementType.TRUSS,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material_id,
            section_id=section_id,
            orientation_angle=0.0,  # Truss elements don't need orientation
            label=label or f"T{self.element_counter}"
        )
    
    def create_spring(self, node: Node, stiffness: float,
                     direction: str = "all",
                     label: Optional[str] = None) -> ElementProperties:
        """Create spring element"""
        properties = {
            "stiffness": stiffness,
            "direction": direction  # "x", "y", "z", "all"
        }
        
        return ElementProperties(
            element_type=ElementType.SPRING,
            start_node_id=node.id,
            end_node_id=None,
            properties=properties,
            label=label or f"SP{self.element_counter}"
        )
    
    def create_damper(self, node: Node, damping_coefficient: float,
                     direction: str = "all",
                     label: Optional[str] = None) -> ElementProperties:
        """Create damper element"""
        properties = {
            "damping_coefficient": damping_coefficient,
            "direction": direction  # "x", "y", "z", "all"
        }
        
        return ElementProperties(
            element_type=ElementType.DAMPER,
            start_node_id=node.id,
            end_node_id=None,
            properties=properties,
            label=label or f"D{self.element_counter}"
        )
    
    def create_shell(self, corner_nodes: List[Node],
                    material_id: Optional[uuid.UUID] = None,
                    thickness: float = 0.1,
                    label: Optional[str] = None) -> ElementProperties:
        """Create shell element (simplified - using first two nodes)"""
        if len(corner_nodes) < 2:
            raise ModelError("Shell element requires at least 2 corner nodes")
        
        properties = {
            "thickness": thickness,
            "corner_nodes": [node.id for node in corner_nodes]
        }
        
        return ElementProperties(
            element_type=ElementType.SHELL,
            start_node_id=corner_nodes[0].id,
            end_node_id=corner_nodes[1].id if len(corner_nodes) > 1 else None,
            material_id=material_id,
            properties=properties,
            label=label or f"SH{self.element_counter}"
        )
    
    def create_wall(self, start_node: Node, end_node: Node,
                   material_id: Optional[uuid.UUID] = None,
                   thickness: float = 0.2,
                   height: float = 3.0,
                   label: Optional[str] = None) -> ElementProperties:
        """Create wall element"""
        properties = {
            "thickness": thickness,
            "height": height
        }
        
        return ElementProperties(
            element_type=ElementType.WALL,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material_id,
            properties=properties,
            label=label or f"W{self.element_counter}"
        )
    
    def create_slab(self, corner_nodes: List[Node],
                   material_id: Optional[uuid.UUID] = None,
                   thickness: float = 0.15,
                   label: Optional[str] = None) -> ElementProperties:
        """Create slab element"""
        if len(corner_nodes) < 3:
            raise ModelError("Slab element requires at least 3 corner nodes")
        
        properties = {
            "thickness": thickness,
            "corner_nodes": [node.id for node in corner_nodes]
        }
        
        return ElementProperties(
            element_type=ElementType.SLAB,
            start_node_id=corner_nodes[0].id,
            end_node_id=corner_nodes[1].id,
            material_id=material_id,
            properties=properties,
            label=label or f"SL{self.element_counter}"
        )
    
    def validate_and_create(self, element_props: ElementProperties,
                          start_node: Node, end_node: Optional[Node] = None) -> List[str]:
        """Validate element properties and return validation errors"""
        errors = []
        
        # Geometry validation
        errors.extend(self.validator.validate_element_geometry(start_node, end_node))
        
        # Type compatibility validation
        errors.extend(self.validator.validate_element_type_compatibility(
            element_props.element_type, start_node, end_node
        ))
        
        # Properties validation
        errors.extend(self.validator.validate_element_properties(element_props))
        
        if not errors:
            self.element_counter += 1
        
        return errors
    
    def get_element_length(self, start_node: Node, end_node: Node) -> float:
        """Calculate element length"""
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        return GeometryEngine.calculate_element_length(start_point, end_point)
    
    def get_element_direction_cosines(self, start_node: Node, end_node: Node) -> Tuple[float, float, float]:
        """Get element direction cosines"""
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        return GeometryEngine.calculate_element_direction_cosines(start_point, end_point)
    
    def get_element_local_axes(self, start_node: Node, end_node: Node, 
                              orientation_angle: float = 0.0) -> Dict[str, List[float]]:
        """Get element local coordinate system axes"""
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        
        coord_system = GeometryEngine.calculate_element_local_axes(
            start_point, end_point, orientation_angle
        )
        
        return {
            "x_axis": [coord_system.x_axis.x, coord_system.x_axis.y, coord_system.x_axis.z],
            "y_axis": [coord_system.y_axis.x, coord_system.y_axis.y, coord_system.y_axis.z],
            "z_axis": [coord_system.z_axis.x, coord_system.z_axis.y, coord_system.z_axis.z]
        }