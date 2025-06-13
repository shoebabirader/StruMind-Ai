"""
Dynamic analysis solver for modal, response spectrum, and time history analysis
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from scipy.integrate import odeint
import uuid
import time

from db.models.structural import Node, Element
from db.models.analysis import AnalysisCase, ModalResult
from core.exceptions import ComputationError, AnalysisError
from .matrix import StiffnessMatrixAssembler, MassMatrixAssembler, DOFManager
from .linear import LinearSolver


class ModalAnalysis:
    """Modal analysis solver"""
    
    def __init__(self):
        self.stiffness_assembler = StiffnessMatrixAssembler()
        self.mass_assembler = MassMatrixAssembler()
        self.results = {}
    
    def run_modal_analysis(self, analysis_case: AnalysisCase, nodes: List[Node],
                          elements: List[Element], materials: Dict[uuid.UUID, Any],
                          sections: Dict[uuid.UUID, Any],
                          boundary_conditions: List[Any],
                          num_modes: int = 10) -> Dict[str, Any]:
        """Run modal analysis to find natural frequencies and mode shapes"""
        try:
            # Step 1: Assemble stiffness matrix
            K_global, dof_manager = self.stiffness_assembler.assemble_global_stiffness_matrix(
                nodes, elements, materials, sections
            )
            
            # Step 2: Apply boundary conditions
            self._apply_boundary_conditions(boundary_conditions, dof_manager)
            dof_manager.finalize_dof_mapping()
            
            # Step 3: Assemble mass matrix
            M_global = self.mass_assembler.assemble_global_mass_matrix(
                nodes, elements, materials, sections, dof_manager
            )
            
            # Step 4: Extract free DOF matrices
            free_dofs = dof_manager.free_dofs
            K_ff = K_global[np.ix_(free_dofs, free_dofs)]
            M_ff = M_global[np.ix_(free_dofs, free_dofs)]
            
            # Step 5: Solve generalized eigenvalue problem
            eigenvalues, eigenvectors = self._solve_eigenvalue_problem(
                K_ff, M_ff, num_modes
            )
            
            # Step 6: Calculate modal properties
            modal_results = self._calculate_modal_properties(
                eigenvalues, eigenvectors, M_ff, free_dofs, dof_manager
            )
            
            # Step 7: Prepare results
            results = {
                'eigenvalues': eigenvalues,
                'eigenvectors': eigenvectors,
                'modal_results': modal_results,
                'free_dofs': free_dofs,
                'dof_manager': dof_manager,
                'stiffness_matrix': K_global,
                'mass_matrix': M_global
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Modal analysis failed: {str(e)}")
    
    def _apply_boundary_conditions(self, boundary_conditions: List[Any],
                                 dof_manager: DOFManager):
        """Apply boundary conditions"""
        for bc in boundary_conditions:
            restraints = [
                bc.restraint_x, bc.restraint_y, bc.restraint_z,
                bc.restraint_xx, bc.restraint_yy, bc.restraint_zz
            ]
            dof_manager.apply_boundary_conditions(bc.node_id, restraints)
    
    def _solve_eigenvalue_problem(self, K: csr_matrix, M: csr_matrix,
                                num_modes: int) -> Tuple[np.ndarray, np.ndarray]:
        """Solve generalized eigenvalue problem K*phi = lambda*M*phi"""
        try:
            # Use shift-invert mode for better convergence
            sigma = 0.0  # Shift value
            
            eigenvalues, eigenvectors = eigsh(
                K, k=min(num_modes, K.shape[0]-1), M=M, sigma=sigma,
                which='LM', mode='normal'
            )
            
            # Sort by frequency
            idx = np.argsort(eigenvalues)
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
            
            # Remove rigid body modes (near-zero eigenvalues)
            tolerance = 1e-6
            valid_modes = eigenvalues > tolerance
            eigenvalues = eigenvalues[valid_modes]
            eigenvectors = eigenvectors[:, valid_modes]
            
            return eigenvalues, eigenvectors
            
        except Exception as e:
            raise ComputationError(f"Eigenvalue solution failed: {str(e)}")
    
    def _calculate_modal_properties(self, eigenvalues: np.ndarray, 
                                  eigenvectors: np.ndarray, M: csr_matrix,
                                  free_dofs: List[int], 
                                  dof_manager: DOFManager) -> List[Dict[str, Any]]:
        """Calculate modal properties for each mode"""
        modal_results = []
        
        for i, (eigenval, eigenvec) in enumerate(zip(eigenvalues, eigenvectors.T)):
            # Natural frequency
            omega = np.sqrt(eigenval)  # rad/s
            frequency = omega / (2 * np.pi)  # Hz
            period = 1.0 / frequency if frequency > 0 else float('inf')
            
            # Normalize mode shape
            modal_mass = eigenvec.T @ M @ eigenvec
            if modal_mass > 0:
                eigenvec = eigenvec / np.sqrt(modal_mass)
            
            # Modal participation factors
            participation_factors = self._calculate_participation_factors(
                eigenvec, M, free_dofs, dof_manager
            )
            
            # Modal mass ratios
            total_mass = M.diagonal().sum()
            mass_ratios = {
                'x': participation_factors['x']**2 / total_mass if total_mass > 0 else 0,
                'y': participation_factors['y']**2 / total_mass if total_mass > 0 else 0,
                'z': participation_factors['z']**2 / total_mass if total_mass > 0 else 0
            }
            
            modal_result = {
                'mode_number': i + 1,
                'eigenvalue': eigenval,
                'frequency': frequency,
                'period': period,
                'circular_frequency': omega,
                'mode_shape': eigenvec,
                'participation_factors': participation_factors,
                'mass_ratios': mass_ratios,
                'modal_mass': modal_mass
            }
            
            modal_results.append(modal_result)
        
        # Calculate cumulative mass ratios
        cumulative_mass_x = 0
        cumulative_mass_y = 0
        cumulative_mass_z = 0
        
        for result in modal_results:
            cumulative_mass_x += result['mass_ratios']['x']
            cumulative_mass_y += result['mass_ratios']['y']
            cumulative_mass_z += result['mass_ratios']['z']
            
            result['cumulative_mass_ratios'] = {
                'x': cumulative_mass_x,
                'y': cumulative_mass_y,
                'z': cumulative_mass_z
            }
        
        return modal_results
    
    def _calculate_participation_factors(self, mode_shape: np.ndarray, M: csr_matrix,
                                       free_dofs: List[int], 
                                       dof_manager: DOFManager) -> Dict[str, float]:
        """Calculate modal participation factors"""
        # Influence vectors for unit ground acceleration
        influence_x = np.zeros(len(free_dofs))
        influence_y = np.zeros(len(free_dofs))
        influence_z = np.zeros(len(free_dofs))
        
        # Map free DOFs to translational directions
        for i, global_dof in enumerate(free_dofs):
            # Find which node and direction this DOF corresponds to
            for node_id, node_dofs in dof_manager.node_dof_map.items():
                if global_dof in node_dofs:
                    local_dof = node_dofs.index(global_dof)
                    if local_dof == 0:  # X translation
                        influence_x[i] = 1.0
                    elif local_dof == 1:  # Y translation
                        influence_y[i] = 1.0
                    elif local_dof == 2:  # Z translation
                        influence_z[i] = 1.0
                    break
        
        # Calculate participation factors
        modal_mass = mode_shape.T @ M @ mode_shape
        
        if modal_mass > 0:
            gamma_x = (mode_shape.T @ M @ influence_x) / modal_mass
            gamma_y = (mode_shape.T @ M @ influence_y) / modal_mass
            gamma_z = (mode_shape.T @ M @ influence_z) / modal_mass
        else:
            gamma_x = gamma_y = gamma_z = 0.0
        
        return {
            'x': gamma_x,
            'y': gamma_y,
            'z': gamma_z
        }
    
    def get_mode_shape(self, analysis_case_id: uuid.UUID, mode_number: int,
                      node_id: uuid.UUID) -> Optional[Dict[str, float]]:
        """Get mode shape displacements for a specific node and mode"""
        results = self.results.get(analysis_case_id)
        if not results or mode_number < 1:
            return None
        
        modal_results = results['modal_results']
        if mode_number > len(modal_results):
            return None
        
        mode_result = modal_results[mode_number - 1]
        mode_shape = mode_result['mode_shape']
        free_dofs = results['free_dofs']
        dof_manager = results['dof_manager']
        
        node_dofs = dof_manager.get_node_dofs(node_id)
        if not node_dofs:
            return None
        
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


class ResponseSpectrumAnalysis:
    """Response spectrum analysis"""
    
    def __init__(self):
        self.modal_analysis = ModalAnalysis()
        self.results = {}
    
    def run_response_spectrum_analysis(self, analysis_case: AnalysisCase,
                                     nodes: List[Node], elements: List[Element],
                                     materials: Dict[uuid.UUID, Any],
                                     sections: Dict[uuid.UUID, Any],
                                     boundary_conditions: List[Any],
                                     response_spectrum: Dict[str, Any]) -> Dict[str, Any]:
        """Run response spectrum analysis"""
        try:
            # Step 1: Perform modal analysis
            modal_results = self.modal_analysis.run_modal_analysis(
                analysis_case, nodes, elements, materials, sections,
                boundary_conditions
            )
            
            # Step 2: Calculate modal responses
            modal_responses = self._calculate_modal_responses(
                modal_results['modal_results'], response_spectrum
            )
            
            # Step 3: Combine modal responses
            combined_responses = self._combine_modal_responses(
                modal_responses, response_spectrum.get('combination_method', 'srss')
            )
            
            results = {
                'modal_results': modal_results,
                'modal_responses': modal_responses,
                'combined_responses': combined_responses,
                'response_spectrum': response_spectrum
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Response spectrum analysis failed: {str(e)}")
    
    def _calculate_modal_responses(self, modal_results: List[Dict[str, Any]],
                                 response_spectrum: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate response for each mode"""
        modal_responses = []
        
        # Extract spectrum data
        periods = np.array(response_spectrum['periods'])
        accelerations = np.array(response_spectrum['accelerations'])
        damping_ratio = response_spectrum.get('damping_ratio', 0.05)
        
        for mode_result in modal_results:
            period = mode_result['period']
            participation_factor = mode_result['participation_factors']['z']  # Assume vertical excitation
            
            # Interpolate spectral acceleration
            if period <= periods[0]:
                spectral_acceleration = accelerations[0]
            elif period >= periods[-1]:
                spectral_acceleration = accelerations[-1]
            else:
                spectral_acceleration = np.interp(period, periods, accelerations)
            
            # Calculate modal response
            modal_displacement = (participation_factor * spectral_acceleration * 
                                period**2) / (4 * np.pi**2)
            
            modal_response = {
                'mode_number': mode_result['mode_number'],
                'spectral_acceleration': spectral_acceleration,
                'modal_displacement': modal_displacement,
                'modal_force': modal_displacement * mode_result['eigenvalue']
            }
            
            modal_responses.append(modal_response)
        
        return modal_responses
    
    def _combine_modal_responses(self, modal_responses: List[Dict[str, Any]],
                               combination_method: str) -> Dict[str, Any]:
        """Combine modal responses using specified method"""
        if combination_method.lower() == 'srss':
            # Square Root of Sum of Squares
            total_displacement = np.sqrt(sum(
                resp['modal_displacement']**2 for resp in modal_responses
            ))
            total_force = np.sqrt(sum(
                resp['modal_force']**2 for resp in modal_responses
            ))
        elif combination_method.lower() == 'cqc':
            # Complete Quadratic Combination (simplified)
            total_displacement = np.sqrt(sum(
                resp['modal_displacement']**2 for resp in modal_responses
            ))
            total_force = np.sqrt(sum(
                resp['modal_force']**2 for resp in modal_responses
            ))
        else:
            # Absolute sum
            total_displacement = sum(
                abs(resp['modal_displacement']) for resp in modal_responses
            )
            total_force = sum(
                abs(resp['modal_force']) for resp in modal_responses
            )
        
        return {
            'total_displacement': total_displacement,
            'total_force': total_force,
            'combination_method': combination_method
        }


class TimeHistoryAnalysis:
    """Time history analysis"""
    
    def __init__(self):
        self.stiffness_assembler = StiffnessMatrixAssembler()
        self.mass_assembler = MassMatrixAssembler()
        self.results = {}
    
    def run_time_history_analysis(self, analysis_case: AnalysisCase,
                                 nodes: List[Node], elements: List[Element],
                                 materials: Dict[uuid.UUID, Any],
                                 sections: Dict[uuid.UUID, Any],
                                 boundary_conditions: List[Any],
                                 time_history: Dict[str, Any]) -> Dict[str, Any]:
        """Run time history analysis"""
        try:
            # Step 1: Assemble system matrices
            K_global, dof_manager = self.stiffness_assembler.assemble_global_stiffness_matrix(
                nodes, elements, materials, sections
            )
            
            self._apply_boundary_conditions(boundary_conditions, dof_manager)
            dof_manager.finalize_dof_mapping()
            
            M_global = self.mass_assembler.assemble_global_mass_matrix(
                nodes, elements, materials, sections, dof_manager
            )
            
            # Step 2: Create damping matrix
            C_global = self._create_damping_matrix(
                K_global, M_global, time_history.get('damping_ratio', 0.05)
            )
            
            # Step 3: Extract free DOF system
            free_dofs = dof_manager.free_dofs
            M_ff = M_global[np.ix_(free_dofs, free_dofs)]
            C_ff = C_global[np.ix_(free_dofs, free_dofs)]
            K_ff = K_global[np.ix_(free_dofs, free_dofs)]
            
            # Step 4: Solve dynamic equation
            time_points = np.array(time_history['time'])
            ground_acceleration = np.array(time_history['acceleration'])
            
            response_history = self._solve_dynamic_equation(
                M_ff, C_ff, K_ff, time_points, ground_acceleration, dof_manager
            )
            
            results = {
                'time_points': time_points,
                'response_history': response_history,
                'free_dofs': free_dofs,
                'dof_manager': dof_manager
            }
            
            self.results[analysis_case.id] = results
            return results
            
        except Exception as e:
            raise AnalysisError(f"Time history analysis failed: {str(e)}")
    
    def _apply_boundary_conditions(self, boundary_conditions: List[Any],
                                 dof_manager: DOFManager):
        """Apply boundary conditions"""
        for bc in boundary_conditions:
            restraints = [
                bc.restraint_x, bc.restraint_y, bc.restraint_z,
                bc.restraint_xx, bc.restraint_yy, bc.restraint_zz
            ]
            dof_manager.apply_boundary_conditions(bc.node_id, restraints)
    
    def _create_damping_matrix(self, K: csr_matrix, M: csr_matrix,
                             damping_ratio: float) -> csr_matrix:
        """Create Rayleigh damping matrix"""
        # Simplified Rayleigh damping: C = alpha*M + beta*K
        # For 5% damping in first two modes (approximate)
        alpha = 0.1  # Mass proportional damping
        beta = 0.001  # Stiffness proportional damping
        
        C = alpha * M + beta * K
        return C
    
    def _solve_dynamic_equation(self, M: csr_matrix, C: csr_matrix, K: csr_matrix,
                              time_points: np.ndarray, ground_acceleration: np.ndarray,
                              dof_manager: DOFManager) -> Dict[str, np.ndarray]:
        """Solve dynamic equation using Newmark method"""
        dt = time_points[1] - time_points[0]  # Assume uniform time step
        n_steps = len(time_points)
        n_dofs = M.shape[0]
        
        # Newmark parameters
        gamma = 0.5
        beta = 0.25
        
        # Initialize response arrays
        displacement = np.zeros((n_dofs, n_steps))
        velocity = np.zeros((n_dofs, n_steps))
        acceleration = np.zeros((n_dofs, n_steps))
        
        # Effective stiffness matrix
        K_eff = K + gamma/(beta*dt) * C + 1/(beta*dt**2) * M
        
        # Time stepping
        for i in range(1, n_steps):
            # External force (ground motion)
            F_ext = self._calculate_ground_motion_force(
                M, ground_acceleration[i], dof_manager
            )
            
            # Effective force
            F_eff = (F_ext + 
                    M @ (1/(beta*dt**2) * displacement[:, i-1] + 
                         1/(beta*dt) * velocity[:, i-1] + 
                         (1/(2*beta) - 1) * acceleration[:, i-1]) +
                    C @ (gamma/(beta*dt) * displacement[:, i-1] + 
                         (gamma/beta - 1) * velocity[:, i-1] + 
                         dt/2 * (gamma/beta - 2) * acceleration[:, i-1]))
            
            # Solve for displacement
            displacement[:, i] = spsolve(K_eff, F_eff)
            
            # Update velocity and acceleration
            acceleration[:, i] = (1/(beta*dt**2) * (displacement[:, i] - displacement[:, i-1]) -
                                1/(beta*dt) * velocity[:, i-1] -
                                (1/(2*beta) - 1) * acceleration[:, i-1])
            
            velocity[:, i] = (velocity[:, i-1] + 
                            dt * ((1-gamma) * acceleration[:, i-1] + 
                                  gamma * acceleration[:, i]))
        
        return {
            'displacement': displacement,
            'velocity': velocity,
            'acceleration': acceleration
        }
    
    def _calculate_ground_motion_force(self, M: csr_matrix, ground_accel: float,
                                     dof_manager: DOFManager) -> np.ndarray:
        """Calculate force vector due to ground motion"""
        n_dofs = M.shape[0]
        influence_vector = np.zeros(n_dofs)
        
        # Apply ground acceleration to all translational DOFs in Z direction
        for node_id, node_dofs in dof_manager.node_dof_map.items():
            if len(node_dofs) > 2:  # Has Z translation DOF
                z_dof = node_dofs[2]
                if z_dof < n_dofs:
                    influence_vector[z_dof] = 1.0
        
        return -M @ influence_vector * ground_accel


class DynamicSolver:
    """Main dynamic analysis solver"""
    
    def __init__(self):
        self.modal_analysis = ModalAnalysis()
        self.response_spectrum_analysis = ResponseSpectrumAnalysis()
        self.time_history_analysis = TimeHistoryAnalysis()
    
    def run_analysis(self, analysis_type: str, analysis_case: AnalysisCase,
                    nodes: List[Node], elements: List[Element],
                    materials: Dict[uuid.UUID, Any], sections: Dict[uuid.UUID, Any],
                    boundary_conditions: List[Any], **kwargs) -> Dict[str, Any]:
        """Run dynamic analysis based on type"""
        if analysis_type == 'modal':
            return self.modal_analysis.run_modal_analysis(
                analysis_case, nodes, elements, materials, sections,
                boundary_conditions, kwargs.get('num_modes', 10)
            )
        elif analysis_type == 'response_spectrum':
            return self.response_spectrum_analysis.run_response_spectrum_analysis(
                analysis_case, nodes, elements, materials, sections,
                boundary_conditions, kwargs['response_spectrum']
            )
        elif analysis_type == 'time_history':
            return self.time_history_analysis.run_time_history_analysis(
                analysis_case, nodes, elements, materials, sections,
                boundary_conditions, kwargs['time_history']
            )
        else:
            raise AnalysisError(f"Unsupported dynamic analysis type: {analysis_type}")