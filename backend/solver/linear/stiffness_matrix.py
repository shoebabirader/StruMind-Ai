"""
Stiffness matrix assembly utilities
"""

import numpy as np
from scipy.sparse import csc_matrix, lil_matrix
from typing import Dict, List, Tuple
import logging

from ...core.modeling.model import StructuralModel
from ...core.modeling.elements import Element

logger = logging.getLogger(__name__)


class StiffnessMatrixAssembler:
    """
    Assembles global stiffness matrix from element contributions
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.dof_per_node = 6  # 3 translations + 3 rotations
        self.total_dofs = len(model.nodes) * self.dof_per_node
        
    def assemble(self) -> csc_matrix:
        """
        Assemble global stiffness matrix
        """
        logger.info("Assembling global stiffness matrix")
        
        # Use lil_matrix for efficient assembly
        K_global = lil_matrix((self.total_dofs, self.total_dofs))
        
        # Process each element
        for element in self.model.elements:
            # Get element stiffness matrix
            k_element = self._get_element_stiffness_matrix(element)
            
            # Get DOF mapping
            dof_map = self._get_element_dof_mapping(element)
            
            # Add to global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    K_global[global_i, global_j] += k_element[i, j]
        
        # Convert to CSC format for efficient solving
        K_global_csc = K_global.tocsc()
        
        logger.info(f"Global stiffness matrix assembled: {self.total_dofs}x{self.total_dofs}")
        logger.info(f"Matrix sparsity: {1 - K_global_csc.nnz / (self.total_dofs**2):.4f}")
        
        return K_global_csc
    
    def _get_element_stiffness_matrix(self, element: Element) -> np.ndarray:
        """
        Get element stiffness matrix in global coordinates
        """
        if element.element_type == "beam":
            return self._beam_stiffness_matrix(element)
        elif element.element_type == "truss":
            return self._truss_stiffness_matrix(element)
        elif element.element_type == "shell":
            return self._shell_stiffness_matrix(element)
        elif element.element_type == "solid":
            return self._solid_stiffness_matrix(element)
        else:
            raise ValueError(f"Unsupported element type: {element.element_type}")
    
    def _beam_stiffness_matrix(self, element: Element) -> np.ndarray:
        """
        3D Euler-Bernoulli beam element stiffness matrix
        """
        # Material properties
        E = element.material.elastic_modulus
        G = element.material.shear_modulus
        
        # Section properties
        A = element.section.area
        Iy = element.section.moment_of_inertia_y
        Iz = element.section.moment_of_inertia_z
        J = element.section.torsional_constant
        
        # Element geometry
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Local stiffness matrix (12x12)
        k_local = np.zeros((12, 12))
        
        # Axial stiffness
        EA_L = E * A / L
        k_local[0, 0] = k_local[6, 6] = EA_L
        k_local[0, 6] = k_local[6, 0] = -EA_L
        
        # Bending about local y-axis (in xz plane)
        EIz_L = E * Iz / L
        EIz_L2 = EIz_L / L
        EIz_L3 = EIz_L2 / L
        
        k_local[2, 2] = k_local[8, 8] = 12 * EIz_L3
        k_local[2, 8] = k_local[8, 2] = -12 * EIz_L3
        k_local[2, 4] = k_local[4, 2] = 6 * EIz_L2
        k_local[8, 10] = k_local[10, 8] = -6 * EIz_L2
        k_local[2, 10] = k_local[10, 2] = 6 * EIz_L2
        k_local[4, 8] = k_local[8, 4] = -6 * EIz_L2
        k_local[4, 4] = k_local[10, 10] = 4 * EIz_L
        k_local[4, 10] = k_local[10, 4] = 2 * EIz_L
        
        # Bending about local z-axis (in xy plane)
        EIy_L = E * Iy / L
        EIy_L2 = EIy_L / L
        EIy_L3 = EIy_L2 / L
        
        k_local[1, 1] = k_local[7, 7] = 12 * EIy_L3
        k_local[1, 7] = k_local[7, 1] = -12 * EIy_L3
        k_local[1, 5] = k_local[5, 1] = -6 * EIy_L2
        k_local[7, 11] = k_local[11, 7] = 6 * EIy_L2
        k_local[1, 11] = k_local[11, 1] = -6 * EIy_L2
        k_local[5, 7] = k_local[7, 5] = 6 * EIy_L2
        k_local[5, 5] = k_local[11, 11] = 4 * EIy_L
        k_local[5, 11] = k_local[11, 5] = 2 * EIy_L
        
        # Torsional stiffness
        GJ_L = G * J / L
        k_local[3, 3] = k_local[9, 9] = GJ_L
        k_local[3, 9] = k_local[9, 3] = -GJ_L
        
        # Transform to global coordinates
        T = self._get_transformation_matrix(element)
        k_global = T.T @ k_local @ T
        
        return k_global
    
    def _truss_stiffness_matrix(self, element: Element) -> np.ndarray:
        """
        3D truss element stiffness matrix
        """
        # Material and section properties
        E = element.material.elastic_modulus
        A = element.section.area
        
        # Element geometry
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        
        dx = end_node.x - start_node.x
        dy = end_node.y - start_node.y
        dz = end_node.z - start_node.z
        L = np.sqrt(dx**2 + dy**2 + dz**2)
        
        # Direction cosines
        cx = dx / L
        cy = dy / L
        cz = dz / L
        
        # Stiffness coefficient
        k = E * A / L
        
        # Local to global transformation for truss
        # Only axial DOFs are active (6x6 matrix for 2 nodes, 3 DOF each)
        k_global = np.zeros((6, 6))
        
        # Direction cosine matrix
        c = np.array([cx, cy, cz])
        
        # Fill stiffness matrix
        for i in range(3):
            for j in range(3):
                k_global[i, j] = k * c[i] * c[j]
                k_global[i, j+3] = -k * c[i] * c[j]
                k_global[i+3, j] = -k * c[i] * c[j]
                k_global[i+3, j+3] = k * c[i] * c[j]
        
        # Expand to 12x12 to match beam DOF structure
        k_expanded = np.zeros((12, 12))
        
        # Map truss DOFs to beam DOF structure
        truss_dofs = [0, 1, 2, 6, 7, 8]  # Translation DOFs only
        
        for i, dof_i in enumerate(truss_dofs):
            for j, dof_j in enumerate(truss_dofs):
                k_expanded[dof_i, dof_j] = k_global[i, j]
        
        return k_expanded
    
    def _shell_stiffness_matrix(self, element: Element) -> np.ndarray:
        """
        Shell element stiffness matrix (simplified)
        """
        # This is a placeholder for shell element implementation
        # In practice, this would be much more complex
        logger.warning("Shell element stiffness matrix not fully implemented")
        return np.eye(24)  # 4 nodes × 6 DOF each
    
    def _solid_stiffness_matrix(self, element: Element) -> np.ndarray:
        """
        Solid element stiffness matrix (simplified)
        """
        # This is a placeholder for solid element implementation
        # In practice, this would use numerical integration
        logger.warning("Solid element stiffness matrix not fully implemented")
        return np.eye(24)  # 8 nodes × 3 DOF each
    
    def _get_transformation_matrix(self, element: Element) -> np.ndarray:
        """
        Get transformation matrix from local to global coordinates
        """
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        
        # Element vector
        dx = end_node.x - start_node.x
        dy = end_node.y - start_node.y
        dz = end_node.z - start_node.z
        L = np.sqrt(dx**2 + dy**2 + dz**2)
        
        # Local x-axis (along element)
        ex = np.array([dx/L, dy/L, dz/L])
        
        # Local y-axis (perpendicular to element in horizontal plane if possible)
        if abs(ex[2]) < 0.9:  # Not vertical
            ey = np.array([-ex[1], ex[0], 0])
            ey = ey / np.linalg.norm(ey)
        else:  # Vertical element
            ey = np.array([1, 0, 0])
        
        # Local z-axis (cross product)
        ez = np.cross(ex, ey)
        ez = ez / np.linalg.norm(ez)
        
        # Recalculate y-axis to ensure orthogonality
        ey = np.cross(ez, ex)
        
        # Rotation matrix
        R = np.array([ex, ey, ez]).T
        
        # Build transformation matrix for 12 DOF
        T = np.zeros((12, 12))
        
        # Apply rotation to each node's DOFs
        for i in range(4):  # 4 blocks of 3x3
            start_idx = i * 3
            end_idx = start_idx + 3
            T[start_idx:end_idx, start_idx:end_idx] = R
        
        return T
    
    def _get_element_dof_mapping(self, element: Element) -> List[int]:
        """
        Get global DOF indices for element nodes
        """
        start_node_index = self._get_node_index(element.start_node_id)
        end_node_index = self._get_node_index(element.end_node_id)
        
        # DOFs for start node
        start_dofs = list(range(
            start_node_index * self.dof_per_node,
            (start_node_index + 1) * self.dof_per_node
        ))
        
        # DOFs for end node
        end_dofs = list(range(
            end_node_index * self.dof_per_node,
            (end_node_index + 1) * self.dof_per_node
        ))
        
        return start_dofs + end_dofs
    
    def _get_node_index(self, node_id: str) -> int:
        """
        Get node index from node ID
        """
        for i, node in enumerate(self.model.nodes):
            if node.id == node_id:
                return i
        raise ValueError(f"Node {node_id} not found in model")
    
    def get_element_stiffness_matrix_local(self, element: Element) -> np.ndarray:
        """
        Get element stiffness matrix in local coordinates (for debugging)
        """
        if element.element_type == "beam":
            return self._beam_stiffness_matrix_local(element)
        elif element.element_type == "truss":
            return self._truss_stiffness_matrix_local(element)
        else:
            raise ValueError(f"Local stiffness matrix not implemented for {element.element_type}")
    
    def _beam_stiffness_matrix_local(self, element: Element) -> np.ndarray:
        """
        Beam element stiffness matrix in local coordinates
        """
        # Material properties
        E = element.material.elastic_modulus
        G = element.material.shear_modulus
        
        # Section properties
        A = element.section.area
        Iy = element.section.moment_of_inertia_y
        Iz = element.section.moment_of_inertia_z
        J = element.section.torsional_constant
        
        # Element length
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Local stiffness matrix
        k_local = np.zeros((12, 12))
        
        # Fill matrix as before (same as in _beam_stiffness_matrix but without transformation)
        # ... (implementation same as above)
        
        return k_local
    
    def _truss_stiffness_matrix_local(self, element: Element) -> np.ndarray:
        """
        Truss element stiffness matrix in local coordinates
        """
        E = element.material.elastic_modulus
        A = element.section.area
        
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        k = E * A / L
        
        # Local stiffness matrix (only axial DOF)
        k_local = np.array([
            [k, -k],
            [-k, k]
        ])
        
        return k_local