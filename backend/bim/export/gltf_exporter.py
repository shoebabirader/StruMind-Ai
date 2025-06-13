"""
glTF (GL Transmission Format) export functionality for 3D visualization
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import base64
import struct
import numpy as np

from db.models.structural import Node, Element, Material, Section
from db.models.project import Project
from core.exceptions import ExportError


class GLTFExporter:
    """glTF exporter for structural models"""
    
    def __init__(self):
        self.buffers = []
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.nodes = []
        self.materials = []
        self.scenes = []
        self.current_buffer_offset = 0
    
    def export_model(self, project: Project, nodes: List[Node], elements: List[Element],
                    materials: List[Material], sections: List[Section],
                    include_results: bool = False, results_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Export structural model to glTF format"""
        
        # Reset internal state
        self._reset_state()
        
        # Create materials
        self._create_materials(materials)
        
        # Create geometry for elements
        self._create_element_geometry(elements, nodes, sections)
        
        # Create scene
        scene_nodes = list(range(len(self.nodes)))
        self.scenes.append({
            "name": project.name,
            "nodes": scene_nodes
        })
        
        # Build glTF JSON
        gltf_json = {
            "asset": {
                "version": "2.0",
                "generator": "StruMind Platform",
                "copyright": f"© {project.name}"
            },
            "scene": 0,
            "scenes": self.scenes,
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": self.buffers
        }
        
        # Add extensions for structural data
        if include_results and results_data:
            gltf_json["extensions"] = {
                "STRUMIND_structural_results": results_data
            }
            gltf_json["extensionsUsed"] = ["STRUMIND_structural_results"]
        
        return gltf_json
    
    def _reset_state(self):
        """Reset internal state for new export"""
        self.buffers = []
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.nodes = []
        self.materials = []
        self.scenes = []
        self.current_buffer_offset = 0
    
    def _create_materials(self, materials: List[Material]):
        """Create glTF materials"""
        # Default material for elements without material
        self.materials.append({
            "name": "Default Steel",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.7, 0.7, 0.8, 1.0],
                "metallicFactor": 0.8,
                "roughnessFactor": 0.3
            }
        })
        
        # Create materials from database
        for material in materials:
            if material.material_type == "steel":
                base_color = [0.7, 0.7, 0.8, 1.0]
                metallic = 0.8
                roughness = 0.3
            elif material.material_type == "concrete":
                base_color = [0.8, 0.8, 0.7, 1.0]
                metallic = 0.0
                roughness = 0.9
            else:
                base_color = [0.6, 0.6, 0.6, 1.0]
                metallic = 0.5
                roughness = 0.5
            
            self.materials.append({
                "name": material.name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": base_color,
                    "metallicFactor": metallic,
                    "roughnessFactor": roughness
                }
            })
    
    def _create_element_geometry(self, elements: List[Element], nodes: List[Node], sections: List[Section]):
        """Create geometry for structural elements"""
        # Create node lookup
        node_lookup = {node.id: node for node in nodes}
        section_lookup = {section.id: section for section in sections}
        
        for element in elements:
            if element.element_type in ["BEAM", "COLUMN", "BRACE"]:
                self._create_beam_geometry(element, node_lookup, section_lookup)
            elif element.element_type in ["SHELL", "PLATE", "WALL", "SLAB"]:
                self._create_shell_geometry(element, node_lookup)
    
    def _create_beam_geometry(self, element: Element, node_lookup: Dict, section_lookup: Dict):
        """Create geometry for beam elements"""
        start_node = node_lookup.get(element.start_node_id)
        end_node = node_lookup.get(element.end_node_id)
        
        if not start_node or not end_node:
            return
        
        # Get section properties
        section = section_lookup.get(element.section_id) if element.section_id else None
        
        if section and section.section_type == "i_section":
            # Create I-beam geometry
            vertices, indices = self._create_i_beam_mesh(start_node, end_node, section)
        elif section and section.section_type == "rectangular":
            # Create rectangular beam geometry
            vertices, indices = self._create_rectangular_beam_mesh(start_node, end_node, section)
        else:
            # Create simple line representation
            vertices, indices = self._create_line_mesh(start_node, end_node)
        
        # Create mesh
        mesh_index = self._create_mesh(vertices, indices, element.label or f"Element_{element.id}")
        
        # Create node
        self.nodes.append({
            "name": element.label or f"Element_{element.id}",
            "mesh": mesh_index
        })
    
    def _create_i_beam_mesh(self, start_node: Node, end_node: Node, section: Section) -> Tuple[np.ndarray, np.ndarray]:
        """Create I-beam mesh geometry"""
        props = section.properties
        
        # I-beam dimensions (convert to meters)
        depth = props.get('d', 400) / 1000.0      # Overall depth
        width = props.get('bf', 200) / 1000.0     # Flange width
        web_thickness = props.get('tw', 10) / 1000.0   # Web thickness
        flange_thickness = props.get('tf', 15) / 1000.0 # Flange thickness
        
        # Create I-beam cross-section points
        half_width = width / 2
        half_web = web_thickness / 2
        half_depth = depth / 2
        
        # Cross-section vertices (local coordinates)
        cross_section = np.array([
            # Top flange
            [-half_width, half_depth, 0],
            [half_width, half_depth, 0],
            [half_width, half_depth - flange_thickness, 0],
            [half_web, half_depth - flange_thickness, 0],
            # Web
            [half_web, -half_depth + flange_thickness, 0],
            [half_width, -half_depth + flange_thickness, 0],
            [half_width, -half_depth, 0],
            [-half_width, -half_depth, 0],
            # Bottom flange
            [-half_width, -half_depth + flange_thickness, 0],
            [-half_web, -half_depth + flange_thickness, 0],
            [-half_web, half_depth - flange_thickness, 0],
            [-half_width, half_depth - flange_thickness, 0]
        ])
        
        # Extrude along beam length
        beam_vector = np.array([end_node.x - start_node.x, 
                               end_node.y - start_node.y, 
                               end_node.z - start_node.z])
        beam_length = np.linalg.norm(beam_vector)
        beam_direction = beam_vector / beam_length if beam_length > 0 else np.array([1, 0, 0])
        
        # Create transformation matrix
        transform = self._create_beam_transform(start_node, end_node)
        
        # Create vertices by extruding cross-section
        vertices = []
        n_cross = len(cross_section)
        
        # Start cross-section
        for point in cross_section:
            local_point = np.array([point[0], point[1], 0, 1])
            world_point = transform @ local_point
            vertices.append([world_point[0], world_point[1], world_point[2]])
        
        # End cross-section
        end_transform = transform.copy()
        end_transform[0:3, 3] = [end_node.x, end_node.y, end_node.z]
        
        for point in cross_section:
            local_point = np.array([point[0], point[1], 0, 1])
            world_point = end_transform @ local_point
            vertices.append([world_point[0], world_point[1], world_point[2]])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Create indices for triangulated faces
        indices = []
        
        # Side faces
        for i in range(n_cross):
            next_i = (i + 1) % n_cross
            
            # Two triangles per quad
            indices.extend([
                i, i + n_cross, next_i,
                next_i, i + n_cross, next_i + n_cross
            ])
        
        # End caps (simplified triangulation)
        center_start = len(vertices)
        center_end = center_start + 1
        
        # Add center points
        start_center = np.mean(vertices[:n_cross], axis=0)
        end_center = np.mean(vertices[n_cross:2*n_cross], axis=0)
        vertices = np.vstack([vertices, start_center, end_center])
        
        # Start cap
        for i in range(n_cross):
            next_i = (i + 1) % n_cross
            indices.extend([center_start, next_i, i])
        
        # End cap
        for i in range(n_cross):
            next_i = (i + 1) % n_cross
            indices.extend([center_end, i + n_cross, next_i + n_cross])
        
        return vertices, np.array(indices, dtype=np.uint16)
    
    def _create_rectangular_beam_mesh(self, start_node: Node, end_node: Node, section: Section) -> Tuple[np.ndarray, np.ndarray]:
        """Create rectangular beam mesh geometry"""
        props = section.properties
        
        # Rectangular dimensions (convert to meters)
        width = props.get('width', 300) / 1000.0
        height = props.get('height', 500) / 1000.0
        
        half_width = width / 2
        half_height = height / 2
        
        # Create rectangular cross-section
        cross_section = np.array([
            [-half_width, -half_height, 0],
            [half_width, -half_height, 0],
            [half_width, half_height, 0],
            [-half_width, half_height, 0]
        ])
        
        # Create transformation matrix
        transform = self._create_beam_transform(start_node, end_node)
        
        # Create vertices
        vertices = []
        
        # Start cross-section
        for point in cross_section:
            local_point = np.array([point[0], point[1], 0, 1])
            world_point = transform @ local_point
            vertices.append([world_point[0], world_point[1], world_point[2]])
        
        # End cross-section
        end_transform = transform.copy()
        end_transform[0:3, 3] = [end_node.x, end_node.y, end_node.z]
        
        for point in cross_section:
            local_point = np.array([point[0], point[1], 0, 1])
            world_point = end_transform @ local_point
            vertices.append([world_point[0], world_point[1], world_point[2]])
        
        vertices = np.array(vertices, dtype=np.float32)
        
        # Create indices for box geometry
        indices = np.array([
            # Bottom face
            0, 1, 5, 0, 5, 4,
            # Top face
            2, 3, 7, 2, 7, 6,
            # Front face
            1, 2, 6, 1, 6, 5,
            # Back face
            3, 0, 4, 3, 4, 7,
            # Left face
            0, 3, 2, 0, 2, 1,
            # Right face
            4, 5, 6, 4, 6, 7
        ], dtype=np.uint16)
        
        return vertices, indices
    
    def _create_line_mesh(self, start_node: Node, end_node: Node) -> Tuple[np.ndarray, np.ndarray]:
        """Create simple line mesh for elements without detailed geometry"""
        vertices = np.array([
            [start_node.x, start_node.y, start_node.z],
            [end_node.x, end_node.y, end_node.z]
        ], dtype=np.float32)
        
        indices = np.array([0, 1], dtype=np.uint16)
        
        return vertices, indices
    
    def _create_shell_geometry(self, element: Element, node_lookup: Dict):
        """Create geometry for shell elements"""
        # Simplified shell representation as a quad
        start_node = node_lookup.get(element.start_node_id)
        end_node = node_lookup.get(element.end_node_id)
        
        if not start_node or not end_node:
            return
        
        # Create simple quad (would need more nodes for proper shell)
        thickness = 0.1  # Default thickness
        if element.properties and 'thickness' in element.properties:
            thickness = element.properties['thickness']
        
        # Create quad vertices
        vertices = np.array([
            [start_node.x, start_node.y, start_node.z],
            [end_node.x, start_node.y, start_node.z],
            [end_node.x, end_node.y, start_node.z],
            [start_node.x, end_node.y, start_node.z],
            # Top face
            [start_node.x, start_node.y, start_node.z + thickness],
            [end_node.x, start_node.y, start_node.z + thickness],
            [end_node.x, end_node.y, start_node.z + thickness],
            [start_node.x, end_node.y, start_node.z + thickness]
        ], dtype=np.float32)
        
        # Create indices for shell
        indices = np.array([
            # Bottom face
            0, 1, 2, 0, 2, 3,
            # Top face
            4, 6, 5, 4, 7, 6,
            # Side faces
            0, 4, 5, 0, 5, 1,
            1, 5, 6, 1, 6, 2,
            2, 6, 7, 2, 7, 3,
            3, 7, 4, 3, 4, 0
        ], dtype=np.uint16)
        
        # Create mesh
        mesh_index = self._create_mesh(vertices, indices, element.label or f"Shell_{element.id}")
        
        # Create node
        self.nodes.append({
            "name": element.label or f"Shell_{element.id}",
            "mesh": mesh_index
        })
    
    def _create_beam_transform(self, start_node: Node, end_node: Node) -> np.ndarray:
        """Create transformation matrix for beam local coordinate system"""
        # Beam direction (local x-axis)
        beam_vector = np.array([end_node.x - start_node.x, 
                               end_node.y - start_node.y, 
                               end_node.z - start_node.z])
        beam_length = np.linalg.norm(beam_vector)
        
        if beam_length == 0:
            return np.eye(4)
        
        x_axis = beam_vector / beam_length
        
        # Create local y and z axes
        # Use global Z as reference for horizontal beams
        if abs(x_axis[2]) < 0.9:  # Not vertical
            z_axis = np.array([0, 0, 1])
            y_axis = np.cross(z_axis, x_axis)
            y_axis = y_axis / np.linalg.norm(y_axis)
            z_axis = np.cross(x_axis, y_axis)
        else:  # Vertical beam
            y_axis = np.array([0, 1, 0])
            z_axis = np.cross(x_axis, y_axis)
            z_axis = z_axis / np.linalg.norm(z_axis)
            y_axis = np.cross(z_axis, x_axis)
        
        # Create transformation matrix
        transform = np.eye(4)
        transform[0:3, 0] = x_axis
        transform[0:3, 1] = y_axis
        transform[0:3, 2] = z_axis
        transform[0:3, 3] = [start_node.x, start_node.y, start_node.z]
        
        return transform
    
    def _create_mesh(self, vertices: np.ndarray, indices: np.ndarray, name: str) -> int:
        """Create glTF mesh from vertices and indices"""
        # Create buffer for vertices
        vertex_buffer = vertices.tobytes()
        vertex_buffer_view = self._create_buffer_view(vertex_buffer, 34962)  # ARRAY_BUFFER
        vertex_accessor = self._create_accessor(vertex_buffer_view, 5126, len(vertices), "VEC3")  # FLOAT
        
        # Create buffer for indices
        index_buffer = indices.tobytes()
        index_buffer_view = self._create_buffer_view(index_buffer, 34963)  # ELEMENT_ARRAY_BUFFER
        index_accessor = self._create_accessor(index_buffer_view, 5123, len(indices), "SCALAR")  # UNSIGNED_SHORT
        
        # Calculate bounding box
        min_vals = vertices.min(axis=0).tolist()
        max_vals = vertices.max(axis=0).tolist()
        
        # Update accessor with bounds
        self.accessors[vertex_accessor]["min"] = min_vals
        self.accessors[vertex_accessor]["max"] = max_vals
        
        # Create mesh
        mesh = {
            "name": name,
            "primitives": [{
                "attributes": {
                    "POSITION": vertex_accessor
                },
                "indices": index_accessor,
                "material": 0  # Use first material
            }]
        }
        
        mesh_index = len(self.meshes)
        self.meshes.append(mesh)
        
        return mesh_index
    
    def _create_buffer_view(self, data: bytes, target: int) -> int:
        """Create glTF buffer view"""
        buffer_view = {
            "buffer": 0,  # Single buffer for simplicity
            "byteOffset": self.current_buffer_offset,
            "byteLength": len(data),
            "target": target
        }
        
        # Add to main buffer
        if not self.buffers:
            self.buffers.append({"byteLength": 0, "uri": ""})
        
        # Update buffer size
        self.buffers[0]["byteLength"] += len(data)
        self.current_buffer_offset += len(data)
        
        buffer_view_index = len(self.buffer_views)
        self.buffer_views.append(buffer_view)
        
        return buffer_view_index
    
    def _create_accessor(self, buffer_view: int, component_type: int, count: int, type_str: str) -> int:
        """Create glTF accessor"""
        accessor = {
            "bufferView": buffer_view,
            "componentType": component_type,
            "count": count,
            "type": type_str
        }
        
        accessor_index = len(self.accessors)
        self.accessors.append(accessor)
        
        return accessor_index
    
    def export_to_file(self, filepath: str, project: Project, nodes: List[Node],
                      elements: List[Element], materials: List[Material],
                      sections: List[Section], include_results: bool = False,
                      results_data: Optional[Dict] = None) -> None:
        """Export model to glTF file"""
        try:
            gltf_json = self.export_model(project, nodes, elements, materials, sections,
                                        include_results, results_data)
            
            # Create binary buffer data
            buffer_data = self._create_buffer_data()
            
            # Encode buffer as data URI
            if buffer_data:
                encoded_buffer = base64.b64encode(buffer_data).decode('ascii')
                gltf_json["buffers"][0]["uri"] = f"data:application/octet-stream;base64,{encoded_buffer}"
            
            # Write JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(gltf_json, f, indent=2)
                
        except Exception as e:
            raise ExportError(f"Failed to export glTF file: {str(e)}")
    
    def _create_buffer_data(self) -> bytes:
        """Create binary buffer data from all geometry"""
        buffer_data = b""
        
        # This would collect all the binary data from vertices and indices
        # For simplicity, returning empty buffer (data URIs would be used instead)
        
        return buffer_data
    
    def export_with_results(self, project: Project, nodes: List[Node], elements: List[Element],
                           materials: List[Material], sections: List[Section],
                           analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Export model with analysis results for visualization"""
        
        # Create base model
        gltf_json = self.export_model(project, nodes, elements, materials, sections)
        
        # Add result visualization data
        if analysis_results:
            # Create color-coded materials based on results
            self._create_result_materials(analysis_results)
            
            # Add result data as extension
            gltf_json["extensions"] = {
                "STRUMIND_structural_results": {
                    "displacements": analysis_results.get("displacements", {}),
                    "stresses": analysis_results.get("stresses", {}),
                    "forces": analysis_results.get("forces", {}),
                    "scale_factors": analysis_results.get("scale_factors", {})
                }
            }
            gltf_json["extensionsUsed"] = ["STRUMIND_structural_results"]
        
        return gltf_json
    
    def _create_result_materials(self, results: Dict[str, Any]):
        """Create materials for result visualization"""
        # Add stress visualization materials
        stress_levels = [
            {"name": "Low Stress", "color": [0.0, 1.0, 0.0, 1.0]},    # Green
            {"name": "Medium Stress", "color": [1.0, 1.0, 0.0, 1.0]}, # Yellow
            {"name": "High Stress", "color": [1.0, 0.5, 0.0, 1.0]},   # Orange
            {"name": "Critical Stress", "color": [1.0, 0.0, 0.0, 1.0]} # Red
        ]
        
        for stress_material in stress_levels:
            self.materials.append({
                "name": stress_material["name"],
                "pbrMetallicRoughness": {
                    "baseColorFactor": stress_material["color"],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8
                }
            })