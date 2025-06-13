"""
Linear solver implementation for structural analysis
"""

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import spsolve
from typing import Dict, List, Tuple, Optional
import logging

from ..matrix import GlobalStiffnessMatrix
from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase
from ...core.modeling.boundary_conditions import BoundaryCondition

logger = logging.getLogger(__name__)


class LinearSolver:
    """
    Linear static analysis solver using direct methods
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.global_stiffness = None
        self.global_load_vector = None
        self.displacement_vector = None
        self.reaction_forces = None
        self.element_forces = None
        
    def assemble_global_stiffness_matrix(self) -> csc_matrix:
        """
        Assemble global stiffness matrix from element stiffness matrices
        """
        logger.info("Assembling global stiffness matrix")
        
        # Get total DOFs
        total_dofs = len(self.model.nodes) * 6  # 6 DOF per node (3 translations + 3 rotations)
        
        # Initialize global stiffness matrix
        K_global = np.zeros((total_dofs, total_dofs))
        
        # Assemble element contributions
        for element in self.model.elements:
            # Get element stiffness matrix in global coordinates
            k_element = self._get_element_stiffness_matrix(element)
            
            # Get element DOF mapping
            dof_map = self._get_element_dof_mapping(element)
            
            # Add element contribution to global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    K_global[global_i, global_j] += k_element[i, j]
        
        # Convert to sparse matrix for efficiency
        self.global_stiffness = csc_matrix(K_global)
        logger.info(f"Global stiffness matrix assembled: {total_dofs}x{total_dofs}")
        
        return self.global_stiffness
    
    def assemble_global_load_vector(self, load_case: LoadCase) -> np.ndarray:
        """
        Assemble global load vector from applied loads
        """
        logger.info(f"Assembling global load vector for load case: {load_case.name}")
        
        total_dofs = len(self.model.nodes) * 6
        F_global = np.zeros(total_dofs)
        
        # Add nodal loads
        for load in load_case.nodal_loads:
            node_id = load.node_id
            node_index = self._get_node_index(node_id)
            
            # Map load components to DOFs
            dof_start = node_index * 6
            F_global[dof_start:dof_start + 3] += [load.fx, load.fy, load.fz]
            F_global[dof_start + 3:dof_start + 6] += [load.mx, load.my, load.mz]
        
        # Add element loads (distributed loads converted to equivalent nodal loads)
        for load in load_case.element_loads:
            equivalent_loads = self._convert_element_load_to_nodal(load)
            for node_id, forces in equivalent_loads.items():
                node_index = self._get_node_index(node_id)
                dof_start = node_index * 6
                F_global[dof_start:dof_start + 6] += forces
        
        self.global_load_vector = F_global
        logger.info("Global load vector assembled")
        
        return self.global_load_vector
    
    def apply_boundary_conditions(self, boundary_conditions: List[BoundaryCondition]):
        """
        Apply boundary conditions by modifying stiffness matrix and load vector
        """
        logger.info("Applying boundary conditions")
        
        # Create modified matrices
        K_modified = self.global_stiffness.toarray().copy()
        F_modified = self.global_load_vector.copy()
        
        # Track constrained DOFs
        constrained_dofs = []
        
        for bc in boundary_conditions:
            node_index = self._get_node_index(bc.node_id)
            dof_start = node_index * 6
            
            # Apply constraints based on support type
            if bc.support_type == "fixed":
                # All 6 DOFs constrained
                for i in range(6):
                    dof = dof_start + i
                    constrained_dofs.append(dof)
                    
            elif bc.support_type == "pinned":
                # Translation DOFs constrained (0, 1, 2)
                for i in range(3):
                    dof = dof_start + i
                    constrained_dofs.append(dof)
                    
            elif bc.support_type == "roller":
                # Vertical translation constrained (assuming Z is vertical)
                dof = dof_start + 2
                constrained_dofs.append(dof)
        
        # Apply penalty method for constraints
        penalty_factor = 1e12
        for dof in constrained_dofs:
            K_modified[dof, dof] += penalty_factor
            F_modified[dof] = 0.0
        
        self.global_stiffness = csc_matrix(K_modified)
        self.global_load_vector = F_modified
        
        logger.info(f"Applied {len(constrained_dofs)} boundary conditions")
    
    def solve(self) -> Dict:
        """
        Solve the linear system K*u = F
        """
        logger.info("Solving linear system")
        
        if self.global_stiffness is None or self.global_load_vector is None:
            raise ValueError("System not assembled. Call assemble methods first.")
        
        # Solve for displacements
        self.displacement_vector = spsolve(self.global_stiffness, self.global_load_vector)
        
        # Calculate reaction forces
        self.reaction_forces = self._calculate_reaction_forces()
        
        # Calculate element forces
        self.element_forces = self._calculate_element_forces()
        
        logger.info("Linear analysis completed successfully")
        
        return {
            "displacements": self._format_displacements(),
            "reactions": self._format_reactions(),
            "element_forces": self._format_element_forces()
        }
    
    def _get_element_stiffness_matrix(self, element) -> np.ndarray:
        """
        Get element stiffness matrix in global coordinates
        """
        # This is a simplified implementation
        # In practice, this would depend on element type and properties
        
        if element.element_type == "beam":
            return self._beam_stiffness_matrix(element)
        elif element.element_type == "truss":
            return self._truss_stiffness_matrix(element)
        else:
            raise ValueError(f"Unsupported element type: {element.element_type}")
    
    def _beam_stiffness_matrix(self, element) -> np.ndarray:
        """
        3D beam element stiffness matrix
        """
        # Get material and section properties
        E = element.material.elastic_modulus
        G = element.material.shear_modulus
        A = element.section.area
        Iy = element.section.moment_of_inertia_y
        Iz = element.section.moment_of_inertia_z
        J = element.section.torsional_constant
        
        # Element length
        L = element.length
        
        # Local stiffness matrix (12x12 for 3D beam)
        k_local = np.zeros((12, 12))
        
        # Axial terms
        k_local[0, 0] = k_local[6, 6] = E * A / L
        k_local[0, 6] = k_local[6, 0] = -E * A / L
        
        # Bending about y-axis
        k_local[2, 2] = k_local[8, 8] = 12 * E * Iz / (L**3)
        k_local[2, 8] = k_local[8, 2] = -12 * E * Iz / (L**3)
        k_local[2, 4] = k_local[4, 2] = 6 * E * Iz / (L**2)
        k_local[8, 10] = k_local[10, 8] = -6 * E * Iz / (L**2)
        k_local[4, 4] = k_local[10, 10] = 4 * E * Iz / L
        k_local[4, 10] = k_local[10, 4] = 2 * E * Iz / L
        
        # Bending about z-axis
        k_local[1, 1] = k_local[7, 7] = 12 * E * Iy / (L**3)
        k_local[1, 7] = k_local[7, 1] = -12 * E * Iy / (L**3)
        k_local[1, 5] = k_local[5, 1] = -6 * E * Iy / (L**2)
        k_local[7, 11] = k_local[11, 7] = 6 * E * Iy / (L**2)
        k_local[5, 5] = k_local[11, 11] = 4 * E * Iy / L
        k_local[5, 11] = k_local[11, 5] = 2 * E * Iy / L
        
        # Torsion
        k_local[3, 3] = k_local[9, 9] = G * J / L
        k_local[3, 9] = k_local[9, 3] = -G * J / L
        
        # Transform to global coordinates
        T = self._get_transformation_matrix(element)
        k_global = T.T @ k_local @ T
        
        return k_global
    
    def _truss_stiffness_matrix(self, element) -> np.ndarray:
        """
        3D truss element stiffness matrix
        """
        E = element.material.elastic_modulus
        A = element.section.area
        L = element.length
        
        # Direction cosines
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        
        dx = end_node.x - start_node.x
        dy = end_node.y - start_node.y
        dz = end_node.z - start_node.z
        
        cx = dx / L
        cy = dy / L
        cz = dz / L
        
        # Local stiffness matrix
        k = E * A / L
        
        # Global stiffness matrix (6x6 for 3D truss)
        k_global = np.zeros((6, 6))
        
        # Fill matrix
        for i in range(3):
            for j in range(3):
                c_i = [cx, cy, cz][i]
                c_j = [cx, cy, cz][j]
                
                k_global[i, j] = k * c_i * c_j
                k_global[i, j+3] = -k * c_i * c_j
                k_global[i+3, j] = -k * c_i * c_j
                k_global[i+3, j+3] = k * c_i * c_j
        
        return k_global
    
    def _get_transformation_matrix(self, element) -> np.ndarray:
        """
        Get transformation matrix from local to global coordinates
        """
        # This is a simplified implementation
        # In practice, this would be more complex for 3D beam elements
        return np.eye(12)  # Identity for now
    
    def _get_element_dof_mapping(self, element) -> List[int]:
        """
        Get global DOF indices for element
        """
        start_node_index = self._get_node_index(element.start_node_id)
        end_node_index = self._get_node_index(element.end_node_id)
        
        start_dofs = list(range(start_node_index * 6, (start_node_index + 1) * 6))
        end_dofs = list(range(end_node_index * 6, (end_node_index + 1) * 6))
        
        return start_dofs + end_dofs
    
    def _get_node_index(self, node_id: str) -> int:
        """
        Get node index from node ID
        """
        for i, node in enumerate(self.model.nodes):
            if node.id == node_id:
                return i
        raise ValueError(f"Node {node_id} not found")
    
    def _convert_element_load_to_nodal(self, load) -> Dict[str, List[float]]:
        """
        Convert distributed element load to equivalent nodal loads
        """
        # Simplified implementation
        # In practice, this would use shape functions
        return {}
    
    def _calculate_reaction_forces(self) -> np.ndarray:
        """
        Calculate reaction forces at supports
        """
        return self.global_stiffness @ self.displacement_vector - self.global_load_vector
    
    def _calculate_element_forces(self) -> Dict:
        """
        Calculate internal forces in elements
        """
        element_forces = {}
        
        for element in self.model.elements:
            # Get element displacements
            dof_map = self._get_element_dof_mapping(element)
            element_displacements = self.displacement_vector[dof_map]
            
            # Calculate element forces
            k_element = self._get_element_stiffness_matrix(element)
            forces = k_element @ element_displacements
            
            element_forces[element.id] = {
                "axial": forces[0],
                "shear_y": forces[1],
                "shear_z": forces[2],
                "torsion": forces[3],
                "moment_y": forces[4],
                "moment_z": forces[5]
            }
        
        return element_forces
    
    def _format_displacements(self) -> Dict:
        """
        Format displacement results
        """
        displacements = {}
        
        for i, node in enumerate(self.model.nodes):
            dof_start = i * 6
            displacements[node.id] = {
                "ux": self.displacement_vector[dof_start],
                "uy": self.displacement_vector[dof_start + 1],
                "uz": self.displacement_vector[dof_start + 2],
                "rx": self.displacement_vector[dof_start + 3],
                "ry": self.displacement_vector[dof_start + 4],
                "rz": self.displacement_vector[dof_start + 5]
            }
        
        return displacements
    
    def _format_reactions(self) -> Dict:
        """
        Format reaction force results
        """
        reactions = {}
        
        for i, node in enumerate(self.model.nodes):
            dof_start = i * 6
            reactions[node.id] = {
                "fx": self.reaction_forces[dof_start],
                "fy": self.reaction_forces[dof_start + 1],
                "fz": self.reaction_forces[dof_start + 2],
                "mx": self.reaction_forces[dof_start + 3],
                "my": self.reaction_forces[dof_start + 4],
                "mz": self.reaction_forces[dof_start + 5]
            }
        
        return reactions
    
    def _format_element_forces(self) -> Dict:
        """
        Format element force results
        """
        return self.element_forces