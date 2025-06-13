"""
Boundary conditions management for StruMind
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from pydantic import BaseModel, Field

from .geometry import Point3D, Vector3D


class RestraintType(str, Enum):
    """Types of restraints"""
    FIXED = "fixed"
    PINNED = "pinned"
    ROLLER = "roller"
    FREE = "free"
    SPRING = "spring"
    CUSTOM = "custom"


class BoundaryCondition(BaseModel):
    """Boundary condition definition"""
    id: str = Field(default_factory=lambda: f"BC_{uuid.uuid4().hex[:8]}")
    node_id: str
    restraints: Dict[str, bool] = Field(default_factory=lambda: {
        "ux": False,  # Translation in X
        "uy": False,  # Translation in Y
        "uz": False,  # Translation in Z
        "rx": False,  # Rotation about X
        "ry": False,  # Rotation about Y
        "rz": False   # Rotation about Z
    })
    spring_constants: Dict[str, float] = Field(default_factory=lambda: {
        "kx": 0.0,    # Spring constant in X
        "ky": 0.0,    # Spring constant in Y
        "kz": 0.0,    # Spring constant in Z
        "krx": 0.0,   # Rotational spring about X
        "kry": 0.0,   # Rotational spring about Y
        "krz": 0.0    # Rotational spring about Z
    })
    prescribed_displacements: Dict[str, float] = Field(default_factory=lambda: {
        "ux": 0.0,
        "uy": 0.0,
        "uz": 0.0,
        "rx": 0.0,
        "ry": 0.0,
        "rz": 0.0
    })
    restraint_type: RestraintType = RestraintType.CUSTOM
    description: Optional[str] = None
    is_active: bool = True


class BoundaryConditionTemplate(BaseModel):
    """Predefined boundary condition templates"""
    name: str
    description: str
    restraints: Dict[str, bool]
    spring_constants: Dict[str, float] = Field(default_factory=dict)


class BoundaryConditionManager:
    """Manager for boundary conditions"""
    
    def __init__(self):
        self.boundary_conditions: Dict[str, BoundaryCondition] = {}
        self.templates = self._create_standard_templates()
    
    def _create_standard_templates(self) -> Dict[str, BoundaryConditionTemplate]:
        """Create standard boundary condition templates"""
        templates = {}
        
        # Fixed support (all DOF restrained)
        templates["fixed"] = BoundaryConditionTemplate(
            name="Fixed Support",
            description="All translations and rotations restrained",
            restraints={
                "ux": True, "uy": True, "uz": True,
                "rx": True, "ry": True, "rz": True
            }
        )
        
        # Pinned support (translations restrained, rotations free)
        templates["pinned"] = BoundaryConditionTemplate(
            name="Pinned Support",
            description="All translations restrained, rotations free",
            restraints={
                "ux": True, "uy": True, "uz": True,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        # Roller support in X direction
        templates["roller_x"] = BoundaryConditionTemplate(
            name="Roller Support (X-direction)",
            description="Y and Z translations restrained, X translation and rotations free",
            restraints={
                "ux": False, "uy": True, "uz": True,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        # Roller support in Y direction
        templates["roller_y"] = BoundaryConditionTemplate(
            name="Roller Support (Y-direction)",
            description="X and Z translations restrained, Y translation and rotations free",
            restraints={
                "ux": True, "uy": False, "uz": True,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        # Roller support in Z direction
        templates["roller_z"] = BoundaryConditionTemplate(
            name="Roller Support (Z-direction)",
            description="X and Y translations restrained, Z translation and rotations free",
            restraints={
                "ux": True, "uy": True, "uz": False,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        # Free (no restraints)
        templates["free"] = BoundaryConditionTemplate(
            name="Free",
            description="No restraints",
            restraints={
                "ux": False, "uy": False, "uz": False,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        # 2D Frame supports
        templates["fixed_2d"] = BoundaryConditionTemplate(
            name="Fixed Support (2D)",
            description="2D fixed support (UX, UY, RZ restrained)",
            restraints={
                "ux": True, "uy": True, "uz": False,
                "rx": False, "ry": False, "rz": True
            }
        )
        
        templates["pinned_2d"] = BoundaryConditionTemplate(
            name="Pinned Support (2D)",
            description="2D pinned support (UX, UY restrained)",
            restraints={
                "ux": True, "uy": True, "uz": False,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        templates["roller_2d_x"] = BoundaryConditionTemplate(
            name="Roller Support 2D (X-direction)",
            description="2D roller support (UY restrained)",
            restraints={
                "ux": False, "uy": True, "uz": False,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        templates["roller_2d_y"] = BoundaryConditionTemplate(
            name="Roller Support 2D (Y-direction)",
            description="2D roller support (UX restrained)",
            restraints={
                "ux": True, "uy": False, "uz": False,
                "rx": False, "ry": False, "rz": False
            }
        )
        
        return templates
    
    def add_boundary_condition(self, node_id: str, restraints: Dict[str, bool],
                              bc_id: str = None, description: str = None) -> BoundaryCondition:
        """Add a boundary condition"""
        if bc_id is None:
            bc_id = f"BC_{len(self.boundary_conditions) + 1:04d}"
        
        bc = BoundaryCondition(
            id=bc_id,
            node_id=node_id,
            restraints=restraints,
            description=description
        )
        
        self.boundary_conditions[bc_id] = bc
        return bc
    
    def add_boundary_condition_from_template(self, node_id: str, template_name: str,
                                           bc_id: str = None) -> BoundaryCondition:
        """Add boundary condition from template"""
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        
        if bc_id is None:
            bc_id = f"BC_{len(self.boundary_conditions) + 1:04d}"
        
        bc = BoundaryCondition(
            id=bc_id,
            node_id=node_id,
            restraints=template.restraints.copy(),
            restraint_type=RestraintType(template_name) if template_name in [e.value for e in RestraintType] else RestraintType.CUSTOM,
            description=template.description
        )
        
        self.boundary_conditions[bc_id] = bc
        return bc
    
    def add_spring_support(self, node_id: str, spring_constants: Dict[str, float],
                          bc_id: str = None, description: str = None) -> BoundaryCondition:
        """Add spring support"""
        if bc_id is None:
            bc_id = f"BC_{len(self.boundary_conditions) + 1:04d}"
        
        # For spring supports, no restraints but spring constants
        restraints = {dof: False for dof in ["ux", "uy", "uz", "rx", "ry", "rz"]}
        
        bc = BoundaryCondition(
            id=bc_id,
            node_id=node_id,
            restraints=restraints,
            spring_constants=spring_constants,
            restraint_type=RestraintType.SPRING,
            description=description or "Spring Support"
        )
        
        self.boundary_conditions[bc_id] = bc
        return bc
    
    def add_prescribed_displacement(self, node_id: str, displacements: Dict[str, float],
                                  bc_id: str = None, description: str = None) -> BoundaryCondition:
        """Add prescribed displacement"""
        if bc_id is None:
            bc_id = f"BC_{len(self.boundary_conditions) + 1:04d}"
        
        # Restrain DOFs that have prescribed displacements
        restraints = {dof: abs(disp) > 1e-12 for dof, disp in displacements.items()}
        
        bc = BoundaryCondition(
            id=bc_id,
            node_id=node_id,
            restraints=restraints,
            prescribed_displacements=displacements,
            description=description or "Prescribed Displacement"
        )
        
        self.boundary_conditions[bc_id] = bc
        return bc
    
    def remove_boundary_condition(self, bc_id: str) -> bool:
        """Remove a boundary condition"""
        if bc_id in self.boundary_conditions:
            del self.boundary_conditions[bc_id]
            return True
        return False
    
    def get_boundary_condition(self, bc_id: str) -> Optional[BoundaryCondition]:
        """Get boundary condition by ID"""
        return self.boundary_conditions.get(bc_id)
    
    def get_boundary_conditions_for_node(self, node_id: str) -> List[BoundaryCondition]:
        """Get all boundary conditions for a specific node"""
        return [bc for bc in self.boundary_conditions.values() if bc.node_id == node_id]
    
    def update_boundary_condition(self, bc_id: str, **kwargs) -> bool:
        """Update boundary condition properties"""
        if bc_id not in self.boundary_conditions:
            return False
        
        bc = self.boundary_conditions[bc_id]
        for key, value in kwargs.items():
            if hasattr(bc, key):
                setattr(bc, key, value)
        
        return True
    
    def get_restrained_dofs(self, node_id: str) -> Dict[str, bool]:
        """Get combined restraints for a node"""
        combined_restraints = {
            "ux": False, "uy": False, "uz": False,
            "rx": False, "ry": False, "rz": False
        }
        
        for bc in self.get_boundary_conditions_for_node(node_id):
            if bc.is_active:
                for dof, restrained in bc.restraints.items():
                    if restrained:
                        combined_restraints[dof] = True
        
        return combined_restraints
    
    def get_spring_constants(self, node_id: str) -> Dict[str, float]:
        """Get combined spring constants for a node"""
        combined_springs = {
            "kx": 0.0, "ky": 0.0, "kz": 0.0,
            "krx": 0.0, "kry": 0.0, "krz": 0.0
        }
        
        for bc in self.get_boundary_conditions_for_node(node_id):
            if bc.is_active and bc.restraint_type == RestraintType.SPRING:
                for spring, value in bc.spring_constants.items():
                    combined_springs[spring] += value
        
        return combined_springs
    
    def get_prescribed_displacements(self, node_id: str) -> Dict[str, float]:
        """Get prescribed displacements for a node"""
        prescribed = {
            "ux": 0.0, "uy": 0.0, "uz": 0.0,
            "rx": 0.0, "ry": 0.0, "rz": 0.0
        }
        
        for bc in self.get_boundary_conditions_for_node(node_id):
            if bc.is_active:
                for dof, value in bc.prescribed_displacements.items():
                    if bc.restraints.get(dof, False) and abs(value) > 1e-12:
                        prescribed[dof] = value
        
        return prescribed
    
    def validate_boundary_conditions(self) -> List[str]:
        """Validate all boundary conditions"""
        errors = []
        
        for bc_id, bc in self.boundary_conditions.items():
            # Check if at least one DOF is restrained or has spring
            has_restraint = any(bc.restraints.values())
            has_spring = any(abs(k) > 1e-12 for k in bc.spring_constants.values())
            
            if not has_restraint and not has_spring:
                errors.append(f"Boundary condition {bc_id} has no effect")
            
            # Check spring constants are non-negative
            for spring, value in bc.spring_constants.items():
                if value < 0:
                    errors.append(f"Boundary condition {bc_id} has negative spring constant {spring}")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of boundary conditions"""
        summary = {
            "total_boundary_conditions": len(self.boundary_conditions),
            "active_boundary_conditions": sum(1 for bc in self.boundary_conditions.values() if bc.is_active),
            "restraint_types": {},
            "nodes_with_restraints": set()
        }
        
        for bc in self.boundary_conditions.values():
            if bc.is_active:
                # Count restraint types
                restraint_type = bc.restraint_type.value
                summary["restraint_types"][restraint_type] = summary["restraint_types"].get(restraint_type, 0) + 1
                
                # Track nodes with restraints
                summary["nodes_with_restraints"].add(bc.node_id)
        
        summary["nodes_with_restraints"] = len(summary["nodes_with_restraints"])
        
        return summary
    
    def clear_all(self):
        """Clear all boundary conditions"""
        self.boundary_conditions.clear()
    
    def get_available_templates(self) -> Dict[str, str]:
        """Get available boundary condition templates"""
        return {name: template.description for name, template in self.templates.items()}


class BoundaryConditionValidator:
    """Boundary condition validation utilities"""
    
    @staticmethod
    def validate_restraints(restraints: Dict[str, bool]) -> List[str]:
        """Validate restraint dictionary"""
        errors = []
        
        required_dofs = ["ux", "uy", "uz", "rx", "ry", "rz"]
        for dof in required_dofs:
            if dof not in restraints:
                errors.append(f"Missing restraint definition for {dof}")
        
        return errors
    
    @staticmethod
    def validate_spring_constants(spring_constants: Dict[str, float]) -> List[str]:
        """Validate spring constants"""
        errors = []
        
        for spring, value in spring_constants.items():
            if value < 0:
                errors.append(f"Spring constant {spring} cannot be negative")
        
        return errors
    
    @staticmethod
    def check_structural_stability(boundary_conditions: List[BoundaryCondition],
                                 num_nodes: int, dimension: int = 3) -> List[str]:
        """Check if boundary conditions provide structural stability"""
        errors = []
        
        # Count total restraints
        total_restraints = 0
        restrained_nodes = set()
        
        for bc in boundary_conditions:
            if bc.is_active:
                restrained_nodes.add(bc.node_id)
                total_restraints += sum(bc.restraints.values())
        
        # Minimum restraints needed for stability
        if dimension == 2:
            min_restraints = 3  # 2D: need to restrain 3 DOF minimum
        else:
            min_restraints = 6  # 3D: need to restrain 6 DOF minimum
        
        if total_restraints < min_restraints:
            errors.append(f"Insufficient restraints for stability. Need at least {min_restraints}, found {total_restraints}")
        
        if not restrained_nodes:
            errors.append("No nodes have boundary conditions - structure is unstable")
        
        return errors