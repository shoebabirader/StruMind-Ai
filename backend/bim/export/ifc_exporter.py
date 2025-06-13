"""
IFC export functionality for structural models
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
import logging

from ...core.modeling.model import StructuralModel
from ...core.modeling.nodes import Node
from ...core.modeling.elements import Element
from ...core.modeling.materials import Material
from ...core.modeling.sections import Section

logger = logging.getLogger(__name__)


class IFCExporter:
    """
    Export structural models to IFC format
    """
    
    def __init__(self):
        self.model = None
        self.project = None
        self.site = None
        self.building = None
        self.building_storey = None
        
        # Mapping dictionaries
        self.node_mapping = {}  # Node ID to IFC entity
        self.element_mapping = {}  # Element ID to IFC entity
        self.material_mapping = {}  # Material ID to IFC entity
        self.section_mapping = {}  # Section ID to IFC entity
        
    def export_to_file(self, model: StructuralModel, file_path: str, 
                      project_info: Optional[Dict] = None) -> bool:
        """
        Export structural model to IFC file (simplified implementation)
        """
        logger.info(f"Exporting model to IFC file: {file_path}")
        
        try:
            self.model = model
            
            # Create IFC data structure
            ifc_data = self._create_ifc_data_structure(project_info or {})
            
            # Export to simplified IFC format (JSON-based for this implementation)
            self._write_ifc_file(ifc_data, file_path)
            
            logger.info(f"IFC export completed successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export IFC file: {e}")
            raise
    
    def _create_ifc_data_structure(self, project_info: Dict) -> Dict:
        """
        Create IFC data structure
        """
        ifc_data = {
            "header": {
                "file_description": ["StruMind Structural Model"],
                "file_name": project_info.get("name", self.model.name or "StruMind Project"),
                "time_stamp": datetime.now().isoformat(),
                "author": ["StruMind Platform"],
                "organization": ["StruMind"],
                "preprocessor_version": "StruMind 1.0.0",
                "originating_system": "StruMind Structural Analysis Platform",
                "authorization": "StruMind User"
            },
            "units": {
                "length_unit": "METRE",
                "area_unit": "SQUARE_METRE", 
                "volume_unit": "CUBIC_METRE",
                "force_unit": "NEWTON",
                "pressure_unit": "PASCAL"
            },
            "project": {
                "global_id": self._generate_guid(),
                "name": project_info.get("name", self.model.name or "StruMind Project"),
                "description": project_info.get("description", self.model.description or ""),
                "phase": "Design"
            },
            "site": {
                "global_id": self._generate_guid(),
                "name": project_info.get("site_name", "Site"),
                "description": "Project site"
            },
            "building": {
                "global_id": self._generate_guid(),
                "name": project_info.get("building_name", "Building"),
                "description": "Main building"
            },
            "building_storey": {
                "global_id": self._generate_guid(),
                "name": "Ground Floor",
                "elevation": 0.0
            },
            "materials": [],
            "sections": [],
            "nodes": [],
            "elements": []
        }
        
        # Export materials
        for material in self.model.materials:
            ifc_material = self._export_material(material)
            ifc_data["materials"].append(ifc_material)
            self.material_mapping[material.id] = ifc_material["global_id"]
        
        # Export sections
        for section in self.model.sections:
            ifc_section = self._export_section(section)
            ifc_data["sections"].append(ifc_section)
            self.section_mapping[section.id] = ifc_section["global_id"]
        
        # Export nodes
        for node in self.model.nodes:
            ifc_node = self._export_node(node)
            ifc_data["nodes"].append(ifc_node)
            self.node_mapping[node.id] = ifc_node["global_id"]
        
        # Export elements
        for element in self.model.elements:
            ifc_element = self._export_element(element)
            if ifc_element:
                ifc_data["elements"].append(ifc_element)
                self.element_mapping[element.id] = ifc_element["global_id"]
        
        return ifc_data
    
    def _export_material(self, material: Material) -> Dict:
        """
        Export material to IFC format
        """
        return {
            "global_id": self._generate_guid(),
            "name": material.name,
            "description": f"{material.material_type} material",
            "material_type": material.material_type,
            "properties": {
                "elastic_modulus": material.elastic_modulus,
                "poisson_ratio": material.poisson_ratio,
                "density": material.density,
                "yield_strength": getattr(material, 'yield_strength', None),
                "compressive_strength": getattr(material, 'compressive_strength', None),
                "tensile_strength": getattr(material, 'tensile_strength', None)
            }
        }
    
    def _export_section(self, section: Section) -> Dict:
        """
        Export section to IFC format
        """
        section_data = {
            "global_id": self._generate_guid(),
            "name": section.name,
            "section_type": section.section_type,
            "properties": {
                "area": section.area,
                "moment_of_inertia_x": section.moment_of_inertia_x,
                "moment_of_inertia_y": section.moment_of_inertia_y,
                "torsional_constant": getattr(section, 'torsional_constant', 0)
            }
        }
        
        # Add type-specific properties
        if hasattr(section, 'width'):
            section_data["properties"]["width"] = section.width
        if hasattr(section, 'depth'):
            section_data["properties"]["depth"] = section.depth
        if hasattr(section, 'thickness'):
            section_data["properties"]["thickness"] = section.thickness
        if hasattr(section, 'diameter'):
            section_data["properties"]["diameter"] = section.diameter
        
        return section_data
    
    def _export_node(self, node: Node) -> Dict:
        """
        Export node to IFC format
        """
        return {
            "global_id": self._generate_guid(),
            "id": node.id,
            "coordinates": {
                "x": node.x,
                "y": node.y,
                "z": node.z
            },
            "restraints": getattr(node, 'restraints', {})
        }
    
    def _export_element(self, element: Element) -> Dict:
        """
        Export element to IFC format
        """
        try:
            # Get start and end nodes
            start_node = self.model.get_node(element.start_node_id)
            end_node = self.model.get_node(element.end_node_id)
            
            if not start_node or not end_node:
                logger.warning(f"Missing nodes for element {element.id}")
                return None
            
            element_data = {
                "global_id": self._generate_guid(),
                "id": element.id,
                "element_type": element.element_type,
                "name": f"{element.element_type.title()}_{element.id}",
                "start_node_id": element.start_node_id,
                "end_node_id": element.end_node_id,
                "start_node_global_id": self.node_mapping.get(element.start_node_id),
                "end_node_global_id": self.node_mapping.get(element.end_node_id),
                "material_id": element.material_id,
                "material_global_id": self.material_mapping.get(element.material_id),
                "section_id": element.section_id,
                "section_global_id": self.section_mapping.get(element.section_id),
                "length": element.length,
                "geometry": {
                    "start_point": [start_node.x, start_node.y, start_node.z],
                    "end_point": [end_node.x, end_node.y, end_node.z]
                }
            }
            
            # Add element-specific properties
            if element.element_type == "beam":
                element_data["predefined_type"] = "BEAM"
            elif element.element_type == "column":
                element_data["predefined_type"] = "COLUMN"
            elif element.element_type == "brace":
                element_data["predefined_type"] = "BRACE"
            else:
                element_data["predefined_type"] = "USERDEFINED"
            
            return element_data
            
        except Exception as e:
            logger.warning(f"Failed to export element {element.id}: {e}")
            return None
    
    def _write_ifc_file(self, ifc_data: Dict, file_path: str):
        """
        Write IFC data to file (simplified JSON format)
        """
        import json
        
        # For a full IFC implementation, this would write proper IFC format
        # For this implementation, we'll write structured JSON
        with open(file_path, 'w') as f:
            json.dump(ifc_data, f, indent=2)
    
    def _generate_guid(self) -> str:
        """
        Generate IFC-style GUID
        """
        return str(uuid.uuid4()).replace('-', '').upper()[:22]
    
    def get_export_summary(self) -> Dict:
        """
        Get summary of exported model
        """
        return {
            "materials_exported": len(self.material_mapping),
            "sections_exported": len(self.section_mapping),
            "elements_exported": len(self.element_mapping),
            "nodes_exported": len(self.node_mapping),
            "export_timestamp": datetime.now().isoformat()
        }