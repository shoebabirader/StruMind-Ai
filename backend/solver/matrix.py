"""
Matrix assembly for structural analysis
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy.sparse import csr_matrix, lil_matrix
import uuid

from db.models.structural import Node, Element, Material, Section
from core.modeling.geometry import Point3D, Vector3D, GeometryEngine
from core.exceptions import ComputationError


class ElementMatrices:
    """Container for element matrices"""
    
    def __init__(self, element_id: uuid.UUID, dof_map: List[int]):
        self.element_id = element_id
        self.dof_map = dof_map  # Global DOF mapping
        self.stiffness_matrix = None
        self.mass_matrix = None
        self.geometric_stiffness_matrix = None
    
    def set_stiffness_matrix(self, k_matrix: np.ndarray):
        """Set element stiffness matrix"""
        self.stiffness_matrix = k_matrix
    
    def set_mass_matrix(self, m_matrix: np.ndarray):
        """Set element mass matrix"""
        self.mass_matrix = m_matrix
    
    def set_geometric_stiffness_matrix(self, kg_matrix: np.ndarray):
        """Set element geometric stiffness matrix"""
        self.geometric_stiffness_matrix = kg_matrix


class DOFManager:
    """Degree of freedom manager"""
    
    def __init__(self):
        self.node_dof_map = {}  # node_id -> [dof_indices]
        self.total_dofs = 0
        self.constrained_dofs = set()
        self.free_dofs = []
    
    def assign_node_dofs(self, node_id: uuid.UUID, num_dofs: int = 6) -> List[int]:
        """Assign DOFs to a node (6 DOF: 3 translations + 3 rotations)"""
        dof_indices = list(range(self.total_dofs, self.total_dofs + num_dofs))
        self.node_dof_map[node_id] = dof_indices
        self.total_dofs += num_dofs
        return dof_indices
    
    def get_node_dofs(self, node_id: uuid.UUID) -> List[int]:
        """Get DOF indices for a node"""
        return self.node_dof_map.get(node_id, [])
    
    def apply_boundary_conditions(self, node_id: uuid.UUID, restraints: List[bool]):
        """Apply boundary conditions (True = constrained, False = free)"""
        node_dofs = self.get_node_dofs(node_id)
        for i, is_constrained in enumerate(restraints):
            if i < len(node_dofs) and is_constrained:
                self.constrained_dofs.add(node_dofs[i])
    
    def finalize_dof_mapping(self):
        """Finalize DOF mapping and identify free DOFs"""
        self.free_dofs = [dof for dof in range(self.total_dofs) 
                         if dof not in self.constrained_dofs]
    
    def get_element_dof_map(self, start_node_id: uuid.UUID, 
                           end_node_id: Optional[uuid.UUID] = None) -> List[int]:
        """Get DOF mapping for an element"""
        dof_map = self.get_node_dofs(start_node_id)
        if end_node_id:
            dof_map.extend(self.get_node_dofs(end_node_id))
        return dof_map


class StiffnessMatrixAssembler:
    """Assembler for global stiffness matrix"""
    
    def __init__(self):
        self.dof_manager = DOFManager()
        self.element_matrices = {}
    
    def calculate_beam_stiffness_matrix(self, element: Element, start_node: Node, 
                                      end_node: Node, material: Material, 
                                      section: Section) -> np.ndarray:
        """Calculate stiffness matrix for beam element"""
        # Element properties
        E = material.elastic_modulus
        G = E / (2 * (1 + material.poisson_ratio))
        A = section.area
        Iy = section.moment_inertia_y
        Iz = section.moment_inertia_z
        J = section.moment_inertia_x or (Iy + Iz)  # Approximate if not provided
        
        # Element geometry
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        L = GeometryEngine.calculate_element_length(start_point, end_point)
        
        if L == 0:
            raise ComputationError("Element length cannot be zero")
        
        # Local stiffness matrix (12x12 for 3D beam)
        k_local = np.zeros((12, 12))
        
        # Axial stiffness
        k_axial = E * A / L
        k_local[0, 0] = k_local[6, 6] = k_axial
        k_local[0, 6] = k_local[6, 0] = -k_axial
        
        # Torsional stiffness
        k_torsion = G * J / L
        k_local[3, 3] = k_local[9, 9] = k_torsion
        k_local[3, 9] = k_local[9, 3] = -k_torsion
        
        # Bending stiffness about y-axis (in xz-plane)
        k_bend_y = 12 * E * Iy / (L**3)
        k_local[2, 2] = k_local[8, 8] = k_bend_y
        k_local[2, 8] = k_local[8, 2] = -k_bend_y
        
        k_moment_y = 6 * E * Iy / (L**2)
        k_local[2, 4] = k_local[4, 2] = k_moment_y
        k_local[2, 10] = k_local[10, 2] = k_moment_y
        k_local[8, 4] = k_local[4, 8] = -k_moment_y
        k_local[8, 10] = k_local[10, 8] = -k_moment_y
        
        k_rot_y = 4 * E * Iy / L
        k_local[4, 4] = k_local[10, 10] = k_rot_y
        k_local[4, 10] = k_local[10, 4] = 2 * E * Iy / L
        
        # Bending stiffness about z-axis (in xy-plane)
        k_bend_z = 12 * E * Iz / (L**3)
        k_local[1, 1] = k_local[7, 7] = k_bend_z
        k_local[1, 7] = k_local[7, 1] = -k_bend_z
        
        k_moment_z = 6 * E * Iz / (L**2)
        k_local[1, 5] = k_local[5, 1] = -k_moment_z
        k_local[1, 11] = k_local[11, 1] = -k_moment_z
        k_local[7, 5] = k_local[5, 7] = k_moment_z
        k_local[7, 11] = k_local[11, 7] = k_moment_z
        
        k_rot_z = 4 * E * Iz / L
        k_local[5, 5] = k_local[11, 11] = k_rot_z
        k_local[5, 11] = k_local[11, 5] = 2 * E * Iz / L
        
        # Transform to global coordinates
        coord_system = GeometryEngine.calculate_element_local_axes(
            start_point, end_point, element.orientation_angle
        )
        
        # Transformation matrix
        T = self._get_transformation_matrix(coord_system)
        
        # Global stiffness matrix
        k_global = T.T @ k_local @ T
        
        return k_global
    
    def calculate_truss_stiffness_matrix(self, element: Element, start_node: Node,
                                       end_node: Node, material: Material,
                                       section: Section) -> np.ndarray:
        """Calculate stiffness matrix for truss element (axial only)"""
        E = material.elastic_modulus
        A = section.area
        
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        L = GeometryEngine.calculate_element_length(start_point, end_point)
        
        if L == 0:
            raise ComputationError("Element length cannot be zero")
        
        # Direction cosines
        dx, dy, dz = GeometryEngine.calculate_element_direction_cosines(start_point, end_point)
        
        # Stiffness coefficient
        k = E * A / L
        
        # Local stiffness matrix (6x6 for 3D truss - only translations)
        k_global = np.zeros((6, 6))
        
        # Fill the matrix based on direction cosines
        for i in range(3):
            for j in range(3):
                direction_i = [dx, dy, dz][i]
                direction_j = [dx, dy, dz][j]
                
                k_global[i, j] = k * direction_i * direction_j
                k_global[i, j+3] = -k * direction_i * direction_j
                k_global[i+3, j] = -k * direction_i * direction_j
                k_global[i+3, j+3] = k * direction_i * direction_j
        
        return k_global
    
    def _get_transformation_matrix(self, coord_system) -> np.ndarray:
        """Get transformation matrix from local to global coordinates"""
        # Direction cosines matrix
        R = np.array([
            [coord_system.x_axis.x, coord_system.x_axis.y, coord_system.x_axis.z],
            [coord_system.y_axis.x, coord_system.y_axis.y, coord_system.y_axis.z],
            [coord_system.z_axis.x, coord_system.z_axis.y, coord_system.z_axis.z]
        ])
        
        # 12x12 transformation matrix for beam element
        T = np.zeros((12, 12))
        for i in range(4):
            T[3*i:3*i+3, 3*i:3*i+3] = R
        
        return T
    
    def assemble_global_stiffness_matrix(self, nodes: List[Node], elements: List[Element],
                                       materials: Dict[uuid.UUID, Material],
                                       sections: Dict[uuid.UUID, Section]) -> Tuple[np.ndarray, DOFManager]:
        """Assemble global stiffness matrix"""
        # Initialize DOF manager
        self.dof_manager = DOFManager()
        
        # Assign DOFs to nodes
        for node in nodes:
            self.dof_manager.assign_node_dofs(node.id)
        
        # Initialize global stiffness matrix
        total_dofs = self.dof_manager.total_dofs
        K_global = lil_matrix((total_dofs, total_dofs))
        
        # Process each element
        for element in elements:
            if not element.is_active:
                continue
            
            # Get nodes
            start_node = next(n for n in nodes if n.id == element.start_node_id)
            end_node = next(n for n in nodes if n.id == element.end_node_id) if element.end_node_id else None
            
            if end_node is None:
                continue  # Skip point elements for now
            
            # Get material and section
            material = materials.get(element.material_id)
            section = sections.get(element.section_id)
            
            if not material or not section:
                continue  # Skip elements without material/section
            
            # Calculate element stiffness matrix
            if element.element_type.value in ['beam', 'column']:
                k_element = self.calculate_beam_stiffness_matrix(
                    element, start_node, end_node, material, section
                )
            elif element.element_type.value == 'truss':
                k_element = self.calculate_truss_stiffness_matrix(
                    element, start_node, end_node, material, section
                )
            else:
                continue  # Skip unsupported element types
            
            # Get DOF mapping
            dof_map = self.dof_manager.get_element_dof_map(element.start_node_id, element.end_node_id)
            
            # Store element matrix
            element_matrix = ElementMatrices(element.id, dof_map)
            element_matrix.set_stiffness_matrix(k_element)
            self.element_matrices[element.id] = element_matrix
            
            # Assemble into global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    K_global[global_i, global_j] += k_element[i, j]
        
        return K_global.tocsr(), self.dof_manager


class MassMatrixAssembler:
    """Assembler for global mass matrix"""
    
    def __init__(self):
        self.dof_manager = None
    
    def calculate_beam_mass_matrix(self, element: Element, start_node: Node,
                                 end_node: Node, material: Material,
                                 section: Section) -> np.ndarray:
        """Calculate consistent mass matrix for beam element"""
        rho = material.density
        A = section.area
        
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        L = GeometryEngine.calculate_element_length(start_point, end_point)
        
        # Mass per unit length
        m = rho * A
        
        # Consistent mass matrix (12x12)
        M_local = np.zeros((12, 12))
        
        # Translational mass terms
        # Axial direction
        M_local[0, 0] = M_local[6, 6] = m * L / 3
        M_local[0, 6] = M_local[6, 0] = m * L / 6
        
        # Transverse directions (consistent mass for bending)
        M_local[1, 1] = M_local[7, 7] = 13 * m * L / 35
        M_local[1, 7] = M_local[7, 1] = 9 * m * L / 70
        M_local[2, 2] = M_local[8, 8] = 13 * m * L / 35
        M_local[2, 8] = M_local[8, 2] = 9 * m * L / 70
        
        # Rotational mass terms (simplified)
        I_polar = section.moment_inertia_x or (section.moment_inertia_y + section.moment_inertia_z)
        mr2 = rho * I_polar
        
        M_local[3, 3] = M_local[9, 9] = mr2 * L / 3
        M_local[3, 9] = M_local[9, 3] = mr2 * L / 6
        
        M_local[4, 4] = M_local[10, 10] = m * L**3 / 105
        M_local[5, 5] = M_local[11, 11] = m * L**3 / 105
        
        # Transform to global coordinates
        coord_system = GeometryEngine.calculate_element_local_axes(
            start_point, end_point, element.orientation_angle
        )
        
        T = self._get_transformation_matrix(coord_system)
        M_global = T.T @ M_local @ T
        
        return M_global
    
    def calculate_lumped_mass_matrix(self, element: Element, start_node: Node,
                                   end_node: Node, material: Material,
                                   section: Section) -> np.ndarray:
        """Calculate lumped mass matrix for element"""
        rho = material.density
        A = section.area
        
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        L = GeometryEngine.calculate_element_length(start_point, end_point)
        
        # Total element mass
        total_mass = rho * A * L
        
        # Lumped mass matrix (half mass at each node)
        M_lumped = np.zeros((12, 12))
        node_mass = total_mass / 2
        
        # Translational masses
        for i in [0, 1, 2, 6, 7, 8]:  # Translation DOFs
            M_lumped[i, i] = node_mass
        
        # Rotational inertias (simplified)
        I_polar = section.moment_inertia_x or (section.moment_inertia_y + section.moment_inertia_z)
        node_inertia = rho * I_polar * L / 2
        
        for i in [3, 4, 5, 9, 10, 11]:  # Rotation DOFs
            M_lumped[i, i] = node_inertia
        
        return M_lumped
    
    def _get_transformation_matrix(self, coord_system) -> np.ndarray:
        """Get transformation matrix from local to global coordinates"""
        R = np.array([
            [coord_system.x_axis.x, coord_system.x_axis.y, coord_system.x_axis.z],
            [coord_system.y_axis.x, coord_system.y_axis.y, coord_system.y_axis.z],
            [coord_system.z_axis.x, coord_system.z_axis.y, coord_system.z_axis.z]
        ])
        
        T = np.zeros((12, 12))
        for i in range(4):
            T[3*i:3*i+3, 3*i:3*i+3] = R
        
        return T
    
    def assemble_global_mass_matrix(self, nodes: List[Node], elements: List[Element],
                                  materials: Dict[uuid.UUID, Material],
                                  sections: Dict[uuid.UUID, Section],
                                  dof_manager: DOFManager,
                                  use_consistent_mass: bool = True) -> np.ndarray:
        """Assemble global mass matrix"""
        self.dof_manager = dof_manager
        total_dofs = dof_manager.total_dofs
        M_global = lil_matrix((total_dofs, total_dofs))
        
        for element in elements:
            if not element.is_active:
                continue
            
            start_node = next(n for n in nodes if n.id == element.start_node_id)
            end_node = next(n for n in nodes if n.id == element.end_node_id) if element.end_node_id else None
            
            if end_node is None:
                continue
            
            material = materials.get(element.material_id)
            section = sections.get(element.section_id)
            
            if not material or not section:
                continue
            
            # Calculate element mass matrix
            if use_consistent_mass:
                m_element = self.calculate_beam_mass_matrix(
                    element, start_node, end_node, material, section
                )
            else:
                m_element = self.calculate_lumped_mass_matrix(
                    element, start_node, end_node, material, section
                )
            
            # Get DOF mapping
            dof_map = dof_manager.get_element_dof_map(element.start_node_id, element.end_node_id)
            
            # Assemble into global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    M_global[global_i, global_j] += m_element[i, j]
        
        return M_global.tocsr()