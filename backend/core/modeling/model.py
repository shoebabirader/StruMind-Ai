"""
Structural model management for StruMind
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import uuid
from pydantic import BaseModel, Field

from .geometry import Point3D, Vector3D
from .nodes import Node, NodeManager
from .elements import Element, ElementFactory, ElementProperties
from .materials import Material, MaterialLibrary
from .sections import Section, SectionLibrary
from .loads import LoadGenerator, LoadValidator, LoadCase, LoadCombination
from .boundary_conditions import BoundaryCondition, BoundaryConditionManager


class ModelMetadata(BaseModel):
    """Model metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    version: str = "1.0"
    units: Dict[str, str] = Field(default_factory=lambda: {
        "length": "m",
        "force": "N",
        "mass": "kg",
        "time": "s",
        "temperature": "C"
    })
    author: Optional[str] = None
    project_id: Optional[str] = None


class ModelSettings(BaseModel):
    """Model analysis settings"""
    analysis_type: str = "linear_static"
    solver_tolerance: float = 1e-6
    max_iterations: int = 1000
    include_self_weight: bool = True
    gravity_direction: Vector3D = Field(default_factory=lambda: Vector3D(0, 0, -1))
    gravity_magnitude: float = 9.81
    
    # Dynamic analysis settings
    num_modes: int = 10
    frequency_range: Tuple[float, float] = (0.0, 100.0)
    damping_ratio: float = 0.05
    
    # Nonlinear analysis settings
    load_steps: int = 10
    convergence_criteria: str = "force"
    line_search: bool = True


class StructuralModel:
    """Main structural model class"""
    
    def __init__(self, name: str, description: str = None):
        self.metadata = ModelMetadata(name=name, description=description)
        self.settings = ModelSettings()
        
        # Core components
        self.node_manager = NodeManager()
        self.element_factory = ElementFactory()
        self.material_library = MaterialLibrary()
        self.section_library = SectionLibrary()
        self.load_generator = LoadGenerator()
        self.boundary_manager = BoundaryConditionManager()
        
        # Model data
        self.elements: Dict[str, Element] = {}
        self.materials: Dict[str, Material] = {}
        self.sections: Dict[str, Section] = {}
        self.boundary_conditions: Dict[str, BoundaryCondition] = {}
        
        # Analysis results storage
        self.analysis_results: Dict[str, Any] = {}
        self.design_results: Dict[str, Any] = {}
        
        # Model state
        self._is_modified = False
        self._is_analyzed = False
    
    def add_node(self, x: float, y: float, z: float, node_id: str = None) -> Node:
        """Add a node to the model"""
        node = self.node_manager.add_node(x, y, z, node_id)
        self._mark_modified()
        return node
    
    def add_element(self, element_type: str, node_ids: List[str],
                   material_id: str, section_id: str, 
                   properties: ElementProperties = None) -> Element:
        """Add an element to the model"""
        # Validate nodes exist
        for node_id in node_ids:
            if not self.node_manager.node_exists(node_id):
                raise ValueError(f"Node {node_id} does not exist")
        
        # Validate material and section exist
        if material_id not in self.materials:
            raise ValueError(f"Material {material_id} does not exist")
        
        if section_id not in self.sections:
            raise ValueError(f"Section {section_id} does not exist")
        
        # Create element
        element = self.element_factory.create_element(
            element_type, node_ids, material_id, section_id, properties
        )
        
        self.elements[element.id] = element
        self._mark_modified()
        return element
    
    def add_material(self, material: Material) -> None:
        """Add a material to the model"""
        self.materials[material.id] = material
        self._mark_modified()
    
    def add_section(self, section: Section) -> None:
        """Add a section to the model"""
        self.sections[section.id] = section
        self._mark_modified()
    
    def add_boundary_condition(self, node_id: str, restraints: Dict[str, bool],
                              bc_id: str = None) -> BoundaryCondition:
        """Add boundary condition to a node"""
        if not self.node_manager.node_exists(node_id):
            raise ValueError(f"Node {node_id} does not exist")
        
        bc = self.boundary_manager.add_boundary_condition(
            node_id, restraints, bc_id
        )
        self.boundary_conditions[bc.id] = bc
        self._mark_modified()
        return bc
    
    def create_load_case(self, name: str, description: str = None) -> LoadCase:
        """Create a load case"""
        load_case = self.load_generator.create_load_case(name, description)
        self._mark_modified()
        return load_case
    
    def add_point_load(self, node_id: str, load_case_id: str,
                      fx: float = 0, fy: float = 0, fz: float = 0,
                      mx: float = 0, my: float = 0, mz: float = 0):
        """Add point load to a node"""
        if not self.node_manager.node_exists(node_id):
            raise ValueError(f"Node {node_id} does not exist")
        
        point_load = self.load_generator.add_point_load(
            node_id, load_case_id, fx, fy, fz, mx, my, mz
        )
        self._mark_modified()
        return point_load
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get model summary statistics"""
        return {
            "metadata": self.metadata.dict(),
            "statistics": {
                "nodes": len(self.node_manager.nodes),
                "elements": len(self.elements),
                "materials": len(self.materials),
                "sections": len(self.sections),
                "boundary_conditions": len(self.boundary_conditions),
                "load_summary": self.load_generator.get_load_summary()
            },
            "bounds": self.node_manager.get_model_bounds(),
            "is_modified": self._is_modified,
            "is_analyzed": self._is_analyzed
        }
    
    def validate_model(self) -> List[str]:
        """Validate the complete model"""
        validator = ModelValidator()
        return validator.validate_complete_model(self)
    
    def clear_analysis_results(self):
        """Clear all analysis results"""
        self.analysis_results.clear()
        self.design_results.clear()
        self._is_analyzed = False
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Export model to dictionary format"""
        return {
            "metadata": self.metadata.dict(),
            "settings": self.settings.dict(),
            "nodes": {nid: node.dict() for nid, node in self.node_manager.nodes.items()},
            "elements": {eid: element.dict() for eid, element in self.elements.items()},
            "materials": {mid: material.dict() for mid, material in self.materials.items()},
            "sections": {sid: section.dict() for sid, section in self.sections.items()},
            "boundary_conditions": {bid: bc.dict() for bid, bc in self.boundary_conditions.items()},
            "load_cases": {lid: lc.dict() for lid, lc in self.load_generator.load_cases.items()},
            "load_combinations": {lid: lc.dict() for lid, lc in self.load_generator.load_combinations.items()},
            "point_loads": {lid: pl.dict() for lid, pl in self.load_generator.point_loads.items()},
            "distributed_loads": {lid: dl.dict() for lid, dl in self.load_generator.distributed_loads.items()},
            "area_loads": {lid: al.dict() for lid, al in self.load_generator.area_loads.items()}
        }
    
    def export_to_json(self, filepath: str = None) -> str:
        """Export model to JSON format"""
        model_dict = self.export_to_dict()
        json_str = json.dumps(model_dict, indent=2, default=str)
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def _mark_modified(self):
        """Mark model as modified"""
        self._is_modified = True
        self.metadata.modified_at = datetime.now()
        self._is_analyzed = False  # Analysis results are no longer valid


class ModelValidator:
    """Model validation utilities"""
    
    def validate_complete_model(self, model: StructuralModel) -> List[str]:
        """Validate complete structural model"""
        errors = []
        
        # Basic model checks
        if not model.node_manager.nodes:
            errors.append("Model has no nodes")
        
        if not model.elements:
            errors.append("Model has no elements")
        
        # Node validation
        node_errors = self.validate_nodes(model)
        errors.extend(node_errors)
        
        # Element validation
        element_errors = self.validate_elements(model)
        errors.extend(element_errors)
        
        # Material validation
        material_errors = self.validate_materials(model)
        errors.extend(material_errors)
        
        # Section validation
        section_errors = self.validate_sections(model)
        errors.extend(section_errors)
        
        # Boundary condition validation
        bc_errors = self.validate_boundary_conditions(model)
        errors.extend(bc_errors)
        
        # Load validation
        load_errors = self.validate_loads(model)
        errors.extend(load_errors)
        
        # Connectivity validation
        connectivity_errors = self.validate_connectivity(model)
        errors.extend(connectivity_errors)
        
        return errors
    
    def validate_nodes(self, model: StructuralModel) -> List[str]:
        """Validate nodes"""
        errors = []
        
        # Check for duplicate coordinates
        coordinates = []
        for node in model.node_manager.nodes.values():
            coord = (node.x, node.y, node.z)
            if coord in coordinates:
                errors.append(f"Duplicate node coordinates at {coord}")
            coordinates.append(coord)
        
        return errors
    
    def validate_elements(self, model: StructuralModel) -> List[str]:
        """Validate elements"""
        errors = []
        
        for element in model.elements.values():
            # Check if all nodes exist
            for node_id in element.node_ids:
                if not model.node_manager.node_exists(node_id):
                    errors.append(f"Element {element.id} references non-existent node {node_id}")
            
            # Check if material exists
            if element.material_id not in model.materials:
                errors.append(f"Element {element.id} references non-existent material {element.material_id}")
            
            # Check if section exists
            if element.section_id not in model.sections:
                errors.append(f"Element {element.id} references non-existent section {element.section_id}")
            
            # Check element geometry
            if len(element.node_ids) < 2:
                errors.append(f"Element {element.id} has insufficient nodes")
            
            # Check for zero-length elements
            if len(element.node_ids) == 2:
                node1 = model.node_manager.get_node(element.node_ids[0])
                node2 = model.node_manager.get_node(element.node_ids[1])
                if node1 and node2:
                    length = ((node2.x - node1.x)**2 + (node2.y - node1.y)**2 + (node2.z - node1.z)**2)**0.5
                    if length < 1e-6:
                        errors.append(f"Element {element.id} has zero length")
        
        return errors
    
    def validate_materials(self, model: StructuralModel) -> List[str]:
        """Validate materials"""
        errors = []
        
        for material in model.materials.values():
            if material.elastic_modulus <= 0:
                errors.append(f"Material {material.id} has invalid elastic modulus")
            
            if material.density < 0:
                errors.append(f"Material {material.id} has negative density")
            
            if material.poisson_ratio < 0 or material.poisson_ratio >= 0.5:
                errors.append(f"Material {material.id} has invalid Poisson's ratio")
        
        return errors
    
    def validate_sections(self, model: StructuralModel) -> List[str]:
        """Validate sections"""
        errors = []
        
        for section in model.sections.values():
            if hasattr(section, 'area') and section.area <= 0:
                errors.append(f"Section {section.id} has invalid area")
            
            if hasattr(section, 'moment_of_inertia_y') and section.moment_of_inertia_y <= 0:
                errors.append(f"Section {section.id} has invalid moment of inertia")
        
        return errors
    
    def validate_boundary_conditions(self, model: StructuralModel) -> List[str]:
        """Validate boundary conditions"""
        errors = []
        
        # Check if model has sufficient restraints
        total_restraints = 0
        for bc in model.boundary_conditions.values():
            if not model.node_manager.node_exists(bc.node_id):
                errors.append(f"Boundary condition {bc.id} references non-existent node {bc.node_id}")
            
            total_restraints += sum(bc.restraints.values())
        
        if total_restraints == 0:
            errors.append("Model has no boundary conditions - structure is unstable")
        
        return errors
    
    def validate_loads(self, model: StructuralModel) -> List[str]:
        """Validate loads"""
        errors = []
        
        # Check if model has loads
        total_loads = (len(model.load_generator.point_loads) + 
                      len(model.load_generator.distributed_loads) + 
                      len(model.load_generator.area_loads))
        
        if total_loads == 0 and not model.settings.include_self_weight:
            errors.append("Model has no applied loads")
        
        # Validate point loads
        for point_load in model.load_generator.point_loads.values():
            if not model.node_manager.node_exists(point_load.node_id):
                errors.append(f"Point load {point_load.id} references non-existent node {point_load.node_id}")
        
        # Validate distributed loads
        for dist_load in model.load_generator.distributed_loads.values():
            if dist_load.element_id not in model.elements:
                errors.append(f"Distributed load {dist_load.id} references non-existent element {dist_load.element_id}")
        
        return errors
    
    def validate_connectivity(self, model: StructuralModel) -> List[str]:
        """Validate model connectivity"""
        errors = []
        
        # Check for unconnected nodes
        connected_nodes = set()
        for element in model.elements.values():
            connected_nodes.update(element.node_ids)
        
        all_nodes = set(model.node_manager.nodes.keys())
        unconnected_nodes = all_nodes - connected_nodes
        
        if unconnected_nodes:
            errors.append(f"Unconnected nodes found: {list(unconnected_nodes)}")
        
        # Check for structural stability (simplified)
        if len(model.elements) < len(model.node_manager.nodes) - 1:
            errors.append("Model may be structurally unstable - insufficient elements")
        
        return errors