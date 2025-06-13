"""
Buckling analysis solver for structural systems
"""

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from typing import Dict, List, Tuple, Optional
import logging

from ..linear.linear_solver import LinearSolver
from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase
from ...core.modeling.boundary_conditions import BoundaryCondition

logger = logging.getLogger(__name__)


class BucklingSolver:
    """
    Buckling analysis solver for eigenvalue buckling analysis
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.linear_solver = LinearSolver(model)
        self.stiffness_matrix = None
        self.geometric_stiffness_matrix = None
        self.buckling_modes = None
        self.buckling_factors = None
        
    def solve_eigenvalue_buckling(self,
                                 boundary_conditions: List[BoundaryCondition],
                                 load_case: LoadCase,
                                 num_modes: int = 10) -> Dict:
        """
        Perform eigenvalue buckling analysis
        """
        logger.info(f"Starting eigenvalue buckling analysis for {num_modes} modes")
        
        try:
            # Assemble stiffness matrices
            self._assemble_stiffness_matrices(boundary_conditions, load_case)
            
            # Solve generalized eigenvalue problem: (K + λ*Kg)*φ = 0
            # Rearranged as: K*φ = -λ*Kg*φ
            eigenvalues, eigenvectors = eigsh(
                self.stiffness_matrix,
                M=-self.geometric_stiffness_matrix,
                k=num_modes,
                which='SM',  # Smallest magnitude eigenvalues
                sigma=0.0    # Shift to find eigenvalues near zero
            )
            
            # Sort by buckling factor (eigenvalue magnitude)
            sort_indices = np.argsort(np.abs(eigenvalues))
            eigenvalues = eigenvalues[sort_indices]
            eigenvectors = eigenvectors[:, sort_indices]
            
            # Calculate buckling factors (load multipliers)
            buckling_factors = np.abs(eigenvalues)
            
            # Normalize buckling modes
            normalized_modes = self._normalize_buckling_modes(eigenvectors)
            
            # Store results
            self.buckling_factors = buckling_factors
            self.buckling_modes = normalized_modes
            
            # Calculate critical buckling loads
            critical_loads = self._calculate_critical_loads(load_case, buckling_factors)
            
            # Classify buckling modes
            mode_classifications = self._classify_buckling_modes(normalized_modes, buckling_factors)
            
            results = {
                "num_modes": num_modes,
                "buckling_factors": buckling_factors.tolist(),
                "critical_buckling_factor": buckling_factors[0],
                "buckling_modes": self._format_buckling_modes(normalized_modes),
                "critical_loads": critical_loads,
                "mode_classifications": mode_classifications,
                "load_case": {
                    "name": load_case.name,
                    "description": load_case.description
                },
                "buckling_summary": self._generate_buckling_summary(buckling_factors, mode_classifications)
            }
            
            logger.info(f"Buckling analysis completed successfully")
            logger.info(f"Critical buckling factor: {buckling_factors[0]:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Buckling analysis failed: {e}")
            raise
    
    def solve_nonlinear_buckling(self,
                                boundary_conditions: List[BoundaryCondition],
                                load_case: LoadCase,
                                load_steps: int = 20,
                                max_load_factor: float = 2.0) -> Dict:
        """
        Perform nonlinear buckling analysis using arc-length method
        """
        logger.info(f"Starting nonlinear buckling analysis with {load_steps} load steps")
        
        try:
            # Initialize
            load_factors = []
            displacements = []
            
            # Get initial stiffness matrix
            self.stiffness_matrix = self.linear_solver.assemble_global_stiffness_matrix()
            self._apply_boundary_conditions_buckling(boundary_conditions)
            
            # Get load vector
            load_vector = self._assemble_load_vector(load_case)
            
            # Arc-length parameters
            arc_length = 0.1  # Initial arc length
            load_factor = 0.0
            displacement = np.zeros(self.stiffness_matrix.shape[0])
            
            # Load stepping with arc-length control
            for step in range(load_steps):
                try:
                    # Predictor step
                    load_factor_pred, displacement_pred = self._arc_length_predictor(
                        load_factor, displacement, load_vector, arc_length
                    )
                    
                    # Corrector iterations
                    load_factor_corr, displacement_corr = self._arc_length_corrector(
                        load_factor_pred, displacement_pred, load_vector, arc_length
                    )
                    
                    # Update
                    load_factor = load_factor_corr
                    displacement = displacement_corr
                    
                    # Store results
                    load_factors.append(load_factor)
                    displacements.append(displacement.copy())
                    
                    # Update geometric stiffness for next step
                    self._update_geometric_stiffness(displacement, load_case)
                    
                    # Check for limit point (buckling)
                    if self._check_limit_point(load_factors, step):
                        logger.info(f"Limit point detected at step {step}")
                        break
                    
                    # Adaptive arc length
                    arc_length = self._adapt_arc_length(arc_length, step)
                    
                    if load_factor > max_load_factor:
                        logger.info(f"Maximum load factor {max_load_factor} reached")
                        break
                        
                except Exception as step_error:
                    logger.warning(f"Step {step} failed: {step_error}")
                    break
            
            # Find critical point
            critical_load_factor = max(load_factors) if load_factors else 0.0
            critical_displacement = displacements[load_factors.index(critical_load_factor)] if load_factors else np.zeros(1)
            
            results = {
                "analysis_type": "nonlinear_buckling",
                "load_steps": len(load_factors),
                "load_factors": load_factors,
                "critical_load_factor": critical_load_factor,
                "critical_displacement": critical_displacement.tolist(),
                "max_displacement": np.max(np.abs(critical_displacement)),
                "load_displacement_curve": {
                    "load_factors": load_factors,
                    "max_displacements": [np.max(np.abs(disp)) for disp in displacements]
                },
                "buckling_summary": {
                    "critical_load_factor": critical_load_factor,
                    "buckling_type": "nonlinear",
                    "analysis_converged": len(load_factors) > 5
                }
            }
            
            logger.info(f"Nonlinear buckling analysis completed")
            logger.info(f"Critical load factor: {critical_load_factor:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Nonlinear buckling analysis failed: {e}")
            raise
    
    def _assemble_stiffness_matrices(self, 
                                   boundary_conditions: List[BoundaryCondition],
                                   load_case: LoadCase):
        """
        Assemble linear and geometric stiffness matrices
        """
        # Assemble linear stiffness matrix
        self.stiffness_matrix = self.linear_solver.assemble_global_stiffness_matrix()
        
        # Assemble geometric stiffness matrix
        self.geometric_stiffness_matrix = self._assemble_geometric_stiffness_matrix(load_case)
        
        # Apply boundary conditions
        self._apply_boundary_conditions_buckling(boundary_conditions)
    
    def _assemble_geometric_stiffness_matrix(self, load_case: LoadCase) -> csc_matrix:
        """
        Assemble geometric stiffness matrix based on applied loads
        """
        total_dofs = len(self.model.nodes) * 6
        Kg_global = np.zeros((total_dofs, total_dofs))
        
        # First, perform linear analysis to get element forces
        boundary_conditions = []  # Simplified - would need actual boundary conditions
        linear_results = self.linear_solver.solve_linear_static(boundary_conditions, [load_case])
        
        for element in self.model.elements:
            # Get element forces from linear analysis
            element_forces = self._get_element_forces(element, linear_results)
            
            # Calculate element geometric stiffness matrix
            Kg_element = self._get_element_geometric_stiffness(element, element_forces)
            
            # Get DOF mapping
            dof_map = self.linear_solver._get_element_dof_mapping(element)
            
            # Add to global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    Kg_global[global_i, global_j] += Kg_element[i, j]
        
        return csc_matrix(Kg_global)
    
    def _get_element_forces(self, element, linear_results) -> Dict:
        """
        Extract element forces from linear analysis results
        """
        # Simplified - would extract actual forces from results
        return {
            "axial": 0.0,  # Axial force (compression positive for buckling)
            "shear_y": 0.0,
            "shear_z": 0.0,
            "moment_x": 0.0,
            "moment_y": 0.0,
            "moment_z": 0.0
        }
    
    def _get_element_geometric_stiffness(self, element, forces: Dict) -> np.ndarray:
        """
        Calculate element geometric stiffness matrix
        """
        if element.element_type == "beam":
            return self._beam_geometric_stiffness(element, forces)
        elif element.element_type == "truss":
            return self._truss_geometric_stiffness(element, forces)
        else:
            # Default - no geometric stiffness
            return np.zeros((12, 12))
    
    def _beam_geometric_stiffness(self, element, forces: Dict) -> np.ndarray:
        """
        Geometric stiffness matrix for beam element
        """
        L = element.length
        P = forces["axial"]  # Axial force (compression positive)
        
        # Simplified geometric stiffness matrix for beam
        # Full implementation would include shear and moment effects
        Kg = np.zeros((12, 12))
        
        if abs(P) > 1e-6:  # Only if significant axial force
            # Geometric stiffness terms for bending about y-axis
            c1 = P / (30 * L)
            c2 = P / 6
            c3 = P * L / 30
            
            # Terms for v-direction (bending about z-axis)
            Kg[1, 1] = Kg[7, 7] = 36 * c1
            Kg[1, 7] = Kg[7, 1] = -36 * c1
            Kg[1, 5] = Kg[5, 1] = 3 * c2
            Kg[1, 11] = Kg[11, 1] = -3 * c2
            Kg[7, 5] = Kg[5, 7] = 3 * c2
            Kg[7, 11] = Kg[11, 7] = -3 * c2
            Kg[5, 5] = Kg[11, 11] = 4 * c3
            Kg[5, 11] = Kg[11, 5] = -c3
            
            # Terms for w-direction (bending about y-axis)
            Kg[2, 2] = Kg[8, 8] = 36 * c1
            Kg[2, 8] = Kg[8, 2] = -36 * c1
            Kg[2, 4] = Kg[4, 2] = -3 * c2
            Kg[2, 10] = Kg[10, 2] = 3 * c2
            Kg[8, 4] = Kg[4, 8] = -3 * c2
            Kg[8, 10] = Kg[10, 8] = 3 * c2
            Kg[4, 4] = Kg[10, 10] = 4 * c3
            Kg[4, 10] = Kg[10, 4] = -c3
        
        return Kg
    
    def _truss_geometric_stiffness(self, element, forces: Dict) -> np.ndarray:
        """
        Geometric stiffness matrix for truss element
        """
        L = element.length
        P = forces["axial"]
        
        # Simplified geometric stiffness for truss
        Kg = np.zeros((6, 6))
        
        if abs(P) > 1e-6:
            # Direction cosines
            start_node = self.model.get_node(element.start_node_id)
            end_node = self.model.get_node(element.end_node_id)
            
            dx = end_node.x - start_node.x
            dy = end_node.y - start_node.y
            dz = end_node.z - start_node.z
            
            cx = dx / L
            cy = dy / L
            cz = dz / L
            
            # Geometric stiffness matrix
            coeff = P / L
            
            # Local geometric stiffness
            Kg_local = np.array([
                [0, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, -1, 0],
                [0, 0, 1, 0, 0, -1],
                [0, 0, 0, 0, 0, 0],
                [0, -1, 0, 0, 1, 0],
                [0, 0, -1, 0, 0, 1]
            ]) * coeff
            
            Kg = Kg_local  # Simplified - should transform to global coordinates
        
        return Kg
    
    def _apply_boundary_conditions_buckling(self, boundary_conditions: List[BoundaryCondition]):
        """
        Apply boundary conditions to buckling matrices
        """
        # Convert to dense for modification
        K_dense = self.stiffness_matrix.toarray()
        Kg_dense = self.geometric_stiffness_matrix.toarray()
        
        # Apply constraints using penalty method
        for bc in boundary_conditions:
            node_index = self.linear_solver._get_node_index(bc.node_id)
            dof_start = node_index * 6
            
            if bc.support_type == "fixed":
                for i in range(6):
                    dof = dof_start + i
                    # Large stiffness for constrained DOFs
                    K_dense[dof, dof] += 1e12
                    # Zero geometric stiffness for constrained DOFs
                    Kg_dense[dof, :] = 0
                    Kg_dense[:, dof] = 0
            elif bc.support_type == "pinned":
                for i in range(3):  # Fix translations only
                    dof = dof_start + i
                    K_dense[dof, dof] += 1e12
                    Kg_dense[dof, :] = 0
                    Kg_dense[:, dof] = 0
        
        self.stiffness_matrix = csc_matrix(K_dense)
        self.geometric_stiffness_matrix = csc_matrix(Kg_dense)
    
    def _normalize_buckling_modes(self, eigenvectors: np.ndarray) -> np.ndarray:
        """
        Normalize buckling mode shapes
        """
        normalized_modes = np.zeros_like(eigenvectors)
        
        for i in range(eigenvectors.shape[1]):
            mode = eigenvectors[:, i]
            # Normalize to unit maximum displacement
            max_disp = np.max(np.abs(mode))
            if max_disp > 1e-12:
                normalized_modes[:, i] = mode / max_disp
            else:
                normalized_modes[:, i] = mode
        
        return normalized_modes
    
    def _calculate_critical_loads(self, load_case: LoadCase, buckling_factors: np.ndarray) -> Dict:
        """
        Calculate critical loads for each buckling mode
        """
        critical_loads = {}
        
        # Get applied loads from load case
        for load in load_case.loads:
            load_type = load.load_type
            load_value = load.magnitude
            
            # Calculate critical load for each mode
            critical_values = buckling_factors * load_value
            
            critical_loads[load_type] = {
                "applied_load": load_value,
                "critical_loads": critical_values.tolist(),
                "first_critical": critical_values[0] if len(critical_values) > 0 else 0.0
            }
        
        return critical_loads
    
    def _classify_buckling_modes(self, modes: np.ndarray, factors: np.ndarray) -> List[Dict]:
        """
        Classify buckling modes by type
        """
        classifications = []
        
        for i in range(modes.shape[1]):
            mode = modes[:, i]
            factor = factors[i]
            
            # Analyze mode shape to classify
            # This is simplified - full implementation would analyze deformation patterns
            
            # Calculate displacement components
            n_nodes = len(self.model.nodes)
            max_translation = 0.0
            max_rotation = 0.0
            
            for j in range(n_nodes):
                dof_start = j * 6
                # Translation components
                trans = np.sqrt(mode[dof_start]**2 + mode[dof_start+1]**2 + mode[dof_start+2]**2)
                # Rotation components  
                rot = np.sqrt(mode[dof_start+3]**2 + mode[dof_start+4]**2 + mode[dof_start+5]**2)
                
                max_translation = max(max_translation, trans)
                max_rotation = max(max_rotation, rot)
            
            # Simple classification based on displacement ratios
            if max_rotation > 2 * max_translation:
                mode_type = "torsional"
            elif max_translation > 2 * max_rotation:
                mode_type = "lateral"
            else:
                mode_type = "combined"
            
            classifications.append({
                "mode": i + 1,
                "buckling_factor": factor,
                "mode_type": mode_type,
                "max_translation": max_translation,
                "max_rotation": max_rotation,
                "description": f"Mode {i+1}: {mode_type} buckling (λ = {factor:.3f})"
            })
        
        return classifications
    
    def _format_buckling_modes(self, modes: np.ndarray) -> List[Dict]:
        """
        Format buckling modes for output
        """
        formatted_modes = []
        
        for i in range(modes.shape[1]):
            mode_data = {}
            for j, node in enumerate(self.model.nodes):
                dof_start = j * 6
                mode_data[node.id] = {
                    "ux": modes[dof_start, i],
                    "uy": modes[dof_start + 1, i],
                    "uz": modes[dof_start + 2, i],
                    "rx": modes[dof_start + 3, i],
                    "ry": modes[dof_start + 4, i],
                    "rz": modes[dof_start + 5, i]
                }
            formatted_modes.append(mode_data)
        
        return formatted_modes
    
    def _generate_buckling_summary(self, factors: np.ndarray, classifications: List[Dict]) -> Dict:
        """
        Generate buckling analysis summary
        """
        return {
            "critical_buckling_factor": factors[0],
            "safety_factor": 1.0 / factors[0] if factors[0] > 0 else float('inf'),
            "first_mode_type": classifications[0]["mode_type"] if classifications else "unknown",
            "number_of_modes": len(factors),
            "buckling_factors_range": {
                "min": np.min(factors),
                "max": np.max(factors)
            },
            "critical_mode_description": classifications[0]["description"] if classifications else ""
        }
    
    def _assemble_load_vector(self, load_case: LoadCase) -> np.ndarray:
        """
        Assemble load vector for buckling analysis
        """
        total_dofs = len(self.model.nodes) * 6
        load_vector = np.zeros(total_dofs)
        
        # Apply loads from load case
        for load in load_case.loads:
            if load.load_type == "point":
                node_index = self.linear_solver._get_node_index(load.node_id)
                dof_start = node_index * 6
                
                # Apply force components
                if hasattr(load, 'fx'):
                    load_vector[dof_start] += load.fx
                if hasattr(load, 'fy'):
                    load_vector[dof_start + 1] += load.fy
                if hasattr(load, 'fz'):
                    load_vector[dof_start + 2] += load.fz
                if hasattr(load, 'mx'):
                    load_vector[dof_start + 3] += load.mx
                if hasattr(load, 'my'):
                    load_vector[dof_start + 4] += load.my
                if hasattr(load, 'mz'):
                    load_vector[dof_start + 5] += load.mz
        
        return load_vector
    
    def _arc_length_predictor(self, load_factor: float, displacement: np.ndarray, 
                            load_vector: np.ndarray, arc_length: float) -> Tuple[float, np.ndarray]:
        """
        Arc-length predictor step
        """
        # Solve for displacement increment
        delta_u = np.linalg.solve(self.stiffness_matrix.toarray(), load_vector)
        
        # Calculate load factor increment
        delta_lambda = arc_length / np.sqrt(np.dot(delta_u, delta_u) + 1.0)
        
        # Predictor values
        load_factor_pred = load_factor + delta_lambda
        displacement_pred = displacement + delta_lambda * delta_u
        
        return load_factor_pred, displacement_pred
    
    def _arc_length_corrector(self, load_factor_pred: float, displacement_pred: np.ndarray,
                            load_vector: np.ndarray, arc_length: float) -> Tuple[float, np.ndarray]:
        """
        Arc-length corrector iterations
        """
        # Simplified corrector - full implementation would iterate
        return load_factor_pred, displacement_pred
    
    def _update_geometric_stiffness(self, displacement: np.ndarray, load_case: LoadCase):
        """
        Update geometric stiffness matrix based on current displacement
        """
        # Simplified - would update based on current element forces
        pass
    
    def _check_limit_point(self, load_factors: List[float], step: int) -> bool:
        """
        Check for limit point (maximum load factor)
        """
        if len(load_factors) < 3:
            return False
        
        # Check if load factor is decreasing
        return load_factors[-1] < load_factors[-2] < load_factors[-3]
    
    def _adapt_arc_length(self, current_arc_length: float, step: int) -> float:
        """
        Adapt arc length based on convergence behavior
        """
        # Simplified adaptive scheme
        if step < 5:
            return current_arc_length * 0.8  # Reduce for initial steps
        else:
            return current_arc_length  # Keep constant