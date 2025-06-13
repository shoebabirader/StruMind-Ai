"""
Reinforced Concrete Design Module
Supports IS 456, ACI 318, Eurocode 2, and other international codes
"""

import math
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from dataclasses import dataclass
import uuid

from db.models.structural import Element, Material, Section
from db.models.design import DesignCase, DesignResult
from core.exceptions import DesignError


class ConcreteGrade(Enum):
    """Standard concrete grades"""
    M15 = "M15"
    M20 = "M20"
    M25 = "M25"
    M30 = "M30"
    M35 = "M35"
    M40 = "M40"
    M45 = "M45"
    M50 = "M50"


class SteelGrade(Enum):
    """Reinforcement steel grades"""
    FE250 = "Fe250"
    FE415 = "Fe415"
    FE500 = "Fe500"
    FE550 = "Fe550"


@dataclass
class DesignForces:
    """Design forces for RC elements"""
    axial_force: float  # N (compression positive)
    shear_force_y: float  # N
    shear_force_z: float  # N
    moment_y: float  # N.m
    moment_z: float  # N.m
    torsion: float  # N.m


@dataclass
class ReinforcementResult:
    """Reinforcement calculation result"""
    area_required: float  # mm²
    area_provided: float  # mm²
    bar_diameter: float  # mm
    number_of_bars: int
    spacing: Optional[float] = None  # mm (for stirrups)
    utilization_ratio: float = 0.0


class ConcreteDesign:
    """Base class for concrete design"""
    
    def __init__(self, design_code: str = "IS456"):
        self.design_code = design_code
        self.load_factors = self._get_load_factors()
        self.material_factors = self._get_material_factors()
    
    def _get_load_factors(self) -> Dict[str, float]:
        """Get load factors based on design code"""
        if self.design_code == "IS456":
            return {
                "dead": 1.5,
                "live": 1.5,
                "wind": 1.5,
                "seismic": 1.5
            }
        elif self.design_code == "ACI318":
            return {
                "dead": 1.4,
                "live": 1.7,
                "wind": 1.6,
                "seismic": 1.0
            }
        else:
            return {"dead": 1.5, "live": 1.5, "wind": 1.5, "seismic": 1.5}
    
    def _get_material_factors(self) -> Dict[str, float]:
        """Get material safety factors"""
        if self.design_code == "IS456":
            return {"concrete": 1.5, "steel": 1.15}
        elif self.design_code == "ACI318":
            return {"concrete": 1.0, "steel": 1.0}  # Strength reduction factors used instead
        else:
            return {"concrete": 1.5, "steel": 1.15}
    
    def get_concrete_properties(self, grade: str) -> Dict[str, float]:
        """Get concrete material properties"""
        concrete_props = {
            "M15": {"fck": 15e6, "E": 22360e6},
            "M20": {"fck": 20e6, "E": 25000e6},
            "M25": {"fck": 25e6, "E": 27386e6},
            "M30": {"fck": 30e6, "E": 29580e6},
            "M35": {"fck": 35e6, "E": 31623e6},
            "M40": {"fck": 40e6, "E": 33541e6},
            "M45": {"fck": 45e6, "E": 35355e6},
            "M50": {"fck": 50e6, "E": 37081e6}
        }
        
        props = concrete_props.get(grade, concrete_props["M25"])
        
        if self.design_code == "IS456":
            props["fcd"] = props["fck"] / self.material_factors["concrete"]
        elif self.design_code == "ACI318":
            props["fcd"] = 0.85 * props["fck"]  # ACI strength reduction
        
        return props
    
    def get_steel_properties(self, grade: str) -> Dict[str, float]:
        """Get reinforcement steel properties"""
        steel_props = {
            "Fe250": {"fy": 250e6, "Es": 200e9},
            "Fe415": {"fy": 415e6, "Es": 200e9},
            "Fe500": {"fy": 500e6, "Es": 200e9},
            "Fe550": {"fy": 550e6, "Es": 200e9}
        }
        
        props = steel_props.get(grade, steel_props["Fe415"])
        
        if self.design_code == "IS456":
            props["fyd"] = props["fy"] / self.material_factors["steel"]
        elif self.design_code == "ACI318":
            props["fyd"] = props["fy"]  # Strength reduction applied separately
        
        return props


class RCBeamDesign(ConcreteDesign):
    """Reinforced concrete beam design"""
    
    def design_beam(self, element: Element, section: Section, material: Material,
                   design_forces: DesignForces, design_params: Dict[str, Any]) -> Dict[str, Any]:
        """Design RC beam for flexure and shear"""
        try:
            # Extract parameters
            concrete_grade = design_params.get("concrete_grade", "M25")
            steel_grade = design_params.get("steel_grade", "Fe415")
            cover = design_params.get("cover", 25e-3)  # m
            
            # Get material properties
            concrete_props = self.get_concrete_properties(concrete_grade)
            steel_props = self.get_steel_properties(steel_grade)
            
            # Section dimensions
            width = section.dimensions.get("width", 0.3)  # m
            depth = section.dimensions.get("height", 0.5)  # m
            effective_depth = depth - cover - 0.010  # Assuming 10mm bar diameter
            
            # Design for flexure
            flexural_design = self._design_flexural_reinforcement(
                design_forces.moment_z, width, effective_depth,
                concrete_props, steel_props
            )
            
            # Design for shear
            shear_design = self._design_shear_reinforcement(
                design_forces.shear_force_y, width, effective_depth,
                concrete_props, steel_props, flexural_design["area_provided"]
            )
            
            # Check minimum reinforcement
            min_reinforcement = self._check_minimum_reinforcement(
                width, depth, concrete_props, steel_props
            )
            
            # Prepare design result
            design_result = {
                "element_id": element.id,
                "design_code": self.design_code,
                "concrete_grade": concrete_grade,
                "steel_grade": steel_grade,
                "section_dimensions": {"width": width, "depth": depth, "effective_depth": effective_depth},
                "design_forces": {
                    "moment": design_forces.moment_z,
                    "shear": design_forces.shear_force_y,
                    "axial": design_forces.axial_force
                },
                "flexural_reinforcement": flexural_design,
                "shear_reinforcement": shear_design,
                "minimum_reinforcement": min_reinforcement,
                "design_checks": self._perform_design_checks(
                    flexural_design, shear_design, min_reinforcement
                )
            }
            
            return design_result
            
        except Exception as e:
            raise DesignError(f"RC beam design failed: {str(e)}")
    
    def _design_flexural_reinforcement(self, moment: float, width: float, effective_depth: float,
                                     concrete_props: Dict[str, float], 
                                     steel_props: Dict[str, float]) -> Dict[str, Any]:
        """Design flexural reinforcement"""
        fck = concrete_props["fck"]
        fy = steel_props["fy"]
        fcd = concrete_props["fcd"]
        fyd = steel_props["fyd"]
        
        # Limiting moment of resistance
        if self.design_code == "IS456":
            xu_max = 0.48 * effective_depth  # Maximum neutral axis depth
            Mu_lim = 0.36 * fck * width * xu_max * (effective_depth - 0.42 * xu_max)
        else:  # ACI318
            xu_max = 0.375 * effective_depth
            Mu_lim = 0.85 * fck * width * xu_max * (effective_depth - 0.5 * xu_max)
        
        if abs(moment) <= Mu_lim:
            # Singly reinforced section
            if self.design_code == "IS456":
                # IS 456 method
                k = moment / (fck * width * effective_depth**2)
                j = 0.5 + math.sqrt(0.25 - k/0.36)
                area_required = moment / (fyd * j * effective_depth)
            else:  # ACI318
                # ACI 318 method
                a = effective_depth - math.sqrt(effective_depth**2 - 2*moment/(0.85*fck*width))
                area_required = moment / (fy * (effective_depth - a/2))
        else:
            # Doubly reinforced section required
            area_required = self._design_doubly_reinforced(
                moment, width, effective_depth, concrete_props, steel_props
            )
        
        # Select reinforcement bars
        bar_selection = self._select_reinforcement_bars(area_required, width)
        
        return {
            "moment_design": moment,
            "area_required": area_required * 1e6,  # Convert to mm²
            "area_provided": bar_selection["area_provided"] * 1e6,
            "bar_diameter": bar_selection["diameter"] * 1000,  # Convert to mm
            "number_of_bars": bar_selection["number"],
            "utilization_ratio": area_required / bar_selection["area_provided"] if bar_selection["area_provided"] > 0 else 0,
            "reinforcement_type": "singly" if abs(moment) <= Mu_lim else "doubly"
        }
    
    def _design_shear_reinforcement(self, shear_force: float, width: float, effective_depth: float,
                                  concrete_props: Dict[str, float], steel_props: Dict[str, float],
                                  tension_steel_area: float) -> Dict[str, Any]:
        """Design shear reinforcement"""
        fck = concrete_props["fck"]
        fy = steel_props["fy"]
        
        # Concrete shear strength
        if self.design_code == "IS456":
            pt = min(tension_steel_area / (width * effective_depth), 0.04) * 100
            tau_c = self._get_concrete_shear_strength_is456(pt, fck)
        else:  # ACI318
            tau_c = 0.17 * math.sqrt(fck)
        
        Vc = tau_c * width * effective_depth
        
        # Check if shear reinforcement is required
        if abs(shear_force) <= Vc:
            # Minimum shear reinforcement
            if self.design_code == "IS456":
                min_shear_steel = 0.87 * fy * width / (0.4 * fy)
            else:  # ACI318
                min_shear_steel = 0.75 * math.sqrt(fck) * width / fy
            
            spacing = min(0.75 * effective_depth, 300e-3)  # Maximum spacing
        else:
            # Design shear reinforcement
            Vs_required = abs(shear_force) - Vc
            
            # Stirrup design
            stirrup_diameter = 8e-3  # 8mm stirrups
            stirrup_area = 2 * math.pi * (stirrup_diameter/2)**2  # Two-legged stirrups
            
            spacing = stirrup_area * fy / (Vs_required / effective_depth)
            spacing = min(spacing, 0.75 * effective_depth, 300e-3)
        
        return {
            "shear_force": shear_force,
            "concrete_shear_capacity": Vc,
            "steel_shear_required": max(0, abs(shear_force) - Vc),
            "stirrup_diameter": 8,  # mm
            "stirrup_spacing": spacing * 1000,  # mm
            "stirrup_area": stirrup_area * 1e6,  # mm²
        }
    
    def _get_concrete_shear_strength_is456(self, pt: float, fck: float) -> float:
        """Get concrete shear strength as per IS 456"""
        # Simplified table lookup - in practice, use full IS 456 Table 19
        if pt <= 0.15:
            return 0.28
        elif pt <= 0.25:
            return 0.35
        elif pt <= 0.50:
            return 0.48
        elif pt <= 0.75:
            return 0.56
        elif pt <= 1.00:
            return 0.62
        else:
            return 0.62 + (pt - 1.0) * 0.1
    
    def _design_doubly_reinforced(self, moment: float, width: float, effective_depth: float,
                                concrete_props: Dict[str, float], 
                                steel_props: Dict[str, float]) -> float:
        """Design doubly reinforced section"""
        # Simplified doubly reinforced design
        # In practice, this would be more detailed
        fck = concrete_props["fck"]
        fy = steel_props["fy"]
        
        # Assume compression steel at d' = 0.1 * effective_depth
        d_prime = 0.1 * effective_depth
        
        # Limiting moment capacity
        xu_max = 0.48 * effective_depth if self.design_code == "IS456" else 0.375 * effective_depth
        Mu_lim = 0.36 * fck * width * xu_max * (effective_depth - 0.42 * xu_max)
        
        # Additional moment to be resisted
        Mu_additional = abs(moment) - Mu_lim
        
        # Compression steel area
        Asc = Mu_additional / (fy * (effective_depth - d_prime))
        
        # Additional tension steel
        Ast_additional = Asc
        
        # Total tension steel
        Ast_limiting = Mu_lim / (fy * 0.87 * effective_depth)
        Ast_total = Ast_limiting + Ast_additional
        
        return Ast_total
    
    def _select_reinforcement_bars(self, area_required: float, width: float) -> Dict[str, Any]:
        """Select appropriate reinforcement bars"""
        # Standard bar diameters in meters
        bar_diameters = [0.008, 0.010, 0.012, 0.016, 0.020, 0.025, 0.032]
        
        best_selection = None
        min_waste = float('inf')
        
        for diameter in bar_diameters:
            bar_area = math.pi * (diameter/2)**2
            num_bars = math.ceil(area_required / bar_area)
            
            # Check if bars fit in width
            clear_cover = 0.025  # 25mm
            bar_spacing = (width - 2*clear_cover - num_bars*diameter) / (num_bars - 1) if num_bars > 1 else 0
            
            if bar_spacing >= diameter and bar_spacing >= 0.020:  # Minimum spacing
                area_provided = num_bars * bar_area
                waste = area_provided - area_required
                
                if waste < min_waste:
                    min_waste = waste
                    best_selection = {
                        "diameter": diameter,
                        "number": num_bars,
                        "area_provided": area_provided,
                        "spacing": bar_spacing
                    }
        
        if best_selection is None:
            # Fallback to minimum reinforcement
            diameter = 0.012  # 12mm bars
            bar_area = math.pi * (diameter/2)**2
            num_bars = max(2, math.ceil(area_required / bar_area))
            
            best_selection = {
                "diameter": diameter,
                "number": num_bars,
                "area_provided": num_bars * bar_area,
                "spacing": (width - 2*0.025 - num_bars*diameter) / (num_bars - 1) if num_bars > 1 else 0
            }
        
        return best_selection
    
    def _check_minimum_reinforcement(self, width: float, depth: float,
                                   concrete_props: Dict[str, float],
                                   steel_props: Dict[str, float]) -> Dict[str, Any]:
        """Check minimum reinforcement requirements"""
        fy = steel_props["fy"]
        
        if self.design_code == "IS456":
            min_tension_steel = 0.85 / fy * width * depth  # IS 456 Clause 26.5.1.1
            min_compression_steel = 0.0  # Not mandatory for beams
        else:  # ACI318
            min_tension_steel = max(
                1.4 / fy * width * depth,  # ACI 318 minimum
                math.sqrt(concrete_props["fck"]) / (4 * fy) * width * depth
            )
            min_compression_steel = 0.0
        
        return {
            "min_tension_steel": min_tension_steel * 1e6,  # mm²
            "min_compression_steel": min_compression_steel * 1e6,  # mm²
        }
    
    def _perform_design_checks(self, flexural_design: Dict[str, Any],
                             shear_design: Dict[str, Any],
                             min_reinforcement: Dict[str, Any]) -> Dict[str, bool]:
        """Perform design checks"""
        checks = {}
        
        # Flexural reinforcement check
        checks["flexural_adequate"] = flexural_design["utilization_ratio"] <= 1.0
        
        # Minimum reinforcement check
        checks["min_tension_steel"] = (
            flexural_design["area_provided"] >= min_reinforcement["min_tension_steel"]
        )
        
        # Shear reinforcement check
        checks["shear_adequate"] = shear_design["stirrup_spacing"] <= 300  # mm
        
        # Overall design check
        checks["design_adequate"] = all(checks.values())
        
        return checks


class RCColumnDesign(ConcreteDesign):
    """Reinforced concrete column design"""
    
    def design_column(self, element: Element, section: Section, material: Material,
                     design_forces: DesignForces, design_params: Dict[str, Any]) -> Dict[str, Any]:
        """Design RC column for axial force and biaxial bending"""
        try:
            # Extract parameters
            concrete_grade = design_params.get("concrete_grade", "M25")
            steel_grade = design_params.get("steel_grade", "Fe415")
            cover = design_params.get("cover", 40e-3)  # m
            
            # Get material properties
            concrete_props = self.get_concrete_properties(concrete_grade)
            steel_props = self.get_steel_properties(steel_grade)
            
            # Section dimensions
            width = section.dimensions.get("width", 0.3)  # m
            depth = section.dimensions.get("height", 0.3)  # m
            
            # Design for axial load and biaxial bending
            column_design = self._design_column_reinforcement(
                design_forces, width, depth, cover, concrete_props, steel_props
            )
            
            # Design ties
            tie_design = self._design_column_ties(
                width, depth, column_design["main_bar_diameter"], steel_props
            )
            
            # Check slenderness
            slenderness_check = self._check_column_slenderness(
                element, width, depth, design_forces
            )
            
            design_result = {
                "element_id": element.id,
                "design_code": self.design_code,
                "concrete_grade": concrete_grade,
                "steel_grade": steel_grade,
                "section_dimensions": {"width": width, "depth": depth},
                "design_forces": {
                    "axial": design_forces.axial_force,
                    "moment_y": design_forces.moment_y,
                    "moment_z": design_forces.moment_z
                },
                "main_reinforcement": column_design,
                "tie_reinforcement": tie_design,
                "slenderness_check": slenderness_check
            }
            
            return design_result
            
        except Exception as e:
            raise DesignError(f"RC column design failed: {str(e)}")
    
    def _design_column_reinforcement(self, design_forces: DesignForces,
                                   width: float, depth: float, cover: float,
                                   concrete_props: Dict[str, float],
                                   steel_props: Dict[str, float]) -> Dict[str, Any]:
        """Design column main reinforcement"""
        fck = concrete_props["fck"]
        fy = steel_props["fy"]
        
        # Gross area
        Ag = width * depth
        
        # Minimum and maximum reinforcement
        if self.design_code == "IS456":
            min_steel_ratio = 0.008  # 0.8%
            max_steel_ratio = 0.04   # 4%
        else:  # ACI318
            min_steel_ratio = 0.01   # 1%
            max_steel_ratio = 0.08   # 8%
        
        min_steel_area = min_steel_ratio * Ag
        max_steel_area = max_steel_ratio * Ag
        
        # Simplified design for axial load with small eccentricity
        P = abs(design_forces.axial_force)
        M = max(abs(design_forces.moment_y), abs(design_forces.moment_z))
        
        # Minimum eccentricity
        e_min = max(0.05 * min(width, depth), 0.020)  # 20mm minimum
        e = max(M / P if P > 0 else 0, e_min)
        
        # Design steel area (simplified method)
        if self.design_code == "IS456":
            # IS 456 simplified method
            Pu_max = 0.4 * fck * Ag + 0.67 * fy * min_steel_area
            if P <= 0.1 * Pu_max:
                # Minimum reinforcement
                steel_area = min_steel_area
            else:
                # Approximate design
                steel_area = (P - 0.4 * fck * Ag) / (0.67 * fy)
                steel_area = max(steel_area, min_steel_area)
        else:  # ACI318
            # ACI 318 simplified method
            steel_area = min_steel_area  # Conservative approach
        
        steel_area = min(steel_area, max_steel_area)
        
        # Select reinforcement bars
        bar_selection = self._select_column_bars(steel_area, width, depth, cover)
        
        return {
            "axial_force": P,
            "moment": M,
            "eccentricity": e,
            "area_required": steel_area * 1e6,  # mm²
            "area_provided": bar_selection["area_provided"] * 1e6,
            "bar_diameter": bar_selection["diameter"] * 1000,  # mm
            "number_of_bars": bar_selection["number"],
            "steel_ratio": bar_selection["area_provided"] / Ag * 100,  # %
        }
    
    def _select_column_bars(self, area_required: float, width: float, depth: float,
                          cover: float) -> Dict[str, Any]:
        """Select column reinforcement bars"""
        # Standard bar diameters
        bar_diameters = [0.012, 0.016, 0.020, 0.025, 0.032]
        
        # Minimum number of bars
        min_bars = 4 if min(width, depth) <= 0.3 else 6
        
        best_selection = None
        min_waste = float('inf')
        
        for diameter in bar_diameters:
            bar_area = math.pi * (diameter/2)**2
            num_bars = max(min_bars, math.ceil(area_required / bar_area))
            
            # Check if bars can be arranged
            if self._check_bar_arrangement(num_bars, width, depth, diameter, cover):
                area_provided = num_bars * bar_area
                waste = area_provided - area_required
                
                if waste < min_waste:
                    min_waste = waste
                    best_selection = {
                        "diameter": diameter,
                        "number": num_bars,
                        "area_provided": area_provided
                    }
        
        if best_selection is None:
            # Fallback
            diameter = 0.016
            bar_area = math.pi * (diameter/2)**2
            num_bars = max(min_bars, math.ceil(area_required / bar_area))
            
            best_selection = {
                "diameter": diameter,
                "number": num_bars,
                "area_provided": num_bars * bar_area
            }
        
        return best_selection
    
    def _check_bar_arrangement(self, num_bars: int, width: float, depth: float,
                             bar_diameter: float, cover: float) -> bool:
        """Check if bars can be arranged in the section"""
        # Simplified check - assumes rectangular arrangement
        clear_width = width - 2 * cover - bar_diameter
        clear_depth = depth - 2 * cover - bar_diameter
        
        # Minimum spacing
        min_spacing = max(bar_diameter, 0.020)  # 20mm minimum
        
        # Check if bars fit along perimeter
        perimeter_length = 2 * (clear_width + clear_depth)
        required_length = num_bars * (bar_diameter + min_spacing)
        
        return required_length <= perimeter_length
    
    def _design_column_ties(self, width: float, depth: float, main_bar_diameter: float,
                          steel_props: Dict[str, float]) -> Dict[str, Any]:
        """Design column ties/stirrups"""
        # Tie diameter
        tie_diameter = max(0.006, main_bar_diameter / 4)  # 6mm minimum, 1/4 of main bar
        
        # Tie spacing
        if self.design_code == "IS456":
            spacing = min(
                16 * main_bar_diameter,  # 16 times main bar diameter
                min(width, depth),       # Least lateral dimension
                0.300                    # 300mm maximum
            )
        else:  # ACI318
            spacing = min(
                16 * main_bar_diameter,
                48 * tie_diameter,
                min(width, depth),
                0.300
            )
        
        return {
            "tie_diameter": tie_diameter * 1000,  # mm
            "tie_spacing": spacing * 1000,        # mm
            "tie_configuration": "rectangular"
        }
    
    def _check_column_slenderness(self, element: Element, width: float, depth: float,
                                design_forces: DesignForces) -> Dict[str, Any]:
        """Check column slenderness effects"""
        # Effective length (simplified - assume fixed-fixed)
        length = element.length or 3.0  # Default 3m if not specified
        effective_length = 0.65 * length  # Fixed-fixed condition
        
        # Radius of gyration
        I_min = min(width * depth**3 / 12, depth * width**3 / 12)
        A = width * depth
        r = math.sqrt(I_min / A)
        
        # Slenderness ratio
        slenderness_ratio = effective_length / r
        
        # Slenderness limits
        if self.design_code == "IS456":
            limit = 60 if design_forces.axial_force > 0 else 180
        else:  # ACI318
            limit = 100
        
        is_slender = slenderness_ratio > limit
        
        return {
            "effective_length": effective_length,
            "slenderness_ratio": slenderness_ratio,
            "slenderness_limit": limit,
            "is_slender": is_slender,
            "requires_slenderness_effects": is_slender
        }