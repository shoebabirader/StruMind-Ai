"""
Linear static analysis solver
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
import uuid
import time

from db.models.structural import Node, Element, Load, LoadCase, BoundaryCondition
from db.models.analysis import AnalysisCase, AnalysisResult
from core.exceptions import ComputationError, AnalysisError
from .matrix import StiffnessMatrixAssembler, DOFManager


class LoadVector:
    """Load vector assembler"""
    
    def __init__(self, dof_manager: DOFManager):
        self.dof_manager = dof_manager
    
    def assemble_load_vector(self, loads: List[Load], nodes: List[Node],
                           elements: List[Element]) -> np.ndarray:
        """Assemble global load vector"""
        total_dofs = self.dof_manager.total_dofs
        F = np.zeros(total_dofs)
        
        for load in loads:
            if load.node_id:
                # Nodal load
                self._apply_nodal_load(F, load, nodes)
            elif load.element_id:
                # Element load
                self._apply_element_load(F, load, elements, nodes)
        
        return F
    
    def _apply_nodal_load(self, F: np.ndarray, load: Load, nodes: List[Node]):
        """Apply nodal load to load vector"""
        node = next((n for n in nodes if n.id == load.node_id), None)
        if not node:
            return
        
        node_dofs = self.dof_manager.get_node_dofs(load.node_id)
        if not node_dofs:
            return
        
        # Map load direction to DOF index
        direction_map = {
            'x': 0, 'y': 1, 'z': 2,
            'xx': 3, 'yy': 4, 'zz': 5
        }
        
        dof_index = direction_map.get(load.direction.value)
        if dof_index is not None and dof_index < len(node_dofs):
            global_dof = node_dofs[dof_index]
            F[global_dof] += load.magnitude
    
    def _apply_element_load(self, F: np.ndarray, load: Load, 
                          elements: List[Element], nodes: List[Node]):
        """Apply element load to load vector (convert to equivalent nodal loads)"""
        element = next((e for e in elements if e.id == load.element_id), None)
        if not element or not element.end_node_id:
            return
        
        start_node = next((n for n in nodes if n.id == element.start_node_id), None)
        end_node = next((n for n in nodes if n.id == element.end_node_id), None)
        
        if not start_node or not end_node:
            return
        
        # Calculate element length
        from core.modeling.geometry import Point3D, GeometryEngine
        start_point = Point3D(start_node.x, start_node.y, start_node.z)
        end_point = Point3D(end_node.x, end_node.y, end_node.z)
        L = GeometryEngine.calculate_element_length(start_point, end_point)
        
        if load.load_type.value == 'distributed':
            self._apply_distributed_load(F, load, start_node, end_node, L)
        elif load.load_type.value == 'point':
            self._apply_element_point_load(F, load, start_node, end_node, L)
    
    def _apply_distributed_load(self, F: np.ndarray, load: Load,
                              start_node: Node, end_node: Node, length: float):
        """Apply distributed load as equivalent nodal loads"""
        w1 = load.magnitude  # Load at start
        w2 = load.magnitude_2 if load.magnitude_2 is not None else w1  # Load at end
        
        # For uniform load: each node gets half the total load
        # For linearly varying load: use appropriate distribution
        if w1 == w2:  # Uniform load
            start_load = w1 * length / 2
            end_load = w1 * length / 2
        else:  # Linearly varying load
            start_load = (2 * w1 + w2) * length / 6
            end_load = (w1 + 2 * w2) * length / 6
        
        # Apply loads to nodes
        direction_map = {'x': 0, 'y': 1, 'z': 2}
        dof_index = direction_map.get(load.direction.value)
        
        if dof_index is not None:
            start_dofs = self.dof_manager.get_node_dofs(start_node.id)
            end_dofs = self.dof_manager.get_node_dofs(end_node.id)
            
            if dof_index < len(start_dofs):
                F[start_dofs[dof_index]] += start_load
            if dof_index < len(end_dofs):
                F[end_dofs[dof_index]] += end_load
    
    def _apply_element_point_load(self, F: np.ndarray, load: Load,
                                start_node: Node, end_node: Node, length: float):
        """Apply point load on element as equivalent nodal loads"""
        position = load.position_start or 0.5  # Default to mid-span
        
        # Shape functions for load distribution
        N1 = 1 - position
        N2 = position
        
        total_load = load.magnitude
        start_load = N1 * total_load
        end_load = N2 * total_load
        
        # Apply loads
        direction_map = {'x': 0, 'y': 1, 'z': 2}
        dof_index = direction_map.get(load.direction.value)
        
        if dof_index is not None:
            start_dofs = self.dof_manager.get_node_dofs(start_node.id)
            end_dofs = self.dof_manager.get_node_dofs(end_node.id)
            
            if dof_index < len(start_dofs):
                F[start_dofs[dof_index]] += start_load
            if dof_index < len(end_dofs):
                F[end_dofs[dof_index]] += end_load


class LinearSolver:
    """Linear equation solver"""
    
    def __init__(self):
        self.solver_options = {
            'method': 'direct',  # 'direct' or 'iterative'
            'tolerance': 1e-12,
            'max_iterations': 1000
        }
    
    def solve(self, K: csr_matrix, F: np.ndarray, 
             constrained_dofs: set) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Solve linear system K*u = F"""
        start_time = time.time()
        
        # Partition system into free and constrained DOFs
        total_dofs = K.shape[0]
        free_dofs = [i for i in range(total_dofs) if i not in constrained_dofs]
        
        if not free_dofs:
            raise AnalysisError("No free degrees of freedom")
        
        # Extract free DOF system
        K_ff = K[np.ix_(free_dofs, free_dofs)]
        F_f = F[free_dofs]
        
        # Check for singularity
        if K_ff.shape[0] == 0:
            raise AnalysisError("Stiffness matrix is empty after applying constraints")
        
        # Solve for free DOF displacements
        try:
            if self.solver_options['method'] == 'direct':
                u_f = spsolve(K_ff, F_f)
            else:
                from scipy.sparse.linalg import cg
                u_f, info = cg(K_ff, F_f, 
                              tol=self.solver_options['tolerance'],
                              maxiter=self.solver_options['max_iterations'])
                if info != 0:
                    raise AnalysisError(f"Iterative solver failed with code {info}")
        
        except Exception as e:
            raise AnalysisError(f"Failed to solve linear system: {str(e)}")
        
        # Assemble full displacement vector
        u_full = np.zeros(total_dofs)
        u_full[free_dofs] = u_f
        
        # Calculate reactions at constrained DOFs
        reactions = K @ u_full - F
        
        solve_time = time.time() - start_time
        
        solver_info = {
            'solve_time': solve_time,
            'total_dofs': total_dofs,
            'free_dofs': len(free_dofs),
            'constrained_dofs': len(constrained_dofs),
            'method': self.solver_options['method'],
            'max_displacement': np.max(np.abs(u_f)) if len(u_f) > 0 else 0.0
        }
        
        return u_full, reactions, solver_info


class LinearStaticAnalysis:
    """Linear static analysis manager"""
    
    def __init__(self):
        self.stiffness_assembler = StiffnessMatrixAssembler()
        self.load_assembler = None
        self.solver = LinearSolver()
        self.results = {}
    
    def run_analysis(self, analysis_case: AnalysisCase, nodes: List[Node],
                    elements: List[Element], materials: Dict[uuid.UUID, Any],
                    sections: Dict[uuid.UUID, Any], loads: List[Load],
                    boundary_conditions: List[BoundaryCondition]) -> Dict[str, Any]:
        """Run linear static analysis"""
        try:
            # Step 1: Assemble global stiffness matrix
            K_global, dof_manager = self.stiffness_assembler.assemble_global_stiffness_matrix(
                nodes, elements, materials, sections
            )
            
            # Step 2: Apply boundary conditions
            self._apply_boundary_conditions(boundary_conditions, dof_manager)
            dof_manager.finalize_dof_mapping()
            
            # Step 3: Assemble load vector
            self.load_assembler = LoadVector(dof_manager)
            F_global = self.load_assembler.assemble_load_vector(loads, nodes, elements)
            
            # Step 4: Solve linear system
            displacements, reactions, solver_info = self.solver.solve(
                K_global, F_global, dof_manager.constrained_dofs
            )
            
            # Step 5: Calculate element forces
            element_forces = self._calculate_element_forces(
                elements, nodes, materials, sections, displacements, dof_manager
            )
            
            # Step 6: Prepare results
            results = {
                'displacements': displacements,
                'reactions': reactions,
                'element_forces': element_forces,
                'solver_info': solver_info,
                'dof_manager': dof_manager,
                'stiffness_matrix': K_global,
                'load_vector': F_global
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Linear static analysis failed: {str(e)}")
    
    def _apply_boundary_conditions(self, boundary_conditions: List[BoundaryCondition],
                                 dof_manager: DOFManager):
        """Apply boundary conditions to DOF manager"""
        for bc in boundary_conditions:
            restraints = [
                bc.restraint_x, bc.restraint_y, bc.restraint_z,
                bc.restraint_xx, bc.restraint_yy, bc.restraint_zz
            ]
            dof_manager.apply_boundary_conditions(bc.node_id, restraints)
    
    def _calculate_element_forces(self, elements: List[Element], nodes: List[Node],
                                materials: Dict[uuid.UUID, Any], sections: Dict[uuid.UUID, Any],
                                displacements: np.ndarray, dof_manager: DOFManager) -> Dict[uuid.UUID, Dict]:
        """Calculate element internal forces"""
        element_forces = {}
        
        for element in elements:
            if not element.is_active or not element.end_node_id:
                continue
            
            # Get element matrices
            element_matrix = self.stiffness_assembler.element_matrices.get(element.id)
            if not element_matrix:
                continue
            
            # Get element displacements
            dof_map = element_matrix.dof_map
            u_element = displacements[dof_map]
            
            # Calculate element forces: F = K * u
            k_element = element_matrix.stiffness_matrix
            f_element = k_element @ u_element
            
            # Store forces (local coordinate system)
            element_forces[element.id] = {
                'axial_force': [f_element[0], f_element[6]],  # Start and end
                'shear_y': [f_element[1], f_element[7]],
                'shear_z': [f_element[2], f_element[8]],
                'torsion': [f_element[3], f_element[9]],
                'moment_y': [f_element[4], f_element[10]],
                'moment_z': [f_element[5], f_element[11]],
                'displacements': u_element.tolist()
            }
        
        return element_forces
    
    def get_node_displacements(self, analysis_case_id: uuid.UUID, 
                             node_id: uuid.UUID) -> Optional[Dict[str, float]]:
        """Get displacements for a specific node"""
        results = self.results.get(analysis_case_id)
        if not results:
            return None
        
        dof_manager = results['dof_manager']
        displacements = results['displacements']
        
        node_dofs = dof_manager.get_node_dofs(node_id)
        if not node_dofs:
            return None
        
        return {
            'displacement_x': displacements[node_dofs[0]],
            'displacement_y': displacements[node_dofs[1]],
            'displacement_z': displacements[node_dofs[2]],
            'rotation_x': displacements[node_dofs[3]],
            'rotation_y': displacements[node_dofs[4]],
            'rotation_z': displacements[node_dofs[5]]
        }
    
    def get_node_reactions(self, analysis_case_id: uuid.UUID,
                         node_id: uuid.UUID) -> Optional[Dict[str, float]]:
        """Get reactions for a specific node"""
        results = self.results.get(analysis_case_id)
        if not results:
            return None
        
        dof_manager = results['dof_manager']
        reactions = results['reactions']
        
        node_dofs = dof_manager.get_node_dofs(node_id)
        if not node_dofs:
            return None
        
        return {
            'reaction_x': reactions[node_dofs[0]],
            'reaction_y': reactions[node_dofs[1]],
            'reaction_z': reactions[node_dofs[2]],
            'moment_x': reactions[node_dofs[3]],
            'moment_y': reactions[node_dofs[4]],
            'moment_z': reactions[node_dofs[5]]
        }
    
    def get_element_forces(self, analysis_case_id: uuid.UUID,
                         element_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get forces for a specific element"""
        results = self.results.get(analysis_case_id)
        if not results:
            return None
        
        return results['element_forces'].get(element_id)
    
    def get_max_displacement(self, analysis_case_id: uuid.UUID) -> Optional[float]:
        """Get maximum displacement magnitude"""
        results = self.results.get(analysis_case_id)
        if not results:
            return None
        
        displacements = results['displacements']
        dof_manager = results['dof_manager']
        
        # Consider only translational DOFs
        max_disp = 0.0
        for node_id, node_dofs in dof_manager.node_dof_map.items():
            if len(node_dofs) >= 3:
                disp_magnitude = np.sqrt(
                    displacements[node_dofs[0]]**2 +
                    displacements[node_dofs[1]]**2 +
                    displacements[node_dofs[2]]**2
                )
                max_disp = max(max_disp, disp_magnitude)
        
        return max_disp