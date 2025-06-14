"""
BIM visualization and viewer functionality
"""

from typing import Dict, List, Optional, Any
import logging

from core.modeling.model import StructuralModel

logger = logging.getLogger(__name__)


class BIMViewer:
    """BIM model viewer and visualization utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_3d_view_data(self, model: StructuralModel) -> Dict[str, Any]:
        """Generate 3D view data for BIM model"""
        try:
            view_data = {
                "nodes": [],
                "elements": [],
                "materials": [],
                "sections": [],
                "bounds": {
                    "min_x": 0, "max_x": 0,
                    "min_y": 0, "max_y": 0,
                    "min_z": 0, "max_z": 0
                }
            }
            
            # Process nodes
            if model.nodes:
                x_coords = [node.x for node in model.nodes]
                y_coords = [node.y for node in model.nodes]
                z_coords = [node.z for node in model.nodes]
                
                view_data["bounds"] = {
                    "min_x": min(x_coords), "max_x": max(x_coords),
                    "min_y": min(y_coords), "max_y": max(y_coords),
                    "min_z": min(z_coords), "max_z": max(z_coords)
                }
                
                for node in model.nodes:
                    view_data["nodes"].append({
                        "id": str(node.id),
                        "x": node.x,
                        "y": node.y,
                        "z": node.z,
                        "label": node.label or f"Node {node.id}"
                    })
            
            # Process elements
            for element in model.elements:
                if element.start_node and element.end_node:
                    view_data["elements"].append({
                        "id": str(element.id),
                        "start_node_id": str(element.start_node.id),
                        "end_node_id": str(element.end_node.id),
                        "element_type": element.element_type,
                        "material_id": str(element.material_id) if element.material_id else None,
                        "section_id": str(element.section_id) if element.section_id else None,
                        "label": element.label or f"Element {element.id}"
                    })
            
            # Process materials
            for material in model.materials:
                view_data["materials"].append({
                    "id": str(material.id),
                    "name": material.name,
                    "material_type": material.material_type,
                    "grade": material.grade
                })
            
            # Process sections
            for section in model.sections:
                view_data["sections"].append({
                    "id": str(section.id),
                    "name": section.name,
                    "section_type": section.section_type,
                    "properties": section.properties
                })
            
            return view_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate 3D view data: {str(e)}")
            return {"error": str(e)}
    
    def generate_section_view(self, model: StructuralModel, plane: str = "xy") -> Dict[str, Any]:
        """Generate 2D section view data"""
        try:
            section_data = {
                "nodes": [],
                "elements": [],
                "plane": plane
            }
            
            # Project nodes to 2D based on plane
            for node in model.nodes:
                if plane == "xy":
                    section_data["nodes"].append({
                        "id": str(node.id),
                        "x": node.x,
                        "y": node.y,
                        "label": node.label or f"Node {node.id}"
                    })
                elif plane == "xz":
                    section_data["nodes"].append({
                        "id": str(node.id),
                        "x": node.x,
                        "y": node.z,
                        "label": node.label or f"Node {node.id}"
                    })
                elif plane == "yz":
                    section_data["nodes"].append({
                        "id": str(node.id),
                        "x": node.y,
                        "y": node.z,
                        "label": node.label or f"Node {node.id}"
                    })
            
            # Project elements to 2D
            for element in model.elements:
                if element.start_node and element.end_node:
                    section_data["elements"].append({
                        "id": str(element.id),
                        "start_node_id": str(element.start_node.id),
                        "end_node_id": str(element.end_node.id),
                        "element_type": element.element_type,
                        "label": element.label or f"Element {element.id}"
                    })
            
            return section_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate section view: {str(e)}")
            return {"error": str(e)}
    
    def get_viewer_settings(self) -> Dict[str, Any]:
        """Get default viewer settings"""
        return {
            "camera": {
                "position": [10, 10, 10],
                "target": [0, 0, 0],
                "up": [0, 0, 1]
            },
            "rendering": {
                "show_nodes": True,
                "show_elements": True,
                "show_labels": False,
                "wireframe": False,
                "background_color": "#f0f0f0"
            },
            "colors": {
                "nodes": "#ff0000",
                "elements": "#0000ff",
                "selected": "#00ff00",
                "highlighted": "#ffff00"
            }
        }