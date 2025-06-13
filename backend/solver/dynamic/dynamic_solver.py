"""
Dynamic analysis solver for structural systems
"""

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh, spsolve
from scipy.integrate import solve_ivp
from typing import Dict, List, Tuple, Optional
import logging

from ..linear.linear_solver import LinearSolver
from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase
from ...core.modeling.boundary_conditions import BoundaryCondition

logger = logging.getLogger(__name__)


class DynamicSolver:
    """
    Main dynamic analysis solver for modal, response spectrum, and time history analysis
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.linear_solver = LinearSolver(model)
        self.mass_matrix = None
        self.stiffness_matrix = None
        self.damping_matrix = None
        self.modes = None
        self.frequencies = None
        self.modal_participation_factors = None
        
    def solve_modal_analysis(self, 
                           boundary_conditions: List[BoundaryCondition],
                           num_modes: int = 10,
                           frequency_range: Tuple[float, float] = None) -> Dict:
        """
        Perform modal analysis to find natural frequencies and mode shapes
        """
        logger.info(f"Starting modal analysis for {num_modes} modes")
        
        # Assemble mass and stiffness matrices
        self._assemble_system_matrices(boundary_conditions)
        
        # Solve generalized eigenvalue problem: K*phi = lambda*M*phi
        try:
            if frequency_range:
                # Find modes in specific frequency range
                sigma = (2 * np.pi * frequency_range[0])**2  # Convert Hz to rad²/s²
                eigenvalues, eigenvectors = eigsh(
                    self.stiffness_matrix, 
                    M=self.mass_matrix,
                    k=num_modes,
                    sigma=sigma,
                    which='LM'
                )
            else:
                # Find lowest modes
                eigenvalues, eigenvectors = eigsh(
                    self.stiffness_matrix,
                    M=self.mass_matrix, 
                    k=num_modes,
                    which='SM'
                )
            
            # Sort by frequency
            sort_indices = np.argsort(eigenvalues)
            eigenvalues = eigenvalues[sort_indices]
            eigenvectors = eigenvectors[:, sort_indices]
            
            # Calculate frequencies (Hz)
            frequencies = np.sqrt(np.abs(eigenvalues)) / (2 * np.pi)
            
            # Calculate periods (seconds)
            periods = 1.0 / frequencies
            
            # Normalize mode shapes
            normalized_modes = self._normalize_mode_shapes(eigenvectors)
            
            # Calculate modal participation factors
            participation_factors = self._calculate_modal_participation_factors(normalized_modes)
            
            # Calculate effective modal masses
            effective_masses = self._calculate_effective_modal_masses(
                normalized_modes, participation_factors
            )
            
            # Store results
            self.modes = normalized_modes
            self.frequencies = frequencies
            self.modal_participation_factors = participation_factors
            
            results = {
                "num_modes": num_modes,
                "frequencies": frequencies.tolist(),
                "periods": periods.tolist(),
                "mode_shapes": self._format_mode_shapes(normalized_modes),
                "participation_factors": participation_factors,
                "effective_masses": effective_masses,
                "modal_analysis_summary": self._generate_modal_summary(
                    frequencies, periods, effective_masses
                )
            }
            
            logger.info(f"Modal analysis completed successfully")
            logger.info(f"First 3 frequencies: {frequencies[:3]} Hz")
            
            return results
            
        except Exception as e:
            logger.error(f"Modal analysis failed: {e}")
            raise
    
    def solve_response_spectrum_analysis(self,
                                       boundary_conditions: List[BoundaryCondition],
                                       response_spectrum: Dict,
                                       damping_ratio: float = 0.05,
                                       combination_method: str = "CQC") -> Dict:
        """
        Perform response spectrum analysis
        """
        logger.info(f"Starting response spectrum analysis with {combination_method} combination")
        
        # Ensure modal analysis is performed first
        if self.modes is None:
            modal_results = self.solve_modal_analysis(boundary_conditions)
        
        # Extract response spectrum data
        periods = np.array(response_spectrum["periods"])
        accelerations = np.array(response_spectrum["accelerations"])
        
        # Calculate modal responses
        modal_responses = []
        
        for i, freq in enumerate(self.frequencies):
            period = 1.0 / freq
            
            # Interpolate spectral acceleration for this period
            Sa = np.interp(period, periods, accelerations)
            
            # Calculate modal response
            participation_factor = self.modal_participation_factors[i]
            modal_mass = self._get_modal_mass(i)
            
            # Modal base shear
            modal_base_shear = participation_factor * modal_mass * Sa
            
            # Modal displacements
            modal_displacement = (Sa / (2 * np.pi * freq)**2) * self.modes[:, i]
            
            modal_responses.append({
                "mode": i + 1,
                "period": period,
                "frequency": freq,
                "spectral_acceleration": Sa,
                "participation_factor": participation_factor,
                "modal_mass": modal_mass,
                "base_shear": modal_base_shear,
                "max_displacement": np.max(np.abs(modal_displacement))
            })
        
        # Combine modal responses
        combined_response = self._combine_modal_responses(
            modal_responses, combination_method, damping_ratio
        )
        
        results = {
            "response_spectrum": response_spectrum,
            "damping_ratio": damping_ratio,
            "combination_method": combination_method,
            "modal_responses": modal_responses,
            "combined_response": combined_response,
            "total_base_shear": combined_response["base_shear"],
            "max_displacement": combined_response["displacement"]
        }
        
        logger.info(f"Response spectrum analysis completed")
        logger.info(f"Total base shear: {combined_response['base_shear']:.2f}")
        
        return results
    
    def solve_time_history_analysis(self,
                                   boundary_conditions: List[BoundaryCondition],
                                   ground_motion: Dict,
                                   damping_ratio: float = 0.05,
                                   integration_method: str = "newmark") -> Dict:
        """
        Perform time history analysis
        """
        logger.info(f"Starting time history analysis with {integration_method} integration")
        
        # Assemble system matrices
        self._assemble_system_matrices(boundary_conditions)
        
        # Assemble damping matrix
        self._assemble_damping_matrix(damping_ratio)
        
        # Extract ground motion data
        time_points = np.array(ground_motion["time"])
        acceleration = np.array(ground_motion["acceleration"])
        dt = time_points[1] - time_points[0]
        
        # Initial conditions
        n_dof = self.stiffness_matrix.shape[0]
        u0 = np.zeros(n_dof)  # Initial displacement
        v0 = np.zeros(n_dof)  # Initial velocity
        
        # Solve equation of motion: M*u'' + C*u' + K*u = -M*r*ag(t)
        if integration_method == "newmark":
            response = self._newmark_integration(
                time_points, acceleration, u0, v0, dt
            )
        elif integration_method == "modal":
            response = self._modal_time_history(
                time_points, acceleration, u0, v0, damping_ratio
            )
        else:
            raise ValueError(f"Unknown integration method: {integration_method}")
        
        # Calculate response quantities
        max_displacement = np.max(np.abs(response["displacement"]), axis=0)
        max_velocity = np.max(np.abs(response["velocity"]), axis=0)
        max_acceleration = np.max(np.abs(response["acceleration"]), axis=0)
        
        # Calculate base shear time history
        base_shear_history = self._calculate_base_shear_history(response)
        
        results = {
            "ground_motion": ground_motion,
            "integration_method": integration_method,
            "damping_ratio": damping_ratio,
            "time_points": time_points.tolist(),
            "displacement_history": response["displacement"].tolist(),
            "velocity_history": response["velocity"].tolist(),
            "acceleration_history": response["acceleration"].tolist(),
            "base_shear_history": base_shear_history.tolist(),
            "max_displacement": max_displacement.tolist(),
            "max_velocity": max_velocity.tolist(),
            "max_acceleration": max_acceleration.tolist(),
            "max_base_shear": np.max(np.abs(base_shear_history))
        }
        
        logger.info(f"Time history analysis completed")
        logger.info(f"Max base shear: {np.max(np.abs(base_shear_history)):.2f}")
        
        return results
    
    def _assemble_system_matrices(self, boundary_conditions: List[BoundaryCondition]):
        """
        Assemble mass and stiffness matrices
        """
        # Assemble stiffness matrix
        self.stiffness_matrix = self.linear_solver.assemble_global_stiffness_matrix()
        
        # Assemble mass matrix
        self.mass_matrix = self._assemble_mass_matrix()
        
        # Apply boundary conditions
        self._apply_boundary_conditions_dynamic(boundary_conditions)
    
    def _assemble_mass_matrix(self) -> csc_matrix:
        """
        Assemble global mass matrix
        """
        total_dofs = len(self.model.nodes) * 6
        M_global = np.zeros((total_dofs, total_dofs))
        
        for element in self.model.elements:
            # Get element mass matrix
            M_element = self._get_element_mass_matrix(element)
            
            # Get DOF mapping
            dof_map = self.linear_solver._get_element_dof_mapping(element)
            
            # Add to global matrix
            for i, global_i in enumerate(dof_map):
                for j, global_j in enumerate(dof_map):
                    M_global[global_i, global_j] += M_element[i, j]
        
        return csc_matrix(M_global)
    
    def _get_element_mass_matrix(self, element) -> np.ndarray:
        """
        Calculate element mass matrix
        """
        if element.element_type == "beam":
            return self._beam_mass_matrix(element)
        elif element.element_type == "truss":
            return self._truss_mass_matrix(element)
        else:
            # Default lumped mass
            return self._lumped_mass_matrix(element)
    
    def _beam_mass_matrix(self, element) -> np.ndarray:
        """
        Consistent mass matrix for beam element
        """
        # Get element properties
        rho = element.material.density  # kg/m³
        A = element.section.area  # m²
        L = element.length  # m
        
        # Mass per unit length
        m = rho * A
        
        # Consistent mass matrix for 3D beam (12x12)
        M = np.zeros((12, 12))
        
        # Translational mass terms
        M[0, 0] = M[6, 6] = m * L / 3
        M[0, 6] = M[6, 0] = m * L / 6
        
        M[1, 1] = M[7, 7] = 13 * m * L / 35
        M[1, 7] = M[7, 1] = 9 * m * L / 70
        M[1, 5] = M[5, 1] = 11 * m * L**2 / 210
        M[1, 11] = M[11, 1] = -13 * m * L**2 / 420
        M[7, 5] = M[5, 7] = 13 * m * L**2 / 420
        M[7, 11] = M[11, 7] = -11 * m * L**2 / 210
        
        M[2, 2] = M[8, 8] = 13 * m * L / 35
        M[2, 8] = M[8, 2] = 9 * m * L / 70
        M[2, 4] = M[4, 2] = -11 * m * L**2 / 210
        M[2, 10] = M[10, 2] = 13 * m * L**2 / 420
        M[8, 4] = M[4, 8] = -13 * m * L**2 / 420
        M[8, 10] = M[10, 8] = 11 * m * L**2 / 210
        
        # Rotational mass terms (simplified)
        I = element.section.moment_of_inertia_x  # m⁴
        J = getattr(element.section, 'torsional_constant', I)  # m⁴
        
        M[3, 3] = M[9, 9] = rho * J * L / 3
        M[3, 9] = M[9, 3] = rho * J * L / 6
        
        M[4, 4] = M[10, 10] = m * L**3 / 105
        M[4, 10] = M[10, 4] = -m * L**3 / 140
        
        M[5, 5] = M[11, 11] = m * L**3 / 105
        M[5, 11] = M[11, 5] = -m * L**3 / 140
        
        return M
    
    def _truss_mass_matrix(self, element) -> np.ndarray:
        """
        Mass matrix for truss element
        """
        rho = element.material.density
        A = element.section.area
        L = element.length
        
        # Mass per unit length
        m = rho * A
        
        # Lumped mass matrix for truss (6x6)
        M = np.zeros((6, 6))
        
        # Equal mass at each node
        mass_per_node = m * L / 2
        
        M[0, 0] = M[1, 1] = M[2, 2] = mass_per_node
        M[3, 3] = M[4, 4] = M[5, 5] = mass_per_node
        
        return M
    
    def _lumped_mass_matrix(self, element) -> np.ndarray:
        """
        Lumped mass matrix for general element
        """
        rho = element.material.density
        A = element.section.area
        L = element.length
        
        total_mass = rho * A * L
        mass_per_node = total_mass / 2
        
        # Lumped mass matrix
        M = np.zeros((12, 12))
        
        # Translational masses only
        for i in [0, 1, 2]:  # First node
            M[i, i] = mass_per_node
        for i in [6, 7, 8]:  # Second node
            M[i, i] = mass_per_node
        
        return M
    
    def _assemble_damping_matrix(self, damping_ratio: float):
        """
        Assemble damping matrix using Rayleigh damping
        """
        if self.frequencies is None:
            # Use approximate frequencies for Rayleigh damping
            omega1 = 2 * np.pi * 1.0  # 1 Hz
            omega2 = 2 * np.pi * 10.0  # 10 Hz
        else:
            omega1 = 2 * np.pi * self.frequencies[0]
            omega2 = 2 * np.pi * self.frequencies[min(2, len(self.frequencies)-1)]
        
        # Rayleigh damping: C = a0*M + a1*K
        a0 = 2 * damping_ratio * omega1 * omega2 / (omega1 + omega2)
        a1 = 2 * damping_ratio / (omega1 + omega2)
        
        self.damping_matrix = a0 * self.mass_matrix + a1 * self.stiffness_matrix
    
    def _apply_boundary_conditions_dynamic(self, boundary_conditions: List[BoundaryCondition]):
        """
        Apply boundary conditions to dynamic system matrices
        """
        # Convert to dense for modification
        K_dense = self.stiffness_matrix.toarray()
        M_dense = self.mass_matrix.toarray()
        
        # Apply constraints using penalty method
        for bc in boundary_conditions:
            node_index = self.linear_solver._get_node_index(bc.node_id)
            dof_start = node_index * 6
            
            if bc.support_type == "fixed":
                for i in range(6):
                    dof = dof_start + i
                    # Large stiffness, small mass
                    K_dense[dof, dof] += 1e12
                    M_dense[dof, dof] = 1e-12
            elif bc.support_type == "pinned":
                for i in range(3):  # Fix translations only
                    dof = dof_start + i
                    K_dense[dof, dof] += 1e12
                    M_dense[dof, dof] = 1e-12
        
        self.stiffness_matrix = csc_matrix(K_dense)
        self.mass_matrix = csc_matrix(M_dense)
    
    def _normalize_mode_shapes(self, eigenvectors: np.ndarray) -> np.ndarray:
        """
        Normalize mode shapes with respect to mass matrix
        """
        normalized_modes = np.zeros_like(eigenvectors)
        
        for i in range(eigenvectors.shape[1]):
            mode = eigenvectors[:, i]
            # Mass normalize: phi^T * M * phi = 1
            modal_mass = mode.T @ self.mass_matrix @ mode
            normalized_modes[:, i] = mode / np.sqrt(modal_mass)
        
        return normalized_modes
    
    def _calculate_modal_participation_factors(self, modes: np.ndarray) -> List[float]:
        """
        Calculate modal participation factors
        """
        participation_factors = []
        
        # Influence vector (unit ground acceleration in X direction)
        n_nodes = len(self.model.nodes)
        r = np.zeros(n_nodes * 6)
        for i in range(n_nodes):
            r[i * 6] = 1.0  # X-direction
        
        for i in range(modes.shape[1]):
            mode = modes[:, i]
            # Participation factor: Gamma = phi^T * M * r / (phi^T * M * phi)
            numerator = mode.T @ self.mass_matrix @ r
            denominator = mode.T @ self.mass_matrix @ mode
            gamma = numerator / denominator if denominator > 0 else 0.0
            participation_factors.append(gamma)
        
        return participation_factors
    
    def _calculate_effective_modal_masses(self, 
                                        modes: np.ndarray,
                                        participation_factors: List[float]) -> Dict:
        """
        Calculate effective modal masses
        """
        total_mass = np.sum(self.mass_matrix.diagonal())
        effective_masses = []
        
        for i, gamma in enumerate(participation_factors):
            mode = modes[:, i]
            modal_mass = mode.T @ self.mass_matrix @ mode
            effective_mass = gamma**2 * modal_mass
            effective_masses.append(effective_mass)
        
        cumulative_mass = np.cumsum(effective_masses)
        mass_participation = cumulative_mass / total_mass * 100
        
        return {
            "effective_masses": effective_masses,
            "cumulative_masses": cumulative_mass.tolist(),
            "mass_participation_percent": mass_participation.tolist(),
            "total_mass": total_mass
        }
    
    def _format_mode_shapes(self, modes: np.ndarray) -> List[Dict]:
        """
        Format mode shapes for output
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
    
    def _generate_modal_summary(self, 
                               frequencies: np.ndarray,
                               periods: np.ndarray,
                               effective_masses: Dict) -> Dict:
        """
        Generate modal analysis summary
        """
        return {
            "fundamental_frequency": frequencies[0],
            "fundamental_period": periods[0],
            "frequency_range": {
                "min": np.min(frequencies),
                "max": np.max(frequencies)
            },
            "mass_participation_90_percent": np.where(
                np.array(effective_masses["mass_participation_percent"]) >= 90.0
            )[0][0] + 1 if len(np.where(
                np.array(effective_masses["mass_participation_percent"]) >= 90.0
            )[0]) > 0 else len(frequencies)
        }
    
    def _combine_modal_responses(self, 
                               modal_responses: List[Dict],
                               method: str,
                               damping_ratio: float) -> Dict:
        """
        Combine modal responses using specified method
        """
        if method == "SRSS":
            # Square Root of Sum of Squares
            base_shear = np.sqrt(sum(r["base_shear"]**2 for r in modal_responses))
            displacement = np.sqrt(sum(r["max_displacement"]**2 for r in modal_responses))
        
        elif method == "CQC":
            # Complete Quadratic Combination
            base_shear = self._cqc_combination([r["base_shear"] for r in modal_responses], damping_ratio)
            displacement = self._cqc_combination([r["max_displacement"] for r in modal_responses], damping_ratio)
        
        else:
            raise ValueError(f"Unknown combination method: {method}")
        
        return {
            "base_shear": base_shear,
            "displacement": displacement,
            "method": method
        }
    
    def _cqc_combination(self, responses: List[float], damping_ratio: float) -> float:
        """
        Complete Quadratic Combination of modal responses
        """
        n_modes = len(responses)
        combined = 0.0
        
        for i in range(n_modes):
            for j in range(n_modes):
                if i == j:
                    correlation = 1.0
                else:
                    # Cross-correlation coefficient
                    freq_ratio = self.frequencies[j] / self.frequencies[i]
                    r = freq_ratio
                    xi = damping_ratio
                    
                    correlation = (8 * xi**2 * (1 + r) * r**(3/2)) / (
                        (1 - r**2)**2 + 4 * xi**2 * r * (1 + r)**2
                    )
                
                combined += responses[i] * responses[j] * correlation
        
        return np.sqrt(abs(combined))
    
    def _get_modal_mass(self, mode_index: int) -> float:
        """
        Get modal mass for specified mode
        """
        if self.modes is None:
            return 0.0
        
        mode = self.modes[:, mode_index]
        return mode.T @ self.mass_matrix @ mode
    
    def _newmark_integration(self, 
                           time_points: np.ndarray,
                           acceleration: np.ndarray,
                           u0: np.ndarray,
                           v0: np.ndarray,
                           dt: float) -> Dict:
        """
        Newmark-beta time integration
        """
        # Newmark parameters
        beta = 0.25  # Average acceleration
        gamma = 0.5
        
        n_steps = len(time_points)
        n_dof = len(u0)
        
        # Initialize response arrays
        u = np.zeros((n_steps, n_dof))
        v = np.zeros((n_steps, n_dof))
        a = np.zeros((n_steps, n_dof))
        
        # Initial conditions
        u[0] = u0
        v[0] = v0
        
        # Calculate initial acceleration
        # M*a0 = F0 - C*v0 - K*u0
        F0 = -self.mass_matrix @ np.ones(n_dof) * acceleration[0]  # Ground motion force
        a[0] = spsolve(self.mass_matrix, F0 - self.damping_matrix @ v0 - self.stiffness_matrix @ u0)
        
        # Integration constants
        a1 = 1.0 / (beta * dt**2)
        a2 = 1.0 / (beta * dt)
        a3 = (1.0 - 2*beta) / (2*beta)
        a4 = gamma / (beta * dt)
        a5 = 1.0 - gamma/beta
        a6 = dt * (1.0 - gamma/(2*beta))
        
        # Effective stiffness matrix
        K_eff = self.stiffness_matrix + a1 * self.mass_matrix + a4 * self.damping_matrix
        
        # Time stepping
        for i in range(1, n_steps):
            # External force
            F_ext = -self.mass_matrix @ np.ones(n_dof) * acceleration[i]
            
            # Effective force
            F_eff = (F_ext + 
                    self.mass_matrix @ (a1*u[i-1] + a2*v[i-1] + a3*a[i-1]) +
                    self.damping_matrix @ (a4*u[i-1] + a5*v[i-1] + a6*a[i-1]))
            
            # Solve for displacement
            u[i] = spsolve(K_eff, F_eff)
            
            # Calculate velocity and acceleration
            v[i] = a4*(u[i] - u[i-1]) - a5*v[i-1] - a6*a[i-1]
            a[i] = a1*(u[i] - u[i-1]) - a2*v[i-1] - a3*a[i-1]
        
        return {
            "displacement": u,
            "velocity": v,
            "acceleration": a
        }
    
    def _modal_time_history(self,
                          time_points: np.ndarray,
                          acceleration: np.ndarray,
                          u0: np.ndarray,
                          v0: np.ndarray,
                          damping_ratio: float) -> Dict:
        """
        Modal time history analysis
        """
        if self.modes is None:
            raise ValueError("Modal analysis must be performed first")
        
        n_steps = len(time_points)
        n_dof = len(u0)
        n_modes = self.modes.shape[1]
        
        # Transform to modal coordinates
        q0 = self.modes.T @ self.mass_matrix @ u0  # Modal displacements
        qd0 = self.modes.T @ self.mass_matrix @ v0  # Modal velocities
        
        # Modal responses
        q = np.zeros((n_steps, n_modes))
        qd = np.zeros((n_steps, n_modes))
        qdd = np.zeros((n_steps, n_modes))
        
        # Solve each modal equation
        for i in range(n_modes):
            omega = 2 * np.pi * self.frequencies[i]
            gamma = self.modal_participation_factors[i]
            
            # Modal equation: qdd + 2*xi*omega*qd + omega^2*q = -gamma*ag(t)
            def modal_equation(t, y):
                q_modal, qd_modal = y
                ag = np.interp(t, time_points, acceleration)
                qdd_modal = -2*damping_ratio*omega*qd_modal - omega**2*q_modal - gamma*ag
                return [qd_modal, qdd_modal]
            
            # Solve modal equation
            sol = solve_ivp(
                modal_equation,
                [time_points[0], time_points[-1]],
                [q0[i], qd0[i]],
                t_eval=time_points,
                method='RK45'
            )
            
            q[:, i] = sol.y[0]
            qd[:, i] = sol.y[1]
            
            # Calculate modal acceleration
            for j in range(n_steps):
                ag = acceleration[j]
                qdd[j, i] = -2*damping_ratio*omega*qd[j, i] - omega**2*q[j, i] - gamma*ag
        
        # Transform back to physical coordinates
        u = np.zeros((n_steps, n_dof))
        v = np.zeros((n_steps, n_dof))
        a = np.zeros((n_steps, n_dof))
        
        for i in range(n_steps):
            u[i] = self.modes @ q[i]
            v[i] = self.modes @ qd[i]
            a[i] = self.modes @ qdd[i]
        
        return {
            "displacement": u,
            "velocity": v,
            "acceleration": a
        }
    
    def _calculate_base_shear_history(self, response: Dict) -> np.ndarray:
        """
        Calculate base shear time history
        """
        n_steps = response["acceleration"].shape[0]
        base_shear = np.zeros(n_steps)
        
        for i in range(n_steps):
            # Base shear = sum of inertial forces
            inertial_forces = self.mass_matrix @ response["acceleration"][i]
            
            # Sum forces in X-direction (assuming first DOF of each node is X)
            n_nodes = len(self.model.nodes)
            for j in range(n_nodes):
                base_shear[i] += inertial_forces[j * 6]  # X-direction force
        
        return base_shear