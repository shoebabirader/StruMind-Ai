"""
Foundation design module for various foundation types
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from ...core.modeling.elements import Element
from ...core.modeling.materials import ConcreteMaterial, SteelMaterial

logger = logging.getLogger(__name__)


class FoundationDesign:
    """
    General foundation design class
    """
    
    def __init__(self, design_code: str = "IS456"):
        self.design_code = design_code
        self.gamma_c = 1.5  # Partial safety factor for concrete
        self.gamma_s = 1.15  # Partial safety factor for steel
        self.gamma_soil = 1.25  # Partial safety factor for soil
        
    def design_isolated_footing(self,
                               loads: Dict,
                               soil_properties: Dict,
                               concrete: ConcreteMaterial,
                               steel: SteelMaterial,
                               column_size: Tuple[float, float]) -> Dict:
        """
        Design isolated square/rectangular footing
        """
        logger.info("Designing isolated footing")
        
        # Extract loads
        P = loads.get('axial', 0)  # kN (compression positive)
        Mx = loads.get('moment_x', 0)  # kN-m
        My = loads.get('moment_y', 0)  # kN-m
        Vx = loads.get('shear_x', 0)  # kN
        Vy = loads.get('shear_y', 0)  # kN
        
        # Soil properties
        qa = soil_properties.get('allowable_bearing_pressure', 150)  # kN/m²
        gamma_soil = soil_properties.get('unit_weight', 18)  # kN/m³
        
        # Column dimensions
        col_width, col_depth = column_size  # mm
        
        results = {
            "foundation_type": "isolated_footing",
            "design_code": self.design_code,
            "loads": loads,
            "soil_properties": soil_properties
        }
        
        # Step 1: Size the footing for bearing pressure
        sizing_results = self._size_footing_for_bearing(P, Mx, My, qa, gamma_soil)
        results["sizing"] = sizing_results
        
        # Step 2: Check punching shear
        punching_results = self._check_punching_shear(
            sizing_results, P, col_width, col_depth, concrete
        )
        results["punching_shear"] = punching_results
        
        # Step 3: Check one-way shear
        one_way_shear_results = self._check_one_way_shear(
            sizing_results, P, col_width, col_depth, concrete
        )
        results["one_way_shear"] = one_way_shear_results
        
        # Step 4: Design flexural reinforcement
        flexural_results = self._design_footing_reinforcement(
            sizing_results, P, Mx, My, col_width, col_depth, concrete, steel
        )
        results["flexural_design"] = flexural_results
        
        # Step 5: Check development length
        development_results = self._check_development_length(
            flexural_results, concrete, steel
        )
        results["development_length"] = development_results
        
        # Overall adequacy
        results["adequate"] = self._check_footing_adequacy(results)
        
        return results
    
    def design_combined_footing(self,
                               loads_list: List[Dict],
                               column_positions: List[Tuple[float, float]],
                               soil_properties: Dict,
                               concrete: ConcreteMaterial,
                               steel: SteelMaterial) -> Dict:
        """
        Design combined footing for multiple columns
        """
        logger.info(f"Designing combined footing for {len(loads_list)} columns")
        
        # Calculate resultant loads
        total_P = sum(loads.get('axial', 0) for loads in loads_list)
        total_Mx = sum(loads.get('moment_x', 0) for loads in loads_list)
        total_My = sum(loads.get('moment_y', 0) for loads in loads_list)
        
        # Calculate centroid of loads
        moment_x = sum(loads.get('axial', 0) * pos[0] for loads, pos in zip(loads_list, column_positions))
        moment_y = sum(loads.get('axial', 0) * pos[1] for loads, pos in zip(loads_list, column_positions))
        
        centroid_x = moment_x / total_P if total_P > 0 else 0
        centroid_y = moment_y / total_P if total_P > 0 else 0
        
        # Soil properties
        qa = soil_properties.get('allowable_bearing_pressure', 150)  # kN/m²
        
        results = {
            "foundation_type": "combined_footing",
            "design_code": self.design_code,
            "number_of_columns": len(loads_list),
            "total_loads": {
                "axial": total_P,
                "moment_x": total_Mx,
                "moment_y": total_My
            },
            "load_centroid": {
                "x": centroid_x,
                "y": centroid_y
            }
        }
        
        # Size the footing
        area_required = total_P / qa * self.gamma_soil
        
        # Determine footing dimensions (rectangular)
        column_span = max(pos[0] for pos in column_positions) - min(pos[0] for pos in column_positions)
        length = column_span + 2 * 0.5  # Add 0.5m on each side
        width = area_required / length
        
        # Round up to practical dimensions
        length = math.ceil(length * 2) / 2  # Round to nearest 0.5m
        width = math.ceil(width * 2) / 2
        
        results["dimensions"] = {
            "length": length,
            "width": width,
            "area": length * width,
            "area_required": area_required
        }
        
        # Design as beam spanning between columns
        beam_design = self._design_combined_footing_as_beam(
            results, loads_list, column_positions, concrete, steel
        )
        results["beam_design"] = beam_design
        
        results["adequate"] = True  # Simplified
        
        return results
    
    def design_pile_cap(self,
                       loads: Dict,
                       pile_properties: Dict,
                       concrete: ConcreteMaterial,
                       steel: SteelMaterial,
                       num_piles: int = 4) -> Dict:
        """
        Design pile cap
        """
        logger.info(f"Designing pile cap for {num_piles} piles")
        
        # Extract loads
        P = loads.get('axial', 0)  # kN
        Mx = loads.get('moment_x', 0)  # kN-m
        My = loads.get('moment_y', 0)  # kN-m
        
        # Pile properties
        pile_capacity = pile_properties.get('capacity', 500)  # kN per pile
        pile_diameter = pile_properties.get('diameter', 500)  # mm
        
        results = {
            "foundation_type": "pile_cap",
            "design_code": self.design_code,
            "loads": loads,
            "pile_properties": pile_properties,
            "number_of_piles": num_piles
        }
        
        # Check pile capacity
        pile_load = P / num_piles  # Simplified - assumes equal load distribution
        
        if pile_load > pile_capacity:
            results["pile_capacity_check"] = {
                "adequate": False,
                "pile_load": pile_load,
                "pile_capacity": pile_capacity,
                "utilization": pile_load / pile_capacity
            }
        else:
            results["pile_capacity_check"] = {
                "adequate": True,
                "pile_load": pile_load,
                "pile_capacity": pile_capacity,
                "utilization": pile_load / pile_capacity
            }
        
        # Size pile cap
        pile_spacing = max(3 * pile_diameter / 1000, 1.0)  # Minimum 3D or 1m
        
        if num_piles == 4:
            # Square arrangement
            cap_size = pile_spacing + pile_diameter / 1000 + 0.3  # Add 300mm edge distance
        else:
            # Simplified sizing
            cap_size = math.sqrt(num_piles) * pile_spacing + 0.6
        
        cap_thickness = max(pile_diameter / 1000 * 1.5, 0.6)  # Minimum thickness
        
        results["dimensions"] = {
            "length": cap_size,
            "width": cap_size,
            "thickness": cap_thickness,
            "pile_spacing": pile_spacing
        }
        
        # Check punching shear around column
        punching_results = self._check_pile_cap_punching_shear(
            results, loads, concrete
        )
        results["punching_shear"] = punching_results
        
        # Design flexural reinforcement
        flexural_results = self._design_pile_cap_reinforcement(
            results, loads, concrete, steel
        )
        results["flexural_design"] = flexural_results
        
        results["adequate"] = (
            results["pile_capacity_check"]["adequate"] and
            punching_results.get("adequate", True) and
            flexural_results.get("adequate", True)
        )
        
        return results
    
    def _size_footing_for_bearing(self, P: float, Mx: float, My: float, 
                                 qa: float, gamma_soil: float) -> Dict:
        """
        Size footing based on bearing pressure requirements
        """
        # Service loads (unfactored)
        P_service = P / 1.5  # Assuming load factor of 1.5
        Mx_service = Mx / 1.5
        My_service = My / 1.5
        
        # Initial sizing for concentric load
        area_required = P_service / qa * 1.1  # 10% factor of safety
        
        # Assume square footing initially
        B = math.sqrt(area_required)
        L = B
        
        # Check bearing pressure with moments
        max_iterations = 10
        for iteration in range(max_iterations):
            # Calculate bearing pressures
            q_max, q_min = self._calculate_bearing_pressures(
                P_service, Mx_service, My_service, L, B
            )
            
            # Check if bearing pressure is acceptable
            if q_max <= qa and q_min >= 0:
                break
            
            # Increase size if needed
            if q_max > qa:
                scale_factor = math.sqrt(q_max / qa)
                L *= scale_factor
                B *= scale_factor
            
            # Increase size if tension occurs
            if q_min < 0:
                L *= 1.2
                B *= 1.2
        
        # Round to practical dimensions
        L = math.ceil(L * 4) / 4  # Round to nearest 0.25m
        B = math.ceil(B * 4) / 4
        
        # Final bearing pressure check
        q_max_final, q_min_final = self._calculate_bearing_pressures(
            P_service, Mx_service, My_service, L, B
        )
        
        return {
            "length": L,
            "width": B,
            "area": L * B,
            "area_required": area_required,
            "bearing_pressure_max": q_max_final,
            "bearing_pressure_min": q_min_final,
            "allowable_bearing_pressure": qa,
            "adequate": q_max_final <= qa and q_min_final >= 0
        }
    
    def _calculate_bearing_pressures(self, P: float, Mx: float, My: float,
                                   L: float, B: float) -> Tuple[float, float]:
        """
        Calculate maximum and minimum bearing pressures
        """
        A = L * B
        Sx = L * B**2 / 6  # Section modulus about x-axis
        Sy = B * L**2 / 6  # Section modulus about y-axis
        
        # Bearing pressure at corners
        q1 = P/A + Mx/Sx + My/Sy
        q2 = P/A + Mx/Sx - My/Sy
        q3 = P/A - Mx/Sx + My/Sy
        q4 = P/A - Mx/Sx - My/Sy
        
        q_max = max(q1, q2, q3, q4)
        q_min = min(q1, q2, q3, q4)
        
        return q_max, q_min
    
    def _check_punching_shear(self, sizing: Dict, P: float, 
                             col_width: float, col_depth: float,
                             concrete: ConcreteMaterial) -> Dict:
        """
        Check punching shear around column
        """
        # Footing dimensions
        L = sizing["length"]
        B = sizing["width"]
        
        # Assume footing thickness
        d = max(L/10, B/10, 0.3)  # Effective depth
        D = d + 0.075  # Total thickness (assuming 75mm cover)
        
        # Critical section for punching shear (d/2 from column face)
        b1 = col_width/1000 + d  # Critical section width
        b2 = col_depth/1000 + d  # Critical section depth
        
        # Punching shear force
        Vu = P * (1 - (b1 * b2)/(L * B))  # Net upward force
        
        # Critical perimeter
        bo = 2 * (b1 + b2)  # Perimeter of critical section
        
        # Punching shear stress
        vu = Vu * 1000 / (bo * 1000 * d * 1000)  # MPa
        
        # Allowable punching shear stress (IS 456)
        fck = concrete.compressive_strength
        vc = 0.25 * math.sqrt(fck)  # MPa (simplified)
        
        return {
            "footing_thickness": D,
            "effective_depth": d,
            "critical_section": {"b1": b1, "b2": b2},
            "punching_force": Vu,
            "punching_stress": vu,
            "allowable_stress": vc,
            "adequate": vu <= vc,
            "utilization": vu / vc
        }
    
    def _check_one_way_shear(self, sizing: Dict, P: float,
                           col_width: float, col_depth: float,
                           concrete: ConcreteMaterial) -> Dict:
        """
        Check one-way shear
        """
        L = sizing["length"]
        B = sizing["width"]
        d = max(L/10, B/10, 0.3)  # Effective depth
        
        # Critical sections for one-way shear (at d from column face)
        x_crit = (L - col_width/1000)/2 - d
        y_crit = (B - col_depth/1000)/2 - d
        
        # Shear forces
        Vu_x = P * x_crit / L  # Shear in x-direction
        Vu_y = P * y_crit / B  # Shear in y-direction
        
        # Shear stresses
        vu_x = Vu_x * 1000 / (B * 1000 * d * 1000)  # MPa
        vu_y = Vu_y * 1000 / (L * 1000 * d * 1000)  # MPa
        
        # Allowable shear stress
        fck = concrete.compressive_strength
        vc = 0.62 * math.sqrt(fck)  # MPa (simplified)
        
        return {
            "shear_force_x": Vu_x,
            "shear_force_y": Vu_y,
            "shear_stress_x": vu_x,
            "shear_stress_y": vu_y,
            "allowable_stress": vc,
            "adequate": max(vu_x, vu_y) <= vc,
            "utilization": max(vu_x, vu_y) / vc
        }
    
    def _design_footing_reinforcement(self, sizing: Dict, P: float,
                                    Mx: float, My: float,
                                    col_width: float, col_depth: float,
                                    concrete: ConcreteMaterial,
                                    steel: SteelMaterial) -> Dict:
        """
        Design flexural reinforcement for footing
        """
        L = sizing["length"]
        B = sizing["width"]
        d = max(L/10, B/10, 0.3)
        
        # Calculate moments at critical sections
        # Critical section for moment is at face of column
        
        # Moment in x-direction (about y-axis)
        x_moment_arm = (L - col_width/1000) / 2
        Mu_x = P * x_moment_arm**2 / (2 * L)  # Simplified
        
        # Moment in y-direction (about x-axis)
        y_moment_arm = (B - col_depth/1000) / 2
        Mu_y = P * y_moment_arm**2 / (2 * B)  # Simplified
        
        # Design reinforcement in x-direction
        As_x = self._calculate_required_steel(Mu_x, B, d, concrete, steel)
        
        # Design reinforcement in y-direction
        As_y = self._calculate_required_steel(Mu_y, L, d, concrete, steel)
        
        # Check minimum reinforcement
        As_min = 0.0012 * B * 1000 * d * 1000 / 1e6  # mm²/m width
        
        As_x = max(As_x, As_min * B)
        As_y = max(As_y, As_min * L)
        
        return {
            "moment_x": Mu_x,
            "moment_y": Mu_y,
            "steel_required_x": As_x,
            "steel_required_y": As_y,
            "steel_minimum": As_min,
            "effective_depth": d,
            "adequate": True  # Simplified
        }
    
    def _calculate_required_steel(self, Mu: float, b: float, d: float,
                                concrete: ConcreteMaterial,
                                steel: SteelMaterial) -> float:
        """
        Calculate required steel area for given moment
        """
        fck = concrete.compressive_strength
        fy = steel.yield_strength
        
        # Simplified steel calculation
        # Mu = 0.87 * fy * As * d * (1 - fy*As/(fck*b*d))
        # Assuming balanced section for simplicity
        
        Ru = Mu * 1e6 / (b * 1000 * (d * 1000)**2)  # N/mm²
        
        # Steel percentage
        p = (0.87 * fck / fy) * (1 - math.sqrt(1 - 4.6 * Ru / fck))
        
        # Steel area
        As = p * b * 1000 * d * 1000 / 100  # mm²
        
        return As
    
    def _check_development_length(self, flexural: Dict,
                                concrete: ConcreteMaterial,
                                steel: SteelMaterial) -> Dict:
        """
        Check development length requirements
        """
        # Assume 16mm bars
        bar_diameter = 16  # mm
        
        fck = concrete.compressive_strength
        fy = steel.yield_strength
        
        # Development length (IS 456)
        Ld = (0.87 * fy * bar_diameter) / (4 * math.sqrt(fck))
        
        # Available length (from critical section to edge)
        available_length = flexural["effective_depth"] * 1000 * 0.8  # 80% of effective depth
        
        return {
            "required_development_length": Ld,
            "available_length": available_length,
            "adequate": available_length >= Ld,
            "bar_diameter_assumed": bar_diameter
        }
    
    def _check_footing_adequacy(self, results: Dict) -> bool:
        """
        Check overall adequacy of footing design
        """
        checks = [
            results.get("sizing", {}).get("adequate", False),
            results.get("punching_shear", {}).get("adequate", False),
            results.get("one_way_shear", {}).get("adequate", False),
            results.get("flexural_design", {}).get("adequate", False),
            results.get("development_length", {}).get("adequate", False)
        ]
        
        return all(checks)
    
    def _design_combined_footing_as_beam(self, footing_data: Dict,
                                       loads_list: List[Dict],
                                       column_positions: List[Tuple[float, float]],
                                       concrete: ConcreteMaterial,
                                       steel: SteelMaterial) -> Dict:
        """
        Design combined footing as beam
        """
        # Simplified beam design
        length = footing_data["dimensions"]["length"]
        width = footing_data["dimensions"]["width"]
        
        # Assume beam depth
        beam_depth = length / 12  # L/12 ratio
        effective_depth = beam_depth - 0.075  # 75mm cover
        
        # Calculate maximum moment (simplified)
        total_load = sum(loads.get('axial', 0) for loads in loads_list)
        max_moment = total_load * length / 8  # Simplified
        
        # Design steel
        As_required = self._calculate_required_steel(
            max_moment, width, effective_depth, concrete, steel
        )
        
        return {
            "beam_depth": beam_depth,
            "effective_depth": effective_depth,
            "max_moment": max_moment,
            "steel_required": As_required,
            "adequate": True
        }
    
    def _check_pile_cap_punching_shear(self, cap_data: Dict, loads: Dict,
                                     concrete: ConcreteMaterial) -> Dict:
        """
        Check punching shear in pile cap
        """
        # Simplified punching shear check
        P = loads.get('axial', 0)
        thickness = cap_data["dimensions"]["thickness"]
        d = thickness - 0.075  # Effective depth
        
        # Assume 400mm x 400mm column
        col_size = 0.4  # m
        
        # Critical perimeter
        bo = 4 * (col_size + d)  # Simplified
        
        # Punching shear stress
        vu = P * 1000 / (bo * 1000 * d * 1000)  # MPa
        
        # Allowable stress
        fck = concrete.compressive_strength
        vc = 0.25 * math.sqrt(fck)
        
        return {
            "punching_stress": vu,
            "allowable_stress": vc,
            "adequate": vu <= vc
        }
    
    def _design_pile_cap_reinforcement(self, cap_data: Dict, loads: Dict,
                                     concrete: ConcreteMaterial,
                                     steel: SteelMaterial) -> Dict:
        """
        Design pile cap reinforcement
        """
        # Simplified reinforcement design
        P = loads.get('axial', 0)
        cap_size = cap_data["dimensions"]["length"]
        thickness = cap_data["dimensions"]["thickness"]
        d = thickness - 0.075
        
        # Moment from pile reaction
        pile_spacing = cap_data["dimensions"]["pile_spacing"]
        moment_arm = pile_spacing / 2
        moment = P/4 * moment_arm  # Assuming 4 piles
        
        # Steel calculation
        As_required = self._calculate_required_steel(
            moment, cap_size, d, concrete, steel
        )
        
        return {
            "design_moment": moment,
            "steel_required": As_required,
            "adequate": True
        }