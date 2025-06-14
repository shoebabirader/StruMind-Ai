"""
DXF export functionality for structural models
"""

import os
import tempfile
from typing import Dict, List, Optional
import logging

from core.modeling.model import StructuralModel
from core.modeling.nodes import Node
from core.modeling.elements import Element
from core.modeling.materials import Material
from core.modeling.sections import Section

logger = logging.getLogger(__name__)


class DXFExporter:
    """DXF file exporter for structural models"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def export_model(self, model: StructuralModel, output_path: str) -> bool:
        """Export structural model to DXF format"""
        try:
            # For now, create a simple DXF-like text file
            # In production, this would use ezdxf library
            
            with open(output_path, 'w') as f:
                f.write("0\nSECTION\n2\nHEADER\n")
                f.write("9\n$ACADVER\n1\nAC1015\n")
                f.write("0\nENDSEC\n")
                
                # Entities section
                f.write("0\nSECTION\n2\nENTITIES\n")
                
                # Export nodes as points
                for node in model.nodes:
                    f.write("0\nPOINT\n")
                    f.write(f"10\n{node.x}\n")
                    f.write(f"20\n{node.y}\n")
                    f.write(f"30\n{node.z}\n")
                
                # Export elements as lines
                for element in model.elements:
                    if element.start_node and element.end_node:
                        f.write("0\nLINE\n")
                        f.write(f"10\n{element.start_node.x}\n")
                        f.write(f"20\n{element.start_node.y}\n")
                        f.write(f"30\n{element.start_node.z}\n")
                        f.write(f"11\n{element.end_node.x}\n")
                        f.write(f"21\n{element.end_node.y}\n")
                        f.write(f"31\n{element.end_node.z}\n")
                
                f.write("0\nENDSEC\n")
                f.write("0\nEOF\n")
            
            self.logger.info(f"DXF export completed: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"DXF export failed: {str(e)}")
            return False
    
    def export_to_bytes(self, model: StructuralModel) -> Optional[bytes]:
        """Export model to DXF format and return as bytes"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
                if self.export_model(model, tmp_file.name):
                    with open(tmp_file.name, 'rb') as f:
                        data = f.read()
                    os.unlink(tmp_file.name)
                    return data
                else:
                    os.unlink(tmp_file.name)
                    return None
        except Exception as e:
            self.logger.error(f"DXF export to bytes failed: {str(e)}")
            return None
    
    def get_export_info(self) -> Dict[str, str]:
        """Get information about DXF export capabilities"""
        return {
            "format": "DXF",
            "version": "AutoCAD R2000",
            "supported_entities": "Points, Lines",
            "description": "Basic DXF export for structural geometry"
        }