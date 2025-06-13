"""
Nonlinear solver implementation for structural analysis
"""

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import spsolve
from typing import Dict, List, Tuple, Optional, Callable
import logging

from ..linear.linear_solver import LinearSolver
from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase
from ...core.modeling.boundary_conditions import BoundaryCondition

logger = logging.getLogger(__name__)


class NonlinearSolver:
    """
    Base class for nonlinear structural analysis solvers
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.linear_solver = LinearSolver(model)
        self.max_iterations = 50
        self.convergence_tolerance = 1e-6
        self.load_steps = 10
        self.current_displacement = None
        self.current_load_factor = 0.0
        self.iteration_history = []
        
    def solve_nonlinear(self, 
                       load_case: LoadCase,
                       boundary_conditions: List[BoundaryCondition],
                       analysis_type: str = "newton_raphson") -> Dict:
        """
        Solve nonlinear analysis using specified method
        """
        logger.info(f"Starting nonlinear analysis: {analysis_type}")
        
        if analysis_type == "newton_raphson":
            return self._newton_raphson_solve(load_case, boundary_conditions)
        elif analysis_type == "arc_length":
            return self._arc_length_solve(load_case, boundary_conditions)
        elif analysis_type == "load_control":
            return self._load_control_solve(load_case, boundary_conditions)
        else:
            raise ValueError(f"Unsupported nonlinear analysis type: {analysis_type}")
    
    def _newton_raphson_solve(self, 
                             load_case: LoadCase,
                             boundary_conditions: List[BoundaryCondition]) -> Dict:
        """
        Newton-Raphson iterative solver
        """
        logger.info("Newton-Raphson nonlinear analysis")
        
        # Initialize
        total_dofs = len(self.model.nodes) * 6
        displacement = np.zeros(total_dofs)
        
        # Assemble reference load vector
        self.linear_solver.assemble_global_load_vector(load_case)
        reference_load = self.linear_solver.global_load_vector.copy()
        
        results = {
            "load_steps": [],
            "convergence_history": [],
            "final_displacements": {},
            "final_forces": {}
        }
        
        # Load stepping
        for step in range(1, self.load_steps + 1):
            load_factor = step / self.load_steps
            target_load = load_factor * reference_load
            
            logger.info(f"Load step {step}/{self.load_steps} (factor: {load_factor:.3f})")
            
            # Newton-Raphson iterations
            converged = False
            step_displacement = displacement.copy()
            
            for iteration in range(self.max_iterations):
                # Assemble tangent stiffness matrix
                K_tangent = self._assemble_tangent_stiffness(step_displacement)
                
                # Apply boundary conditions
                K_tangent, target_load_bc = self._apply_boundary_conditions_nonlinear(
                    K_tangent, target_load, boundary_conditions
                )
                
                # Calculate residual
                internal_forces = self._calculate_internal_forces(step_displacement)
                residual = target_load_bc - internal_forces
                
                # Check convergence
                residual_norm = np.linalg.norm(residual)
                displacement_norm = np.linalg.norm(step_displacement)
                
                if displacement_norm > 0:
                    relative_error = residual_norm / displacement_norm
                else:
                    relative_error = residual_norm
                
                logger.debug(f"  Iteration {iteration + 1}: Residual = {residual_norm:.2e}, "
                           f"Relative error = {relative_error:.2e}")
                
                if relative_error < self.convergence_tolerance:
                    converged = True
                    logger.info(f"  Converged in {iteration + 1} iterations")
                    break
                
                # Solve for displacement increment
                try:
                    delta_u = spsolve(K_tangent, residual)
                    step_displacement += delta_u
                except Exception as e:
                    logger.error(f"Failed to solve system: {e}")
                    break
            
            if not converged:
                logger.warning(f"Load step {step} did not converge")
            
            # Store step results
            displacement = step_displacement.copy()
            self.current_displacement = displacement
            self.current_load_factor = load_factor
            
            step_results = {
                "load_factor": load_factor,
                "converged": converged,
                "iterations": iteration + 1,
                "displacement_norm": np.linalg.norm(displacement),
                "max_displacement": np.max(np.abs(displacement))
            }
            
            results["load_steps"].append(step_results)
        
        # Format final results
        results["final_displacements"] = self._format_displacements(displacement)
        results["final_forces"] = self._calculate_element_forces_nonlinear(displacement)
        
        return results
    
    def _arc_length_solve(self, 
                         load_case: LoadCase,
                         boundary_conditions: List[BoundaryCondition]) -> Dict:
        """
        Arc-length method for handling snap-through and snap-back
        """
        logger.info("Arc-length nonlinear analysis")
        
        # This is a simplified implementation
        # Full arc-length method is quite complex
        
        total_dofs = len(self.model.nodes) * 6
        displacement = np.zeros(total_dofs)
        load_factor = 0.0
        
        # Arc-length parameter
        arc_length = 1.0
        
        results = {
            "load_steps": [],
            "convergence_history": [],
            "final_displacements": {},
            "final_forces": {}
        }
        
        # Reference load vector
        self.linear_solver.assemble_global_load_vector(load_case)
        reference_load = self.linear_solver.global_load_vector.copy()
        
        for step in range(self.load_steps):
            logger.info(f"Arc-length step {step + 1}/{self.load_steps}")
            
            # Predictor step
            K_tangent = self._assemble_tangent_stiffness(displacement)
            K_tangent, _ = self._apply_boundary_conditions_nonlinear(
                K_tangent, reference_load, boundary_conditions
            )
            
            # Solve for displacement and load factor increments
            delta_u_pred = spsolve(K_tangent, reference_load)
            delta_lambda_pred = arc_length / np.linalg.norm(delta_u_pred)
            delta_u_pred *= delta_lambda_pred
            
            # Update predictions
            displacement_pred = displacement + delta_u_pred
            load_factor_pred = load_factor + delta_lambda_pred
            
            # Corrector iterations
            converged = False
            current_displacement = displacement_pred.copy()
            current_load_factor = load_factor_pred
            
            for iteration in range(self.max_iterations):
                # Calculate residual
                K_tangent = self._assemble_tangent_stiffness(current_displacement)
                internal_forces = self._calculate_internal_forces(current_displacement)
                residual = current_load_factor * reference_load - internal_forces
                
                # Arc-length constraint
                constraint = (np.dot(current_displacement - displacement, delta_u_pred) + 
                             (current_load_factor - load_factor) * delta_lambda_pred * 
                             np.dot(reference_load, delta_u_pred) - arc_length**2)
                
                # Check convergence
                if np.linalg.norm(residual) < self.convergence_tolerance and abs(constraint) < self.convergence_tolerance:
                    converged = True
                    break
                
                # Solve correction system (simplified)
                delta_u_corr = spsolve(K_tangent, residual)
                delta_lambda_corr = -constraint / np.dot(reference_load, delta_u_corr)
                
                current_displacement += delta_u_corr
                current_load_factor += delta_lambda_corr
            
            if converged:
                displacement = current_displacement
                load_factor = current_load_factor
                logger.info(f"  Converged: Load factor = {load_factor:.3f}")
            else:
                logger.warning(f"Step {step + 1} did not converge")
            
            step_results = {
                "load_factor": load_factor,
                "converged": converged,
                "iterations": iteration + 1,
                "displacement_norm": np.linalg.norm(displacement)
            }
            
            results["load_steps"].append(step_results)
        
        results["final_displacements"] = self._format_displacements(displacement)
        results["final_forces"] = self._calculate_element_forces_nonlinear(displacement)
        
        return results
    
    def _load_control_solve(self, 
                           load_case: LoadCase,
                           boundary_conditions: List[BoundaryCondition]) -> Dict:
        """
        Load control method (incremental loading)
        """
        logger.info("Load control nonlinear analysis")
        
        # Similar to Newton-Raphson but with fixed load increments
        return self._newton_raphson_solve(load_case, boundary_conditions)
    
    def _assemble_tangent_stiffness(self, displacement: np.ndarray) -> csc_matrix:
        """
        Assemble tangent stiffness matrix including geometric and material nonlinearity
        """
        # Start with linear stiffness
        K_linear = self.linear_solver.assemble_global_stiffness_matrix()
        
        # Add geometric stiffness (P-Delta effects)
        K_geometric = self._assemble_geometric_stiffness(displacement)
        
        # Add material stiffness modifications
        K_material = self._assemble_material_stiffness(displacement)
        
        # Total tangent stiffness
        K_tangent = K_linear + K_geometric + K_material
        
        return K_tangent
    
    def _assemble_geometric_stiffness(self, displacement: np.ndarray) -> csc_matrix:
        """
        Assemble geometric stiffness matrix for P-Delta effects
        """
        total_dofs = len(self.model.nodes) * 6
        K_geometric = np.zeros((total_dofs, total_dofs))
        
        # This is a simplified implementation
        # Full geometric stiffness requires element-level calculations
        
        for element in self.model.elements:
            if element.element_type == "beam":
                K_g_element = self._beam_geometric_stiffness(element, displacement)
                
                # Get DOF mapping
                dof_map = self.linear_solver._get_element_dof_mapping(element)
                
                # Add to global matrix
                for i, global_i in enumerate(dof_map):
                    for j, global_j in enumerate(dof_map):
                        K_geometric[global_i, global_j] += K_g_element[i, j]
        
        return csc_matrix(K_geometric)
    
    def _beam_geometric_stiffness(self, element, displacement: np.ndarray) -> np.ndarray:
        """
        Geometric stiffness matrix for beam element
        """
        # Get element displacements
        dof_map = self.linear_solver._get_element_dof_mapping(element)
        element_displacement = displacement[dof_map]
        
        # Calculate axial force
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Simplified axial force calculation
        E = element.material.elastic_modulus
        A = element.section.area
        axial_strain = (element_displacement[6] - element_displacement[0]) / L
        axial_force = E * A * axial_strain
        
        # Geometric stiffness matrix (simplified)
        K_g = np.zeros((12, 12))
        
        # P-Delta terms (simplified)
        if abs(axial_force) > 1e-10:
            # Transverse terms
            K_g[1, 1] = K_g[7, 7] = axial_force / L
            K_g[1, 7] = K_g[7, 1] = -axial_force / L
            K_g[2, 2] = K_g[8, 8] = axial_force / L
            K_g[2, 8] = K_g[8, 2] = -axial_force / L
        
        return K_g
    
    def _assemble_material_stiffness(self, displacement: np.ndarray) -> csc_matrix:
        """
        Assemble material stiffness modifications for material nonlinearity
        """
        # This would handle material nonlinearity (plasticity, cracking, etc.)
        # For now, return zero matrix (linear material behavior)
        total_dofs = len(self.model.nodes) * 6
        return csc_matrix((total_dofs, total_dofs))
    
    def _calculate_internal_forces(self, displacement: np.ndarray) -> np.ndarray:
        """
        Calculate internal forces for given displacement state
        """
        # This is a simplified implementation
        # Should include geometric and material nonlinearity effects
        
        # Start with linear internal forces
        K_linear = self.linear_solver.assemble_global_stiffness_matrix()
        internal_forces = K_linear @ displacement
        
        # Add nonlinear contributions
        # (geometric nonlinearity, material nonlinearity, etc.)
        
        return internal_forces
    
    def _apply_boundary_conditions_nonlinear(self, 
                                           K_matrix: csc_matrix,
                                           load_vector: np.ndarray,
                                           boundary_conditions: List[BoundaryCondition]) -> Tuple[csc_matrix, np.ndarray]:
        """
        Apply boundary conditions for nonlinear analysis
        """
        # Convert to dense for modification
        K_modified = K_matrix.toarray()
        F_modified = load_vector.copy()
        
        # Apply constraints
        for bc in boundary_conditions:
            node_index = self.linear_solver._get_node_index(bc.node_id)
            dof_start = node_index * 6
            
            if bc.support_type == "fixed":
                for i in range(6):
                    dof = dof_start + i
                    # Penalty method
                    K_modified[dof, dof] += 1e12
                    F_modified[dof] = 0.0
            elif bc.support_type == "pinned":
                for i in range(3):
                    dof = dof_start + i
                    K_modified[dof, dof] += 1e12
                    F_modified[dof] = 0.0
            elif bc.support_type == "roller":
                dof = dof_start + 2  # Z-direction
                K_modified[dof, dof] += 1e12
                F_modified[dof] = 0.0
        
        return csc_matrix(K_modified), F_modified
    
    def _calculate_element_forces_nonlinear(self, displacement: np.ndarray) -> Dict:
        """
        Calculate element forces including nonlinear effects
        """
        element_forces = {}
        
        for element in self.model.elements:
            # Get element displacements
            dof_map = self.linear_solver._get_element_dof_mapping(element)
            element_displacement = displacement[dof_map]
            
            # Calculate element forces (including nonlinear effects)
            if element.element_type == "beam":
                forces = self._beam_forces_nonlinear(element, element_displacement)
            elif element.element_type == "truss":
                forces = self._truss_forces_nonlinear(element, element_displacement)
            else:
                # Fallback to linear calculation
                k_element = self.linear_solver._get_element_stiffness_matrix(element)
                force_vector = k_element @ element_displacement
                forces = {
                    "axial": force_vector[0],
                    "shear_y": force_vector[1],
                    "shear_z": force_vector[2],
                    "torsion": force_vector[3],
                    "moment_y": force_vector[4],
                    "moment_z": force_vector[5]
                }
            
            element_forces[element.id] = forces
        
        return element_forces
    
    def _beam_forces_nonlinear(self, element, element_displacement: np.ndarray) -> Dict:
        """
        Calculate beam forces including geometric nonlinearity
        """
        # Get element properties
        E = element.material.elastic_modulus
        A = element.section.area
        
        # Element geometry
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Calculate deformed length
        dx_def = (end_node.x + element_displacement[6]) - (start_node.x + element_displacement[0])
        dy_def = (end_node.y + element_displacement[7]) - (start_node.y + element_displacement[1])
        dz_def = (end_node.z + element_displacement[8]) - (start_node.z + element_displacement[2])
        L_def = np.sqrt(dx_def**2 + dy_def**2 + dz_def**2)
        
        # Geometric strain
        strain = (L_def - L) / L
        
        # Axial force (including geometric effects)
        axial_force = E * A * strain
        
        # For simplicity, other forces calculated linearly
        k_element = self.linear_solver._get_element_stiffness_matrix(element)
        force_vector = k_element @ element_displacement
        
        return {
            "axial": axial_force,
            "shear_y": force_vector[1],
            "shear_z": force_vector[2],
            "torsion": force_vector[3],
            "moment_y": force_vector[4],
            "moment_z": force_vector[5]
        }
    
    def _truss_forces_nonlinear(self, element, element_displacement: np.ndarray) -> Dict:
        """
        Calculate truss forces including geometric nonlinearity
        """
        # Similar to beam but only axial force
        E = element.material.elastic_modulus
        A = element.section.area
        
        start_node = self.model.get_node(element.start_node_id)
        end_node = self.model.get_node(element.end_node_id)
        L = np.sqrt(
            (end_node.x - start_node.x)**2 +
            (end_node.y - start_node.y)**2 +
            (end_node.z - start_node.z)**2
        )
        
        # Deformed length
        dx_def = (end_node.x + element_displacement[3]) - (start_node.x + element_displacement[0])
        dy_def = (end_node.y + element_displacement[4]) - (start_node.y + element_displacement[1])
        dz_def = (end_node.z + element_displacement[5]) - (start_node.z + element_displacement[2])
        L_def = np.sqrt(dx_def**2 + dy_def**2 + dz_def**2)
        
        strain = (L_def - L) / L
        axial_force = E * A * strain
        
        return {
            "axial": axial_force,
            "shear_y": 0.0,
            "shear_z": 0.0,
            "torsion": 0.0,
            "moment_y": 0.0,
            "moment_z": 0.0
        }
    
    def _format_displacements(self, displacement: np.ndarray) -> Dict:
        """
        Format displacement results
        """
        displacements = {}
        
        for i, node in enumerate(self.model.nodes):
            dof_start = i * 6
            displacements[node.id] = {
                "ux": displacement[dof_start],
                "uy": displacement[dof_start + 1],
                "uz": displacement[dof_start + 2],
                "rx": displacement[dof_start + 3],
                "ry": displacement[dof_start + 4],
                "rz": displacement[dof_start + 5]
            }
        
        return displacements
    
    def set_analysis_parameters(self, 
                               max_iterations: int = 50,
                               convergence_tolerance: float = 1e-6,
                               load_steps: int = 10):
        """
        Set analysis parameters
        """
        self.max_iterations = max_iterations
        self.convergence_tolerance = convergence_tolerance
        self.load_steps = load_steps
        
        logger.info(f"Analysis parameters set: max_iter={max_iterations}, "
                   f"tolerance={convergence_tolerance}, steps={load_steps}")
    
    def get_convergence_history(self) -> List[Dict]:
        """
        Get convergence history for analysis
        """
        return self.iteration_history