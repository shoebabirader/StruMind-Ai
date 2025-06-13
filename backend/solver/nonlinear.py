"""
Nonlinear static analysis solver
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import uuid

from db.models.structural import Node, Element, Load, BoundaryCondition
from db.models.analysis import AnalysisCase
from core.exceptions import AnalysisError, ComputationError
from .linear import LinearStaticAnalysis, LoadVector
from .matrix import StiffnessMatrixAssembler, DOFManager


class NonlinearSolver:
    """Nonlinear equation solver using Newton-Raphson method"""
    
    def __init__(self):
        self.max_iterations = 50
        self.convergence_tolerance = 1e-6
        self.load_step_tolerance = 1e-8
    
    def solve_newton_raphson(self, K_initial, F_total, constrained_dofs,
                           get_tangent_stiffness_func, get_internal_force_func,
                           load_steps: List[float]) -> Tuple[np.ndarray, List[Dict]]:
        """Solve nonlinear system using Newton-Raphson with load stepping"""
        total_dofs = K_initial.shape[0]
        free_dofs = [i for i in range(total_dofs) if i not in constrained_dofs]
        
        # Initialize solution
        u_total = np.zeros(total_dofs)
        convergence_history = []
        
        for step_idx, load_factor in enumerate(load_steps):
            F_step = F_total * load_factor
            u_step = np.zeros(total_dofs)
            
            # Newton-Raphson iterations for this load step
            for iteration in range(self.max_iterations):
                # Get current tangent stiffness matrix
                K_tangent = get_tangent_stiffness_func(u_total + u_step)
                
                # Get internal forces
                F_internal = get_internal_force_func(u_total + u_step)
                
                # Calculate residual
                residual = F_step - F_internal
                
                # Extract free DOF system
                K_ff = K_tangent[np.ix_(free_dofs, free_dofs)]
                R_f = residual[free_dofs]
                
                # Check convergence
                residual_norm = np.linalg.norm(R_f)
                if residual_norm < self.convergence_tolerance:
                    convergence_history.append({
                        'load_step': step_idx + 1,
                        'iteration': iteration + 1,
                        'residual_norm': residual_norm,
                        'converged': True
                    })
                    break
                
                # Solve for displacement increment
                try:
                    from scipy.sparse.linalg import spsolve
                    du_f = spsolve(K_ff, R_f)
                except:
                    raise ComputationError(f"Failed to solve tangent system at load step {step_idx + 1}")
                
                # Update displacement
                du_full = np.zeros(total_dofs)
                du_full[free_dofs] = du_f
                u_step += du_full
                
                convergence_history.append({
                    'load_step': step_idx + 1,
                    'iteration': iteration + 1,
                    'residual_norm': residual_norm,
                    'converged': False
                })
            
            else:
                raise ComputationError(f"Newton-Raphson failed to converge at load step {step_idx + 1}")
            
            # Update total displacement
            u_total += u_step
        
        return u_total, convergence_history


class NonlinearStaticAnalysis:
    """Nonlinear static analysis manager"""
    
    def __init__(self):
        self.stiffness_assembler = StiffnessMatrixAssembler()
        self.linear_analysis = LinearStaticAnalysis()
        self.nonlinear_solver = NonlinearSolver()
        self.results = {}
    
    def run_analysis(self, analysis_case: AnalysisCase, nodes: List[Node],
                    elements: List[Element], materials: Dict[uuid.UUID, Any],
                    sections: Dict[uuid.UUID, Any], loads: List[Load],
                    boundary_conditions: List[BoundaryCondition]) -> Dict[str, Any]:
        """Run nonlinear static analysis"""
        try:
            # Step 1: Get initial linear stiffness matrix
            K_initial, dof_manager = self.stiffness_assembler.assemble_global_stiffness_matrix(
                nodes, elements, materials, sections
            )
            
            # Step 2: Apply boundary conditions
            self._apply_boundary_conditions(boundary_conditions, dof_manager)
            dof_manager.finalize_dof_mapping()
            
            # Step 3: Assemble load vector
            load_assembler = LoadVector(dof_manager)
            F_total = load_assembler.assemble_load_vector(loads, nodes, elements)
            
            # Step 4: Define load steps
            load_steps = self._generate_load_steps(analysis_case.parameters)
            
            # Step 5: Define nonlinear functions
            def get_tangent_stiffness(u_current):
                return self._calculate_tangent_stiffness(
                    u_current, elements, nodes, materials, sections, dof_manager
                )
            
            def get_internal_force(u_current):
                return self._calculate_internal_forces(
                    u_current, elements, nodes, materials, sections, dof_manager
                )
            
            # Step 6: Solve nonlinear system
            displacements, convergence_history = self.nonlinear_solver.solve_newton_raphson(
                K_initial, F_total, dof_manager.constrained_dofs,
                get_tangent_stiffness, get_internal_force, load_steps
            )
            
            # Step 7: Calculate final element forces
            element_forces = self._calculate_final_element_forces(
                displacements, elements, nodes, materials, sections, dof_manager
            )
            
            # Step 8: Prepare results
            results = {
                'displacements': displacements,
                'element_forces': element_forces,
                'convergence_history': convergence_history,
                'load_steps': load_steps,
                'dof_manager': dof_manager,
                'analysis_type': 'nonlinear_static'
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Nonlinear static analysis failed: {str(e)}")
    
    def _apply_boundary_conditions(self, boundary_conditions: List[BoundaryCondition],
                                 dof_manager: DOFManager):
        """Apply boundary conditions"""
        for bc in boundary_conditions:
            restraints = [
                bc.restraint_x, bc.restraint_y, bc.restraint_z,
                bc.restraint_xx, bc.restraint_yy, bc.restraint_zz
            ]
            dof_manager.apply_boundary_conditions(bc.node_id, restraints)
    
    def _generate_load_steps(self, parameters: Dict[str, Any]) -> List[float]:
        """Generate load stepping sequence"""
        num_steps = parameters.get('load_steps', 10)
        step_type = parameters.get('step_type', 'linear')
        
        if step_type == 'linear':
            return np.linspace(0.1, 1.0, num_steps).tolist()
        elif step_type == 'exponential':
            return (1.0 - np.exp(-np.linspace(0, 3, num_steps))).tolist()
        else:
            return np.linspace(0.1, 1.0, num_steps).tolist()
    
    def _calculate_tangent_stiffness(self, u_current: np.ndarray, elements: List[Element],
                                   nodes: List[Node], materials: Dict[uuid.UUID, Any],
                                   sections: Dict[uuid.UUID, Any], 
                                   dof_manager: DOFManager) -> np.ndarray:
        """Calculate tangent stiffness matrix for current displacement state"""
        # For this implementation, we'll use the initial stiffness matrix
        # In a full nonlinear analysis, this would include geometric stiffness
        # and material nonlinearity effects
        
        K_tangent, _ = self.stiffness_assembler.assemble_global_stiffness_matrix(
            nodes, elements, materials, sections
        )
        
        # Add geometric stiffness effects (simplified)
        K_geometric = self._calculate_geometric_stiffness(
            u_current, elements, nodes, materials, sections, dof_manager
        )
        
        return K_tangent + K_geometric
    
    def _calculate_geometric_stiffness(self, u_current: np.ndarray, elements: List[Element],
                                     nodes: List[Node], materials: Dict[uuid.UUID, Any],
                                     sections: Dict[uuid.UUID, Any],
                                     dof_manager: DOFManager) -> np.ndarray:
        """Calculate geometric stiffness matrix (P-Delta effects)"""
        total_dofs = len(u_current)
        K_geometric = np.zeros((total_dofs, total_dofs))
        
        # Simplified geometric stiffness calculation
        # In practice, this would be more sophisticated
        for element in elements:
            if not element.is_active or not element.end_node_id:
                continue
            
            # Get element DOFs
            dof_map = dof_manager.get_element_dof_map(element.start_node_id, element.end_node_id)
            if len(dof_map) < 12:
                continue
            
            # Get element displacements
            u_element = u_current[dof_map]
            
            # Calculate axial force (simplified)
            axial_displacement = u_element[6] - u_element[0]  # End - Start in local x
            material = materials.get(element.material_id)
            section = sections.get(element.section_id)
            
            if material and section:
                E = material.elastic_modulus
                A = section.area
                
                # Element length
                start_node = next(n for n in nodes if n.id == element.start_node_id)
                end_node = next(n for n in nodes if n.id == element.end_node_id)
                
                from core.modeling.geometry import Point3D, GeometryEngine
                start_point = Point3D(start_node.x, start_node.y, start_node.z)
                end_point = Point3D(end_node.x, end_node.y, end_node.z)
                L = GeometryEngine.calculate_element_length(start_point, end_point)
                
                # Axial force
                N = E * A * axial_displacement / L
                
                # Geometric stiffness matrix (simplified)
                kg_element = self._get_element_geometric_stiffness(N, L)
                
                # Assemble into global matrix
                for i, global_i in enumerate(dof_map):
                    for j, global_j in enumerate(dof_map):
                        if i < kg_element.shape[0] and j < kg_element.shape[1]:
                            K_geometric[global_i, global_j] += kg_element[i, j]
        
        return K_geometric
    
    def _get_element_geometric_stiffness(self, axial_force: float, length: float) -> np.ndarray:
        """Get element geometric stiffness matrix"""
        # Simplified geometric stiffness for beam element
        kg = np.zeros((12, 12))
        
        if length > 0:
            # Geometric stiffness terms (simplified)
            kg_coeff = axial_force / length
            
            # Transverse terms
            kg[1, 1] = kg[7, 7] = kg_coeff
            kg[1, 7] = kg[7, 1] = -kg_coeff
            kg[2, 2] = kg[8, 8] = kg_coeff
            kg[2, 8] = kg[8, 2] = -kg_coeff
        
        return kg
    
    def _calculate_internal_forces(self, u_current: np.ndarray, elements: List[Element],
                                 nodes: List[Node], materials: Dict[uuid.UUID, Any],
                                 sections: Dict[uuid.UUID, Any],
                                 dof_manager: DOFManager) -> np.ndarray:
        """Calculate internal force vector for current displacement state"""
        total_dofs = len(u_current)
        F_internal = np.zeros(total_dofs)
        
        for element in elements:
            if not element.is_active or not element.end_node_id:
                continue
            
            # Get element matrices
            element_matrix = self.stiffness_assembler.element_matrices.get(element.id)
            if not element_matrix:
                continue
            
            # Get element displacements
            dof_map = element_matrix.dof_map
            u_element = u_current[dof_map]
            
            # Calculate element internal forces
            k_element = element_matrix.stiffness_matrix
            f_element = k_element @ u_element
            
            # Assemble into global vector
            for i, global_dof in enumerate(dof_map):
                F_internal[global_dof] += f_element[i]
        
        return F_internal
    
    def _calculate_final_element_forces(self, displacements: np.ndarray, elements: List[Element],
                                      nodes: List[Node], materials: Dict[uuid.UUID, Any],
                                      sections: Dict[uuid.UUID, Any],
                                      dof_manager: DOFManager) -> Dict[uuid.UUID, Dict]:
        """Calculate final element forces"""
        # Use the same method as linear analysis for now
        return self.linear_analysis._calculate_element_forces(
            elements, nodes, materials, sections, displacements, dof_manager
        )