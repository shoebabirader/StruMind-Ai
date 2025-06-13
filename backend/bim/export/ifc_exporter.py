"""
IFC (Industry Foundation Classes) export functionality
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import uuid
import json

from db.models.structural import Node, Element, Material, Section
from db.models.project import Project
from core.exceptions import ExportError


class IFCExporter:
    """IFC file exporter for structural models"""
    
    def __init__(self):
        self.entity_counter = 1
        self.entities = {}
        self.project_info = {}
    
    def export_model(self, project: Project, nodes: List[Node], elements: List[Element],
                    materials: List[Material], sections: List[Section]) -> str:
        """Export structural model to IFC format"""
        
        # Initialize IFC file
        ifc_content = self._create_ifc_header(project)
        
        # Create basic IFC entities
        ifc_content += self._create_basic_entities(project)
        
        # Export materials
        material_entities = self._export_materials(materials)
        ifc_content += material_entities
        
        # Export sections
        section_entities = self._export_sections(sections)
        ifc_content += section_entities
        
        # Export nodes as points
        node_entities = self._export_nodes(nodes)
        ifc_content += node_entities
        
        # Export elements
        element_entities = self._export_elements(elements, nodes, materials, sections)
        ifc_content += element_entities
        
        # Close IFC file
        ifc_content += self._create_ifc_footer()
        
        return ifc_content
    
    def _create_ifc_header(self, project: Project) -> str:
        """Create IFC file header"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        
        header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [StructuralAnalysisView]'),'2;1');
FILE_NAME('{project.name}.ifc','{timestamp}',('StruMind Platform'),('StruMind Engineering'),'StruMind IFC Exporter','StruMind Platform v1.0','');
FILE_SCHEMA(('IFC4'));
ENDSEC;

DATA;
"""
        return header
    
    def _create_basic_entities(self, project: Project) -> str:
        """Create basic IFC entities"""
        entities = ""
        
        # Create project
        project_id = self._get_next_id()
        self.entities['project'] = project_id
        entities += f"#{project_id}= IFCPROJECT('{self._generate_guid()}',$,'{project.name}','{project.description or ''}',$,$,$,(#{self._get_next_id()}),#{self._get_next_id()});\n"
        
        # Create geometric representation context
        context_id = self._get_current_id()
        entities += f"#{context_id}= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#{self._get_next_id()},$);\n"
        
        # Create axis placement
        axis_id = self._get_current_id()
        entities += f"#{axis_id}= IFCAXIS2PLACEMENT3D(#{self._get_next_id()},$,$);\n"
        
        # Create origin point
        origin_id = self._get_current_id()
        entities += f"#{origin_id}= IFCCARTESIANPOINT((0.,0.,0.));\n"
        
        # Create unit assignment
        unit_id = self._get_current_id() - 1
        entities += f"#{unit_id}= IFCUNITASSIGNMENT((#{self._get_next_id()},#{self._get_next_id()},#{self._get_next_id()}));\n"
        
        # Create SI units
        length_unit_id = self._get_current_id()
        entities += f"#{length_unit_id}= IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);\n"
        
        area_unit_id = self._get_current_id()
        entities += f"#{area_unit_id}= IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);\n"
        
        volume_unit_id = self._get_current_id()
        entities += f"#{volume_unit_id}= IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);\n"
        
        # Create site
        site_id = self._get_next_id()
        self.entities['site'] = site_id
        entities += f"#{site_id}= IFCSITE('{self._generate_guid()}',$,'Site',$,$,#{self._get_next_id()},$,.ELEMENT.,$,$,$,$,$);\n"
        
        # Create site placement
        site_placement_id = self._get_current_id()
        entities += f"#{site_placement_id}= IFCLOCALPLACEMENT($,#{axis_id});\n"
        
        # Create building
        building_id = self._get_next_id()
        self.entities['building'] = building_id
        entities += f"#{building_id}= IFCBUILDING('{self._generate_guid()}',$,'{project.name} Structure',$,$,#{self._get_next_id()},$,.ELEMENT.,$,$,$);\n"
        
        # Create building placement
        building_placement_id = self._get_current_id()
        entities += f"#{building_placement_id}= IFCLOCALPLACEMENT(#{site_placement_id},#{axis_id});\n"
        
        return entities
    
    def _export_materials(self, materials: List[Material]) -> str:
        """Export materials to IFC"""
        entities = ""
        
        for material in materials:
            material_id = self._get_next_id()
            self.entities[f'material_{material.id}'] = material_id
            
            # Create material
            entities += f"#{material_id}= IFCMATERIAL('{material.name}','{material.material_type}','');\n"
            
            # Create material properties
            if material.properties:
                props_id = self._get_next_id()
                
                # Extract common properties
                elastic_modulus = material.properties.get('elastic_modulus', 0)
                poisson_ratio = material.properties.get('poisson_ratio', 0)
                density = material.properties.get('density', 0)
                
                entities += f"#{props_id}= IFCMATERIALPROPERTIES('{material.name} Properties','{material.material_type}',#{material_id});\n"
                
                # Add mechanical properties
                if elastic_modulus > 0:
                    mech_props_id = self._get_next_id()
                    entities += f"#{mech_props_id}= IFCMECHANICALPROPERTIES({elastic_modulus},{poisson_ratio},$,$,$,$,$);\n"
        
        return entities
    
    def _export_sections(self, sections: List[Section]) -> str:
        """Export sections to IFC"""
        entities = ""
        
        for section in sections:
            section_id = self._get_next_id()
            self.entities[f'section_{section.id}'] = section_id
            
            # Determine IFC section type based on section type
            if section.section_type == "i_section":
                entities += self._create_i_section(section_id, section)
            elif section.section_type == "rectangular":
                entities += self._create_rectangular_section(section_id, section)
            elif section.section_type == "circular":
                entities += self._create_circular_section(section_id, section)
            else:
                # Generic section
                entities += f"#{section_id}= IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,'{section.name}',$);\n"
        
        return entities
    
    def _create_i_section(self, section_id: int, section: Section) -> str:
        """Create IFC I-section"""
        props = section.properties
        
        # Extract I-section properties
        overall_width = props.get('bf', 200)  # mm
        overall_depth = props.get('d', 400)   # mm
        web_thickness = props.get('tw', 10)   # mm
        flange_thickness = props.get('tf', 15) # mm
        
        return f"#{section_id}= IFCISHAPEPROFILEDEF(.AREA.,'{section.name}',$,{overall_width},{overall_depth},{web_thickness},{flange_thickness},$,$,$);\n"
    
    def _create_rectangular_section(self, section_id: int, section: Section) -> str:
        """Create IFC rectangular section"""
        props = section.properties
        
        width = props.get('width', 300)   # mm
        height = props.get('height', 500) # mm
        
        return f"#{section_id}= IFCRECTANGLEPROFILEDEF(.AREA.,'{section.name}',$,{width},{height});\n"
    
    def _create_circular_section(self, section_id: int, section: Section) -> str:
        """Create IFC circular section"""
        props = section.properties
        
        radius = props.get('radius', 150)  # mm
        
        return f"#{section_id}= IFCCIRCLEPROFILEDEF(.AREA.,'{section.name}',$,{radius});\n"
    
    def _export_nodes(self, nodes: List[Node]) -> str:
        """Export nodes as IFC points"""
        entities = ""
        
        for node in nodes:
            point_id = self._get_next_id()
            self.entities[f'node_{node.id}'] = point_id
            
            # Convert coordinates to mm (IFC typically uses mm)
            x_mm = node.x * 1000
            y_mm = node.y * 1000
            z_mm = node.z * 1000
            
            entities += f"#{point_id}= IFCCARTESIANPOINT(({x_mm},{y_mm},{z_mm}));\n"
        
        return entities
    
    def _export_elements(self, elements: List[Element], nodes: List[Node],
                        materials: List[Material], sections: List[Section]) -> str:
        """Export elements to IFC"""
        entities = ""
        
        # Create node lookup
        node_lookup = {node.id: node for node in nodes}
        
        for element in elements:
            if element.element_type in ["BEAM", "COLUMN", "BRACE"]:
                entities += self._create_structural_member(element, node_lookup)
            elif element.element_type in ["SHELL", "PLATE", "WALL", "SLAB"]:
                entities += self._create_structural_surface_member(element, node_lookup)
        
        return entities
    
    def _create_structural_member(self, element: Element, node_lookup: Dict) -> str:
        """Create IFC structural member (beam/column)"""
        entities = ""
        
        member_id = self._get_next_id()
        self.entities[f'element_{element.id}'] = member_id
        
        # Get start and end nodes
        start_node = node_lookup.get(element.start_node_id)
        end_node = node_lookup.get(element.end_node_id)
        
        if not start_node or not end_node:
            return ""
        
        # Create structural member
        member_type = "BEAM" if element.element_type == "BEAM" else "COLUMN"
        entities += f"#{member_id}= IFCSTRUCTURALMEMBER('{self._generate_guid()}',$,'{element.label or element.element_type}',$,$,#{self._get_next_id()},$,.{member_type}.);\n"
        
        # Create placement
        placement_id = self._get_current_id()
        entities += f"#{placement_id}= IFCLOCALPLACEMENT($,#{self._get_next_id()});\n"
        
        # Create axis placement for member
        axis_id = self._get_current_id()
        start_point_id = self.entities.get(f'node_{element.start_node_id}')
        entities += f"#{axis_id}= IFCAXIS2PLACEMENT3D(#{start_point_id},$,$);\n"
        
        # Create geometric representation
        geom_id = self._get_next_id()
        entities += f"#{geom_id}= IFCPRODUCTDEFINITIONSHAPE($,$,(#{self._get_next_id()}));\n"
        
        # Create shape representation
        shape_id = self._get_current_id()
        entities += f"#{shape_id}= IFCSHAPEREPRESENTATION(#{self.entities.get('project', 1)},'Body','SweptSolid',(#{self._get_next_id()}));\n"
        
        # Create line for member axis
        line_id = self._get_current_id()
        end_point_id = self.entities.get(f'node_{element.end_node_id}')
        entities += f"#{line_id}= IFCLINE(#{start_point_id},#{self._get_next_id()});\n"
        
        # Create direction vector
        vector_id = self._get_current_id()
        dx = end_node.x - start_node.x
        dy = end_node.y - start_node.y
        dz = end_node.z - start_node.z
        length = (dx**2 + dy**2 + dz**2)**0.5
        if length > 0:
            dx, dy, dz = dx/length, dy/length, dz/length
        entities += f"#{vector_id}= IFCVECTOR(#{self._get_next_id()},{length * 1000});\n"
        
        # Create direction
        dir_id = self._get_current_id()
        entities += f"#{dir_id}= IFCDIRECTION(({dx},{dy},{dz}));\n"
        
        return entities
    
    def _create_structural_surface_member(self, element: Element, node_lookup: Dict) -> str:
        """Create IFC structural surface member (shell/plate)"""
        entities = ""
        
        member_id = self._get_next_id()
        self.entities[f'element_{element.id}'] = member_id
        
        # Create structural surface member
        entities += f"#{member_id}= IFCSTRUCTURALSURFACEMEMBER('{self._generate_guid()}',$,'{element.label or element.element_type}',$,$,#{self._get_next_id()},$,.SHELL.,$);\n"
        
        # Create placement
        placement_id = self._get_current_id()
        start_point_id = self.entities.get(f'node_{element.start_node_id}')
        entities += f"#{placement_id}= IFCLOCALPLACEMENT($,#{self._get_next_id()});\n"
        
        # Create axis placement
        axis_id = self._get_current_id()
        entities += f"#{axis_id}= IFCAXIS2PLACEMENT3D(#{start_point_id},$,$);\n"
        
        return entities
    
    def _create_ifc_footer(self) -> str:
        """Create IFC file footer"""
        return "\nENDSEC;\n\nEND-ISO-10303-21;\n"
    
    def _get_next_id(self) -> int:
        """Get next entity ID"""
        current_id = self.entity_counter
        self.entity_counter += 1
        return current_id
    
    def _get_current_id(self) -> int:
        """Get current entity ID without incrementing"""
        return self.entity_counter
    
    def _generate_guid(self) -> str:
        """Generate IFC GUID"""
        # IFC uses a compressed GUID format
        guid = str(uuid.uuid4()).replace('-', '')
        return guid[:22]  # IFC GUID is 22 characters
    
    def export_to_file(self, filepath: str, project: Project, nodes: List[Node],
                      elements: List[Element], materials: List[Material],
                      sections: List[Section]) -> None:
        """Export model to IFC file"""
        try:
            ifc_content = self.export_model(project, nodes, elements, materials, sections)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(ifc_content)
                
        except Exception as e:
            raise ExportError(f"Failed to export IFC file: {str(e)}")
    
    def validate_export_data(self, nodes: List[Node], elements: List[Element]) -> List[str]:
        """Validate data before export"""
        errors = []
        
        if not nodes:
            errors.append("No nodes to export")
        
        if not elements:
            errors.append("No elements to export")
        
        # Check element connectivity
        node_ids = {node.id for node in nodes}
        for element in elements:
            if element.start_node_id not in node_ids:
                errors.append(f"Element {element.id} references non-existent start node {element.start_node_id}")
            
            if element.end_node_id and element.end_node_id not in node_ids:
                errors.append(f"Element {element.id} references non-existent end node {element.end_node_id}")
        
        return errors


class IFCImporter:
    """IFC file importer for structural models"""
    
    def __init__(self):
        self.entities = {}
        self.nodes = []
        self.elements = []
        self.materials = []
        self.sections = []
    
    def import_model(self, ifc_content: str) -> Dict[str, Any]:
        """Import structural model from IFC content"""
        try:
            # Parse IFC content
            self._parse_ifc_content(ifc_content)
            
            # Extract structural data
            self._extract_nodes()
            self._extract_elements()
            self._extract_materials()
            self._extract_sections()
            
            return {
                "nodes": self.nodes,
                "elements": self.elements,
                "materials": self.materials,
                "sections": self.sections
            }
            
        except Exception as e:
            raise ExportError(f"Failed to import IFC file: {str(e)}")
    
    def _parse_ifc_content(self, content: str) -> None:
        """Parse IFC file content"""
        # Simplified IFC parsing - in practice would use a proper IFC library
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') and '=' in line:
                # Extract entity ID and definition
                parts = line.split('=', 1)
                entity_id = int(parts[0][1:])  # Remove #
                entity_def = parts[1].strip()
                
                self.entities[entity_id] = entity_def
    
    def _extract_nodes(self) -> None:
        """Extract nodes from IFC entities"""
        for entity_id, entity_def in self.entities.items():
            if 'IFCCARTESIANPOINT' in entity_def:
                # Extract coordinates
                coords_start = entity_def.find('((') + 2
                coords_end = entity_def.find('))')
                if coords_start > 1 and coords_end > coords_start:
                    coords_str = entity_def[coords_start:coords_end]
                    coords = [float(x.strip()) for x in coords_str.split(',')]
                    
                    if len(coords) >= 3:
                        # Convert from mm to m
                        node_data = {
                            "id": str(entity_id),
                            "x": coords[0] / 1000.0,
                            "y": coords[1] / 1000.0,
                            "z": coords[2] / 1000.0,
                            "label": f"N{entity_id}"
                        }
                        self.nodes.append(node_data)
    
    def _extract_elements(self) -> None:
        """Extract elements from IFC entities"""
        for entity_id, entity_def in self.entities.items():
            if 'IFCSTRUCTURALMEMBER' in entity_def or 'IFCSTRUCTURALSURFACEMEMBER' in entity_def:
                # Extract element information
                element_data = {
                    "id": str(entity_id),
                    "element_type": "BEAM",  # Simplified
                    "label": f"E{entity_id}"
                }
                self.elements.append(element_data)
    
    def _extract_materials(self) -> None:
        """Extract materials from IFC entities"""
        for entity_id, entity_def in self.entities.items():
            if 'IFCMATERIAL' in entity_def:
                # Extract material information
                material_data = {
                    "id": str(entity_id),
                    "name": f"Material_{entity_id}",
                    "material_type": "steel"  # Simplified
                }
                self.materials.append(material_data)
    
    def _extract_sections(self) -> None:
        """Extract sections from IFC entities"""
        for entity_id, entity_def in self.entities.items():
            if 'PROFILEDEF' in entity_def:
                # Extract section information
                section_data = {
                    "id": str(entity_id),
                    "name": f"Section_{entity_id}",
                    "section_type": "i_section"  # Simplified
                }
                self.sections.append(section_data)
    
    def import_from_file(self, filepath: str) -> Dict[str, Any]:
        """Import model from IFC file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                ifc_content = f.read()
            
            return self.import_model(ifc_content)
            
        except Exception as e:
            raise ExportError(f"Failed to import IFC file: {str(e)}")