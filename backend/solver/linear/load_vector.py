"""
Load vector assembly utilities
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase, NodalLoad, ElementLoad

logger = logging.getLogger(__name__)


class LoadVectorAssembler:
    """
    Assembles global load vector from applied loads
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.dof_per_node = 6  # 3 translations + 3 rotations
        self.total_dofs = len(model.nodes) * self.dof_per_node
        
    def assemble(self, load_case: LoadCase) -> np.ndarray:
        """
        Assemble global load vector for given load case
        """
        logger.info(f"Assembling load vector for case: {load_case.name}")
        
        # Initialize global load vector
        F_global = np.zeros(self.total_dofs)
        
        # Add nodal loads
        self._add_nodal_loads(F_global, load_case.nodal_loads)
        
        # Add element loads (converted to equivalent nodal loads)
        self._add_element_loads(F_global, load_case.element_loads)
        
        # Add distributed loads
        if hasattr(load_case, 'distributed_loads'):
            self._add_distributed_loads(F_global, load_case.distributed_loads)
        
        # Add pressure loads
        if hasattr(load_case, 'pressure_loads'):
            self._add_pressure_loads(F_global, load_case.pressure_loads)
        
        logger.info(f"Load vector assembled with {np.count_nonzero(F_global)} non-zero entries")
        
        return F_global
    
    def _add_nodal_loads(self, F_global: np.ndarray, nodal_loads: List[NodalLoad]):
        """
        Add nodal loads to global load vector
        """
        for load in nodal_loads:
            node_index = self._get_node_index(load.node_id)
            dof_start = node_index * self.dof_per_node
            
            # Add force components
            F_global[dof_start] += load.fx      # X-direction force
            F_global[dof_start + 1] += load.fy  # Y-direction force
            F_global[dof_start + 2] += load.fz  # Z-direction force
            
            # Add moment components
            F_global[dof_start + 3] += load.mx  # X-direction moment
            F_global[dof_start + 4] += load.my  # Y-direction moment
            F_global[dof_start + 5] += load.mz  # Z-direction moment
    
    def _add_element_loads(self, F_global: np.ndarray, element_loads: List[ElementLoad]):
        """
        Add element loads converted to equivalent nodal loads
        """
        for load in element_loads:
            element = self.model.get_element(load.element_id)
            
            if load.load_type == "distributed":
                equivalent_loads = self._convert_distributed_load(element, load)
            elif load.load_type == "point":
                equivalent_loads = self._convert_point_load(element, load)
            else:
                logger.warning(f"Unsupported element load type: {load.load_type}")
                continue
            
            # Add equivalent loads to global vector
            for node_id, forces in equivalent_loads.items():
                node_index = self._get_node_index(node_id)
                dof_start = node_index * self.dof_per_node
                
                for i, force in enumerate(forces):
                    F_global[dof_start + i] += force
    
    def _convert_distributed_load(self, element, load) -> Dict[str, List[float]]:
        """
        Convert distributed load to equivalent nodal loads
        """
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        
        # Element length
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # For uniform distributed load on beam element
        if element.element_type == "beam":
            return self._beam_distributed_load_equivalent(element, load, L)
        elif element.element_type == "truss":
            return self._truss_distributed_load_equivalent(element, load, L)
        else:
            logger.warning(f"Distributed load conversion not implemented for {element.element_type}")
            return {}
    
    def _beam_distributed_load_equivalent(self, element, load, L: float) -> Dict[str, List[float]]:
        """
        Convert distributed load on beam to equivalent nodal loads
        """
        # Uniform distributed load intensity
        wx = getattr(load, 'wx', 0.0)  # Load per unit length in X
        wy = getattr(load, 'wy', 0.0)  # Load per unit length in Y
        wz = getattr(load, 'wz', 0.0)  # Load per unit length in Z
        
        # Total load
        Px_total = wx * L
        Py_total = wy * L
        Pz_total = wz * L
        
        # For uniform load, each node gets half the total load
        # Plus moments for transverse loads
        
        equivalent_loads = {}
        
        # Start node
        equivalent_loads[element.start_node_id] = [
            Px_total / 2,  # Fx
            Py_total / 2,  # Fy
            Pz_total / 2,  # Fz
            0.0,           # Mx
            -wz * L**2 / 12,  # My (moment due to distributed load in Z)
            wy * L**2 / 12,   # Mz (moment due to distributed load in Y)
        ]
        
        # End node
        equivalent_loads[element.end_node_id] = [
            Px_total / 2,  # Fx
            Py_total / 2,  # Fy
            Pz_total / 2,  # Fz
            0.0,           # Mx
            wz * L**2 / 12,   # My
            -wy * L**2 / 12,  # Mz
        ]
        
        return equivalent_loads
    
    def _truss_distributed_load_equivalent(self, element, load, L: float) -> Dict[str, List[float]]:
        """
        Convert distributed load on truss to equivalent nodal loads
        """
        # For truss, only axial loads are considered
        wx = getattr(load, 'wx', 0.0)
        wy = getattr(load, 'wy', 0.0)
        wz = getattr(load, 'wz', 0.0)
        
        # Total load distributed equally to nodes
        equivalent_loads = {}
        
        # Start node
        equivalent_loads[element.start_node_id] = [
            wx * L / 2,  # Fx
            wy * L / 2,  # Fy
            wz * L / 2,  # Fz
            0.0, 0.0, 0.0  # No moments for truss
        ]
        
        # End node
        equivalent_loads[element.end_node_id] = [
            wx * L / 2,  # Fx
            wy * L / 2,  # Fy
            wz * L / 2,  # Fz
            0.0, 0.0, 0.0  # No moments for truss
        ]
        
        return equivalent_loads
    
    def _convert_point_load(self, element, load) -> Dict[str, List[float]]:
        """
        Convert point load on element to equivalent nodal loads
        """
        # Load position along element (0 to 1)
        position = getattr(load, 'position', 0.5)  # Default to mid-span
        
        # Load components
        fx = getattr(load, 'fx', 0.0)
        fy = getattr(load, 'fy', 0.0)
        fz = getattr(load, 'fz', 0.0)
        
        # Element length
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Distance from start node
        a = position * L
        b = L - a
        
        if element.element_type == "beam":
            return self._beam_point_load_equivalent(element, load, a, b, L)
        elif element.element_type == "truss":
            return self._truss_point_load_equivalent(element, load, a, b, L)
        else:
            logger.warning(f"Point load conversion not implemented for {element.element_type}")
            return {}
    
    def _beam_point_load_equivalent(self, element, load, a: float, b: float, L: float) -> Dict[str, List[float]]:
        """
        Convert point load on beam to equivalent nodal loads using shape functions
        """
        fx = getattr(load, 'fx', 0.0)
        fy = getattr(load, 'fy', 0.0)
        fz = getattr(load, 'fz', 0.0)
        
        equivalent_loads = {}
        
        # For axial load (simple linear interpolation)
        # Start node gets (b/L) of the load, end node gets (a/L)
        
        # For transverse loads, use beam shape functions
        # Simplified approach: linear distribution for axial, shape function for transverse
        
        # Start node
        equivalent_loads[element.start_node_id] = [
            fx * b / L,  # Fx (linear distribution)
            fy * b / L,  # Fy (simplified)
            fz * b / L,  # Fz (simplified)
            0.0,         # Mx
            -fz * a * b**2 / (L**2),  # My (approximate)
            fy * a * b**2 / (L**2),   # Mz (approximate)
        ]
        
        # End node
        equivalent_loads[element.end_node_id] = [
            fx * a / L,  # Fx
            fy * a / L,  # Fy
            fz * a / L,  # Fz
            0.0,         # Mx
            fz * a**2 * b / (L**2),   # My
            -fy * a**2 * b / (L**2),  # Mz
        ]
        
        return equivalent_loads
    
    def _truss_point_load_equivalent(self, element, load, a: float, b: float, L: float) -> Dict[str, List[float]]:
        """
        Convert point load on truss to equivalent nodal loads
        """
        fx = getattr(load, 'fx', 0.0)
        fy = getattr(load, 'fy', 0.0)
        fz = getattr(load, 'fz', 0.0)
        
        equivalent_loads = {}
        
        # Linear distribution based on position
        # Start node
        equivalent_loads[element.start_node_id] = [
            fx * b / L,  # Fx
            fy * b / L,  # Fy
            fz * b / L,  # Fz
            0.0, 0.0, 0.0  # No moments for truss
        ]
        
        # End node
        equivalent_loads[element.end_node_id] = [
            fx * a / L,  # Fx
            fy * a / L,  # Fy
            fz * a / L,  # Fz
            0.0, 0.0, 0.0  # No moments for truss
        ]
        
        return equivalent_loads
    
    def _add_distributed_loads(self, F_global: np.ndarray, distributed_loads: List):
        """
        Add distributed loads (area loads, pressure loads, etc.)
        """
        # This would handle surface loads on shell/plate elements
        # Implementation depends on element types and load definitions
        logger.info("Processing distributed loads")
        pass
    
    def _add_pressure_loads(self, F_global: np.ndarray, pressure_loads: List):
        """
        Add pressure loads on surfaces
        """
        # This would handle pressure loads on shell/solid element faces
        logger.info("Processing pressure loads")
        pass
    
    def _get_node_index(self, node_id: str) -> int:
        """
        Get node index from node ID
        """
        for i, node in enumerate(self.model.nodes):
            if node.id == node_id:
                return i
        raise ValueError(f"Node {node_id} not found in model")
    
    def get_load_summary(self, load_case: LoadCase) -> Dict:
        """
        Get summary of loads in the load case
        """
        summary = {
            "total_nodal_loads": len(load_case.nodal_loads),
            "total_element_loads": len(load_case.element_loads),
            "total_force_x": 0.0,
            "total_force_y": 0.0,
            "total_force_z": 0.0,
            "total_moment_x": 0.0,
            "total_moment_y": 0.0,
            "total_moment_z": 0.0
        }
        
        # Sum nodal loads
        for load in load_case.nodal_loads:
            summary["total_force_x"] += load.fx
            summary["total_force_y"] += load.fy
            summary["total_force_z"] += load.fz
            summary["total_moment_x"] += load.mx
            summary["total_moment_y"] += load.my
            summary["total_moment_z"] += load.mz
        
        # Note: Element loads would need to be converted to get total forces
        
        return summary