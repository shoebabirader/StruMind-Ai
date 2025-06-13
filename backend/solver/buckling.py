"""
Buckling analysis solver
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy.sparse.linalg import eigsh
import uuid

from db.models.structural import Node, Element, Load, BoundaryCondition
from db.models.analysis import AnalysisCase
from core.exceptions import AnalysisError, ComputationError
from .matrix import StiffnessMatrixAssembler, DOFManager
from .linear import LoadVector


class BucklingAnalysis:
    """Linear buckling analysis solver"""
    
    def __init__(self):
        self.stiffness_assembler = StiffnessMatrixAssembler()
        self.results = {}
    
    def run_analysis(self, analysis_case: AnalysisCase, nodes: List[Node],
                    elements: List[Element], materials: Dict[uuid.UUID, Any],
                    sections: Dict[uuid.UUID, Any], loads: List[Load],
                    boundary_conditions: List[BoundaryCondition]) -> Dict[str, Any]:
        """Run linear buckling analysis"""
        try:
            # Step 1: Assemble elastic stiffness matrix
            K_elastic, dof_manager = self.stiffness_assembler.assemble_global_stiffness_matrix(
                nodes, elements, materials, sections
            )
            
            # Step 2: Apply boundary conditions
            self._apply_boundary_conditions(boundary_conditions, dof_manager)
            dof_manager.finalize_dof_mapping()
            
            # Step 3: Perform linear static analysis to get stress state
            stress_state = self._calculate_stress_state(
                K_elastic, loads, nodes, elements, dof_manager
            )
            
            # Step 4: Assemble geometric stiffness matrix
            K_geometric = self._assemble_geometric_stiffness_matrix(
                stress_state, elements, nodes, materials, sections, dof_manager
            )
            
            # Step 5: Solve eigenvalue problem
            buckling_factors, buckling_modes = self._solve_buckling_eigenvalue_problem(
                K_elastic, K_geometric, dof_manager, analysis_case.parameters
            )
            
            # Step 6: Calculate buckling loads
            buckling_loads = self._calculate_buckling_loads(buckling_factors, loads)
            
            # Step 7: Prepare results
            results = {
                'buckling_factors': buckling_factors,
                'buckling_modes': buckling_modes,
                'buckling_loads': buckling_loads,
                'stress_state': stress_state,
                'dof_manager': dof_manager,
                'analysis_type': 'buckling'
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Buckling analysis failed: {str(e)}")
    
    def _apply_boundary_conditions(self, boundary_conditions: List[BoundaryCondition],
                                 dof_manager: DOFManager):
        """Apply boundary conditions"""
        for bc in boundary_conditions:
            restraints = [
                bc.restraint_x, bc.restraint_y, bc.restraint_z,
                bc.restraint_xx, bc.restraint_yy, bc.restraint_zz
            ]
            dof_manager.apply_boundary_conditions(bc.node_id, restraints)
    
    def _calculate_stress_state(self, K_elastic, loads: List[Load], nodes: List[Node],
                              elements: List[Element], dof_manager: DOFManager) -> Dict[str, Any]:
        """Calculate stress state from applied loads"""
        # Assemble load vector
        load_assembler = LoadVector(dof_manager)
        F_applied = load_assembler.assemble_load_vector(loads, nodes, elements)
        
        # Solve linear system
        free_dofs = dof_manager.free_dofs
        K_ff = K_elastic[np.ix_(free_dofs, free_dofs)]
        F_f = F_applied[free_dofs]
        
        from scipy.sparse.linalg import spsolve
        u_f = spsolve(K_ff, F_f)
        
        # Assemble full displacement vector
        u_full = np.zeros(len(F_applied))
        u_full[free_dofs] = u_f
        
        # Calculate element forces
        element_forces = {}
        for element in elements:
            if not element.is_active or not element.end_node_id:
                continue
            
            element_matrix = self.stiffness_assembler.element_matrices.get(element.id)
            if not element_matrix:
                continue
            
            dof_map = element_matrix.dof_map
            u_element = u_full[dof_map]
            k_element = element_matrix.stiffness_matrix
            f_element = k_element @ u_element
            
            # Store axial force (primary contributor to buckling)
            element_forces[element.id] = {
                'axial_force': f_element[0],  # Local x-direction force
                'displacements': u_element
            }
        
        return {
            'displacements': u_full,
            'element_forces': element_forces
        }
    
    def _assemble_geometric_stiffness_matrix(self, stress_state: Dict[str, Any],
                                           elements: List[Element], nodes: List[Node],
                                           materials: Dict[uuid.UUID, Any],
                                           sections: Dict[uuid.UUID, Any],
                                           dof_manager: DOFManager) -> np.ndarray:
        """Assemble geometric stiffness matrix based on stress state"""
        total_dofs = dof_manager.total_dofs
        K_geometric = np.zeros((total_dofs, total_dofs))
        
        element_forces = stress_state['element_forces']
        
        for element in elements:
            if not element.is_active or not element.end_node_id:
                continue
            
            element_force_data = element_forces.get(element.id)
            if not element_force_data:
                continue
            
            # Get axial force
            axial_force = element_force_data['axial_force']
            
            # Get element geometry
            start_node = next(n for n in nodes if n.id == element.start_node_id)
            end_node = next(n for n in nodes if n.id == element.end_node_id)
            
            from core.modeling.geometry import Point3D, GeometryEngine
            start_point = Point3D(start_node.x, start_node.y, start_node.z)
            end_point = Point3D(end_node.x, end_node.y, end_node.z)
            length = GeometryEngine.calculate_element_length(start_point, end_point)
            
            # Calculate element geometric stiffness matrix
            kg_element = self._calculate_element_geometric_stiffness(
                axial_force, length, element, start_point, end_point
            )
            
            # Get DOF mapping
            dof_map = dof_manager.get_element_dof_map(element.start_node_id, element.end_node_id)
            
            # Assemble into global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    if i < kg_element.shape[0] and j < kg_element.shape[1]:
                        K_geometric[global_i, global_j] += kg_element[i, j]
        
        return K_geometric
    
    def _calculate_element_geometric_stiffness(self, axial_force: float, length: float,
                                             element, start_point, end_point) -> np.ndarray:
        """Calculate element geometric stiffness matrix"""
        # Geometric stiffness matrix for beam element under axial force
        kg = np.zeros((12, 12))
        
        if length <= 0:
            return kg
        
        # Geometric stiffness coefficients
        if axial_force != 0:
            # For compression (negative axial force), geometric stiffness reduces overall stiffness
            # For tension (positive axial force), it increases stiffness
            
            # Simplified geometric stiffness matrix
            # In practice, this would be more detailed based on beam theory
            
            # Transverse bending terms (major contributor to buckling)
            kg_coeff = abs(axial_force) / length
            
            # Y-direction bending
            kg[1, 1] = kg[7, 7] = 6.0/5.0 * kg_coeff
            kg[1, 7] = kg[7, 1] = -6.0/5.0 * kg_coeff
            kg[1, 5] = kg[5, 1] = kg[1, 11] = kg[11, 1] = kg_coeff * length / 10.0
            kg[7, 5] = kg[5, 7] = kg[7, 11] = kg[11, 7] = -kg_coeff * length / 10.0
            kg[5, 5] = kg[11, 11] = 2.0 * kg_coeff * length**2 / 15.0
            kg[5, 11] = kg[11, 5] = -kg_coeff * length**2 / 30.0
            
            # Z-direction bending
            kg[2, 2] = kg[8, 8] = 6.0/5.0 * kg_coeff
            kg[2, 8] = kg[8, 2] = -6.0/5.0 * kg_coeff
            kg[2, 4] = kg[4, 2] = kg[2, 10] = kg[10, 2] = -kg_coeff * length / 10.0
            kg[8, 4] = kg[4, 8] = kg[8, 10] = kg[10, 8] = kg_coeff * length / 10.0
            kg[4, 4] = kg[10, 10] = 2.0 * kg_coeff * length**2 / 15.0
            kg[4, 10] = kg[10, 4] = -kg_coeff * length**2 / 30.0
        
        # Transform to global coordinates if needed
        coord_system = GeometryEngine.calculate_element_local_axes(
            start_point, end_point, element.orientation_angle
        )
        
        T = self._get_transformation_matrix(coord_system)
        kg_global = T.T @ kg @ T
        
        return kg_global
    
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
    
    def _solve_buckling_eigenvalue_problem(self, K_elastic, K_geometric, dof_manager: DOFManager,
                                         parameters: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """Solve buckling eigenvalue problem"""
        # Extract free DOF matrices
        free_dofs = dof_manager.free_dofs
        K_e_ff = K_elastic[np.ix_(free_dofs, free_dofs)]
        K_g_ff = K_geometric[np.ix_(free_dofs, free_dofs)]
        
        # Number of modes to extract
        num_modes = parameters.get('num_modes', 5)
        num_modes = min(num_modes, len(free_dofs) - 1)
        
        if num_modes <= 0:
            raise ComputationError("No modes to extract")
        
        try:
            # Solve generalized eigenvalue problem: (K_e + lambda * K_g) * phi = 0
            # This becomes: K_e * phi = -lambda * K_g * phi
            # Or: K_g * phi = -(1/lambda) * K_e * phi
            
            eigenvalues, eigenvectors = eigsh(
                -K_g_ff, k=num_modes, M=K_e_ff, sigma=0.0, which='LM'
            )
            
            # Buckling factors are the negative reciprocals of eigenvalues
            buckling_factors = -1.0 / eigenvalues
            
            # Sort by buckling factor (lowest first)
            idx = np.argsort(buckling_factors)
            buckling_factors = buckling_factors[idx]
            eigenvectors = eigenvectors[:, idx]
            
            # Filter out negative buckling factors (unstable modes)
            positive_modes = buckling_factors > 0
            buckling_factors = buckling_factors[positive_modes]
            eigenvectors = eigenvectors[:, positive_modes]
            
            return buckling_factors, eigenvectors
            
        except Exception as e:
            raise ComputationError(f"Buckling eigenvalue solution failed: {str(e)}")
    
    def _calculate_buckling_loads(self, buckling_factors: np.ndarray, 
                                loads: List[Load]) -> List[Dict[str, Any]]:
        """Calculate critical buckling loads"""
        buckling_loads = []
        
        for i, factor in enumerate(buckling_factors):
            buckling_load_case = []
            
            for load in loads:
                critical_magnitude = load.magnitude * factor
                
                buckling_load_case.append({
                    'load_id': load.id,
                    'original_magnitude': load.magnitude,
                    'critical_magnitude': critical_magnitude,
                    'buckling_factor': factor,
                    'load_type': load.load_type.value,
                    'direction': load.direction.value
                })
            
            buckling_loads.append({
                'mode_number': i + 1,
                'buckling_factor': factor,
                'loads': buckling_load_case
            })
        
        return buckling_loads
    
    def get_buckling_mode_shape(self, analysis_case_id: uuid.UUID, mode_number: int,
                              node_id: uuid.UUID) -> Optional[Dict[str, float]]:
        """Get buckling mode shape for specific node and mode"""
        results = self.results.get(analysis_case_id)
        if not results or mode_number < 1:
            return None
        
        buckling_modes = results['buckling_modes']
        if mode_number > buckling_modes.shape[1]:
            return None
        
        mode_shape = buckling_modes[:, mode_number - 1]
        dof_manager = results['dof_manager']
        
        node_dofs = dof_manager.get_node_dofs(node_id)
        if not node_dofs:
            return None
        
        free_dofs = dof_manager.free_dofs
        
        # Extract mode shape values for this node
        mode_displacements = {}
        dof_names = ['displacement_x', 'displacement_y', 'displacement_z',
                    'rotation_x', 'rotation_y', 'rotation_z']
        
        for i, dof_name in enumerate(dof_names):
            if i < len(node_dofs):
                global_dof = node_dofs[i]
                if global_dof in free_dofs:
                    free_dof_index = free_dofs.index(global_dof)
                    mode_displacements[dof_name] = mode_shape[free_dof_index]
                else:
                    mode_displacements[dof_name] = 0.0
        
        return mode_displacements
    
    def get_critical_buckling_factor(self, analysis_case_id: uuid.UUID) -> Optional[float]:
        """Get the lowest (critical) buckling factor"""
        results = self.results.get(analysis_case_id)
        if not results:
            return None
        
        buckling_factors = results['buckling_factors']
        if len(buckling_factors) > 0:
            return buckling_factors[0]  # Already sorted, first is lowest
        
        return None