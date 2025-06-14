"""
IFC import functionality for structural models
"""

import json
import uuid
from typing import Dict, List, Optional, Any
import logging

from core.modeling.model import StructuralModel
from core.modeling.nodes import Node
from core.modeling.elements import Element
from core.modeling.materials import MaterialProperties, MaterialStandard
from core.modeling.sections import SectionProperties
from db.models.structural import Material, Section

logger = logging.getLogger(__name__)


class IFCImporter:
    """
    Import structural models from IFC format
    """
    
    def __init__(self):
        self.model = None
        self.imported_data = {}
        
        # Mapping dictionaries
        self.node_mapping = {}  # IFC GUID to Node object
        self.element_mapping = {}  # IFC GUID to Element object
        self.material_mapping = {}  # IFC GUID to Material object
        self.section_mapping = {}  # IFC GUID to Section object
        
    def import_from_file(self, file_path: str) -> StructuralModel:
        """
        Import structural model from IFC file
        """
        logger.info(f"Importing model from IFC file: {file_path}")
        
        try:
            # Load IFC data (simplified JSON format for this implementation)
            with open(file_path, 'r') as f:
                self.imported_data = json.load(f)
            
            # Create new structural model
            self.model = StructuralModel()
            
            # Import in order: materials, sections, nodes, elements
            self._import_materials()
            self._import_sections()
            self._import_nodes()
            self._import_elements()
            
            # Set model metadata
            project_info = self.imported_data.get("project", {})
            self.model.name = project_info.get("name", "Imported Model")
            self.model.description = project_info.get("description", "")
            
            logger.info(f"IFC import completed successfully")
            return self.model
            
        except Exception as e:
            logger.error(f"Failed to import IFC file: {e}")
            raise
    
    def _import_materials(self):
        """
        Import materials from IFC data
        """
        materials_data = self.imported_data.get("materials", [])
        
        for material_data in materials_data:
            try:
                material = self._create_material_from_ifc(material_data)
                if material:
                    self.model.add_material(material)
                    self.material_mapping[material_data["global_id"]] = material
                    
            except Exception as e:
                logger.warning(f"Failed to import material {material_data.get('name', 'Unknown')}: {e}")
    
    def _import_sections(self):
        """
        Import sections from IFC data
        """
        sections_data = self.imported_data.get("sections", [])
        
        for section_data in sections_data:
            try:
                section = self._create_section_from_ifc(section_data)
                if section:
                    self.model.add_section(section)
                    self.section_mapping[section_data["global_id"]] = section
                    
            except Exception as e:
                logger.warning(f"Failed to import section {section_data.get('name', 'Unknown')}: {e}")
    
    def _import_nodes(self):
        """
        Import nodes from IFC data
        """
        nodes_data = self.imported_data.get("nodes", [])
        
        for node_data in nodes_data:
            try:
                node = self._create_node_from_ifc(node_data)
                if node:
                    self.model.add_node(node)
                    self.node_mapping[node_data["global_id"]] = node
                    
            except Exception as e:
                logger.warning(f"Failed to import node {node_data.get('id', 'Unknown')}: {e}")
    
    def _import_elements(self):
        """
        Import elements from IFC data
        """
        elements_data = self.imported_data.get("elements", [])
        
        for element_data in elements_data:
            try:
                element = self._create_element_from_ifc(element_data)
                if element:
                    self.model.add_element(element)
                    self.element_mapping[element_data["global_id"]] = element
                    
            except Exception as e:
                logger.warning(f"Failed to import element {element_data.get('id', 'Unknown')}: {e}")
    
    def _create_material_from_ifc(self, material_data: Dict) -> Optional[Material]:
        """
        Create material object from IFC data
        """
        material_type = material_data.get("material_type", "steel").lower()
        properties = material_data.get("properties", {})
        
        # Common properties
        name = material_data.get("name", "Unknown Material")
        elastic_modulus = properties.get("elastic_modulus", 200000)  # MPa
        poisson_ratio = properties.get("poisson_ratio", 0.3)
        density = properties.get("density", 7850)  # kg/m³
        
        if material_type == "steel":
            yield_strength = properties.get("yield_strength", 250)  # MPa
            ultimate_strength = properties.get("ultimate_strength", 400)  # MPa
            
            return SteelMaterial(
                id=uuid.uuid4(),
                name=name,
                elastic_modulus=elastic_modulus,
                poisson_ratio=poisson_ratio,
                density=density,
                yield_strength=yield_strength,
                ultimate_strength=ultimate_strength,
                material_type="steel"
            )
            
        elif material_type == "concrete":
            compressive_strength = properties.get("compressive_strength", 25)  # MPa
            tensile_strength = properties.get("tensile_strength", 2.5)  # MPa
            
            return ConcreteMaterial(
                id=uuid.uuid4(),
                name=name,
                elastic_modulus=elastic_modulus,
                poisson_ratio=poisson_ratio,
                density=density,
                compressive_strength=compressive_strength,
                tensile_strength=tensile_strength,
                material_type="concrete"
            )
        
        else:
            # Generic material
            return Material(
                id=uuid.uuid4(),
                name=name,
                elastic_modulus=elastic_modulus,
                poisson_ratio=poisson_ratio,
                density=density,
                material_type=material_type
            )
    
    def _create_section_from_ifc(self, section_data: Dict) -> Optional[Section]:
        """
        Create section object from IFC data
        """
        section_type = section_data.get("section_type", "generic").lower()
        properties = section_data.get("properties", {})
        
        # Common properties
        name = section_data.get("name", "Unknown Section")
        area = properties.get("area", 0.01)  # m²
        moment_of_inertia_x = properties.get("moment_of_inertia_x", 1e-6)  # m⁴
        moment_of_inertia_y = properties.get("moment_of_inertia_y", 1e-6)  # m⁴
        
        if section_type in ["i_section", "h_section", "w_section"]:
            # Steel I-section
            depth = properties.get("depth", 0.3)  # m
            flange_width = properties.get("width", 0.15)  # m
            flange_thickness = properties.get("flange_thickness", 0.01)  # m
            web_thickness = properties.get("web_thickness", 0.008)  # m
            
            return SteelSection(
                id=uuid.uuid4(),
                name=name,
                section_type=section_type,
                area=area,
                moment_of_inertia_x=moment_of_inertia_x,
                moment_of_inertia_y=moment_of_inertia_y,
                depth=depth,
                flange_width=flange_width,
                flange_thickness=flange_thickness,
                web_thickness=web_thickness
            )
            
        elif section_type == "rectangular":
            # Rectangular section (could be steel or concrete)
            width = properties.get("width", 0.3)  # m
            depth = properties.get("depth", 0.5)  # m
            
            return ConcreteSection(
                id=uuid.uuid4(),
                name=name,
                section_type=section_type,
                area=area,
                moment_of_inertia_x=moment_of_inertia_x,
                moment_of_inertia_y=moment_of_inertia_y,
                width=width,
                depth=depth
            )
            
        elif section_type == "circular":
            # Circular section
            diameter = properties.get("diameter", 0.3)  # m
            
            return Section(
                id=uuid.uuid4(),
                name=name,
                section_type=section_type,
                area=area,
                moment_of_inertia_x=moment_of_inertia_x,
                moment_of_inertia_y=moment_of_inertia_y,
                diameter=diameter
            )
        
        else:
            # Generic section
            return Section(
                id=uuid.uuid4(),
                name=name,
                section_type=section_type,
                area=area,
                moment_of_inertia_x=moment_of_inertia_x,
                moment_of_inertia_y=moment_of_inertia_y
            )
    
    def _create_node_from_ifc(self, node_data: Dict) -> Optional[Node]:
        """
        Create node object from IFC data
        """
        coordinates = node_data.get("coordinates", {})
        
        return Node(
            id=uuid.uuid4(),
            x=coordinates.get("x", 0.0),
            y=coordinates.get("y", 0.0),
            z=coordinates.get("z", 0.0),
            restraints=node_data.get("restraints", {})
        )
    
    def _create_element_from_ifc(self, element_data: Dict) -> Optional[Element]:
        """
        Create element object from IFC data
        """
        # Find start and end nodes
        start_node_global_id = element_data.get("start_node_global_id")
        end_node_global_id = element_data.get("end_node_global_id")
        
        start_node = self.node_mapping.get(start_node_global_id)
        end_node = self.node_mapping.get(end_node_global_id)
        
        if not start_node or not end_node:
            logger.warning(f"Missing nodes for element {element_data.get('id')}")
            return None
        
        # Find material and section
        material_global_id = element_data.get("material_global_id")
        section_global_id = element_data.get("section_global_id")
        
        material = self.material_mapping.get(material_global_id)
        section = self.section_mapping.get(section_global_id)
        
        if not material or not section:
            logger.warning(f"Missing material or section for element {element_data.get('id')}")
            return None
        
        # Determine element type from predefined type
        predefined_type = element_data.get("predefined_type", "USERDEFINED").lower()
        if predefined_type == "beam":
            element_type = "beam"
        elif predefined_type == "column":
            element_type = "column"
        elif predefined_type == "brace":
            element_type = "brace"
        else:
            element_type = element_data.get("element_type", "beam")
        
        return Element(
            id=uuid.uuid4(),
            element_type=element_type,
            start_node_id=start_node.id,
            end_node_id=end_node.id,
            material_id=material.id,
            section_id=section.id,
            length=element_data.get("length", 0.0),
            is_active=True
        )
    
    def get_import_summary(self) -> Dict:
        """
        Get summary of imported model
        """
        return {
            "materials_imported": len(self.material_mapping),
            "sections_imported": len(self.section_mapping),
            "nodes_imported": len(self.node_mapping),
            "elements_imported": len(self.element_mapping),
            "import_timestamp": self.imported_data.get("header", {}).get("time_stamp"),
            "original_file": self.imported_data.get("header", {}).get("file_name")
        }
    
    def validate_imported_model(self) -> Dict[str, List[str]]:
        """
        Validate the imported model for consistency
        """
        errors = []
        warnings = []
        
        # Check for orphaned elements
        for element in self.model.elements:
            start_node = self.model.get_node(element.start_node_id)
            end_node = self.model.get_node(element.end_node_id)
            
            if not start_node:
                errors.append(f"Element {element.id} references missing start node {element.start_node_id}")
            if not end_node:
                errors.append(f"Element {element.id} references missing end node {element.end_node_id}")
            
            material = self.model.get_material(element.material_id)
            section = self.model.get_section(element.section_id)
            
            if not material:
                errors.append(f"Element {element.id} references missing material {element.material_id}")
            if not section:
                errors.append(f"Element {element.id} references missing section {element.section_id}")
        
        # Check for duplicate nodes at same location
        node_locations = {}
        for node in self.model.nodes:
            location = (round(node.x, 6), round(node.y, 6), round(node.z, 6))
            if location in node_locations:
                warnings.append(f"Nodes {node_locations[location]} and {node.id} are at the same location")
            else:
                node_locations[location] = node.id
        
        # Check for zero-length elements
        for element in self.model.elements:
            if element.length < 1e-6:
                warnings.append(f"Element {element.id} has zero or very small length")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }