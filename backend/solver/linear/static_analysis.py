"""
Linear static analysis implementation
"""

import numpy as np
from typing import Dict, List, Optional
import logging

from .linear_solver import LinearSolver
from ...core.modeling.model import StructuralModel
from ...core.modeling.loads import LoadCase, LoadCombination
from ...core.modeling.boundary_conditions import BoundaryCondition

logger = logging.getLogger(__name__)


class LinearStaticAnalysis:
    """
    Linear static analysis manager
    """
    
    def __init__(self, model: StructuralModel):
        self.model = model
        self.solver = LinearSolver(model)
        self.results = {}
        
    def run_analysis(self, 
                    load_cases: List[LoadCase],
                    boundary_conditions: List[BoundaryCondition],
                    load_combinations: Optional[List[LoadCombination]] = None) -> Dict:
        """
        Run linear static analysis for given load cases
        """
        logger.info("Starting linear static analysis")
        
        # Validate model
        self._validate_model()
        
        # Assemble global stiffness matrix (same for all load cases)
        self.solver.assemble_global_stiffness_matrix()
        
        # Analyze each load case
        for load_case in load_cases:
            logger.info(f"Analyzing load case: {load_case.name}")
            
            # Assemble load vector for this case
            self.solver.assemble_global_load_vector(load_case)
            
            # Apply boundary conditions
            self.solver.apply_boundary_conditions(boundary_conditions)
            
            # Solve
            case_results = self.solver.solve()
            
            # Store results
            self.results[load_case.name] = case_results
        
        # Process load combinations if provided
        if load_combinations:
            self._process_load_combinations(load_combinations)
        
        logger.info("Linear static analysis completed")
        return self.results
    
    def _validate_model(self):
        """
        Validate structural model before analysis
        """
        if not self.model.nodes:
            raise ValueError("Model has no nodes")
        
        if not self.model.elements:
            raise ValueError("Model has no elements")
        
        # Check for unconnected nodes
        connected_nodes = set()
        for element in self.model.elements:
            connected_nodes.add(element.start_node_id)
            connected_nodes.add(element.end_node_id)
        
        all_nodes = {node.id for node in self.model.nodes}
        unconnected = all_nodes - connected_nodes
        
        if unconnected:
            logger.warning(f"Unconnected nodes found: {unconnected}")
        
        # Check for missing materials and sections
        for element in self.model.elements:
            if not element.material:
                raise ValueError(f"Element {element.id} has no material assigned")
            if not element.section:
                raise ValueError(f"Element {element.id} has no section assigned")
    
    def _process_load_combinations(self, load_combinations: List[LoadCombination]):
        """
        Process load combinations using superposition
        """
        logger.info("Processing load combinations")
        
        for combination in load_combinations:
            logger.info(f"Processing combination: {combination.name}")
            
            # Initialize combined results
            combined_displacements = {}
            combined_reactions = {}
            combined_element_forces = {}
            
            # Get first load case to initialize structure
            first_case = combination.load_factors[0]
            first_case_name = first_case["load_case"]
            
            if first_case_name not in self.results:
                logger.warning(f"Load case {first_case_name} not found in results")
                continue
            
            # Initialize with first case
            for node_id in self.results[first_case_name]["displacements"]:
                combined_displacements[node_id] = {
                    "ux": 0.0, "uy": 0.0, "uz": 0.0,
                    "rx": 0.0, "ry": 0.0, "rz": 0.0
                }
                combined_reactions[node_id] = {
                    "fx": 0.0, "fy": 0.0, "fz": 0.0,
                    "mx": 0.0, "my": 0.0, "mz": 0.0
                }
            
            for element_id in self.results[first_case_name]["element_forces"]:
                combined_element_forces[element_id] = {
                    "axial": 0.0, "shear_y": 0.0, "shear_z": 0.0,
                    "torsion": 0.0, "moment_y": 0.0, "moment_z": 0.0
                }
            
            # Combine results using load factors
            for load_factor_data in combination.load_factors:
                case_name = load_factor_data["load_case"]
                factor = load_factor_data["factor"]
                
                if case_name not in self.results:
                    logger.warning(f"Load case {case_name} not found in results")
                    continue
                
                case_results = self.results[case_name]
                
                # Combine displacements
                for node_id, displacements in case_results["displacements"].items():
                    for dof, value in displacements.items():
                        combined_displacements[node_id][dof] += factor * value
                
                # Combine reactions
                for node_id, reactions in case_results["reactions"].items():
                    for dof, value in reactions.items():
                        combined_reactions[node_id][dof] += factor * value
                
                # Combine element forces
                for element_id, forces in case_results["element_forces"].items():
                    for force_type, value in forces.items():
                        combined_element_forces[element_id][force_type] += factor * value
            
            # Store combination results
            self.results[combination.name] = {
                "displacements": combined_displacements,
                "reactions": combined_reactions,
                "element_forces": combined_element_forces,
                "combination_type": "linear"
            }
    
    def get_max_displacement(self, load_case: str = None) -> Dict:
        """
        Get maximum displacements for a load case or all cases
        """
        if load_case:
            if load_case not in self.results:
                raise ValueError(f"Load case {load_case} not found")
            cases_to_check = [load_case]
        else:
            cases_to_check = list(self.results.keys())
        
        max_displacements = {
            "ux": {"value": 0.0, "node": None, "case": None},
            "uy": {"value": 0.0, "node": None, "case": None},
            "uz": {"value": 0.0, "node": None, "case": None},
            "total": {"value": 0.0, "node": None, "case": None}
        }
        
        for case_name in cases_to_check:
            displacements = self.results[case_name]["displacements"]
            
            for node_id, node_displacements in displacements.items():
                # Check individual components
                for dof in ["ux", "uy", "uz"]:
                    abs_value = abs(node_displacements[dof])
                    if abs_value > abs(max_displacements[dof]["value"]):
                        max_displacements[dof] = {
                            "value": node_displacements[dof],
                            "node": node_id,
                            "case": case_name
                        }
                
                # Check total displacement
                total_disp = np.sqrt(
                    node_displacements["ux"]**2 + 
                    node_displacements["uy"]**2 + 
                    node_displacements["uz"]**2
                )
                
                if total_disp > max_displacements["total"]["value"]:
                    max_displacements["total"] = {
                        "value": total_disp,
                        "node": node_id,
                        "case": case_name
                    }
        
        return max_displacements
    
    def get_max_element_forces(self, load_case: str = None) -> Dict:
        """
        Get maximum element forces for a load case or all cases
        """
        if load_case:
            if load_case not in self.results:
                raise ValueError(f"Load case {load_case} not found")
            cases_to_check = [load_case]
        else:
            cases_to_check = list(self.results.keys())
        
        max_forces = {
            "axial": {"value": 0.0, "element": None, "case": None},
            "shear_y": {"value": 0.0, "element": None, "case": None},
            "shear_z": {"value": 0.0, "element": None, "case": None},
            "torsion": {"value": 0.0, "element": None, "case": None},
            "moment_y": {"value": 0.0, "element": None, "case": None},
            "moment_z": {"value": 0.0, "element": None, "case": None}
        }
        
        for case_name in cases_to_check:
            element_forces = self.results[case_name]["element_forces"]
            
            for element_id, forces in element_forces.items():
                for force_type, value in forces.items():
                    abs_value = abs(value)
                    if abs_value > abs(max_forces[force_type]["value"]):
                        max_forces[force_type] = {
                            "value": value,
                            "element": element_id,
                            "case": case_name
                        }
        
        return max_forces
    
    def export_results(self, format: str = "json") -> Dict:
        """
        Export analysis results in specified format
        """
        if format == "json":
            return self.results
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_deformed_shape(self, load_case: str, scale_factor: float = 1.0) -> Dict:
        """
        Get deformed node coordinates for visualization
        """
        if load_case not in self.results:
            raise ValueError(f"Load case {load_case} not found")
        
        displacements = self.results[load_case]["displacements"]
        deformed_nodes = {}
        
        for node in self.model.nodes:
            node_displacements = displacements[node.id]
            
            deformed_nodes[node.id] = {
                "x": node.x + scale_factor * node_displacements["ux"],
                "y": node.y + scale_factor * node_displacements["uy"],
                "z": node.z + scale_factor * node_displacements["uz"],
                "original_x": node.x,
                "original_y": node.y,
                "original_z": node.z
            }
        
        return deformed_nodes