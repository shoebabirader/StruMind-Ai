"""
IS 456:2000 Concrete Design Implementation
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from ...core.modeling.elements import Element
from ...core.modeling.sections import ConcreteSection
from ...core.modeling.materials import ConcreteMaterial, SteelMaterial

logger = logging.getLogger(__name__)


class IS456ConcreteDesign:
    """
    IS 456:2000 concrete design implementation
    """
    
    def __init__(self):
        self.code_name = "IS 456:2000"
        self.gamma_c = 1.5  # Partial safety factor for concrete
        self.gamma_s = 1.15  # Partial safety factor for steel
        self.min_cover = 25  # mm, minimum concrete cover
        
    def design_beam(self,
                   element: Element,
                   forces: Dict,
                   section: ConcreteSection,
                   concrete: ConcreteMaterial,
                   steel: SteelMaterial) -> Dict:
        """
        Design reinforced concrete beam according to IS 456
        """
        logger.info(f"Designing RC beam {element.id} per IS 456")
        
        # Extract forces
        Mu = max(abs(forces.get('moment_y', 0)), abs(forces.get('moment_z', 0)))  # kN-m
        Vu = max(abs(forces.get('shear_y', 0)), abs(forces.get('shear_z', 0)))   # kN
        
        # Material properties
        fck = concrete.compressive_strength  # MPa
        fy = steel.yield_strength  # MPa
        
        # Section properties
        b = section.width  # mm
        D = section.depth  # mm
        d = D - self.min_cover - 10  # Effective depth (assuming 10mm bar radius)
        
        results = {
            "element_id": element.id,
            "code": self.code_name,
            "forces": {
                "Mu": Mu,
                "Vu": Vu
            },
            "section_properties": {
                "width": b,
                "depth": D,
                "effective_depth": d
            }
        }
        
        # Flexural design
        if Mu > 0:
            flexural_results = self._design_flexure_is456(Mu, b, d, fck, fy)
            results["flexural"] = flexural_results
        
        # Shear design
        if Vu > 0:
            shear_results = self._design_shear_is456(Vu, b, d, fck, fy, flexural_results.get("As_provided", 0))
            results["shear"] = shear_results
        
        # Check minimum reinforcement
        min_steel_results = self._check_minimum_steel_is456(b, d, fy)
        results["minimum_steel"] = min_steel_results
        
        # Overall adequacy
        results["adequate"] = self._check_overall_adequacy(results)
        
        return results
    
    def design_column(self,
                     element: Element,
                     forces: Dict,
                     section: ConcreteSection,
                     concrete: ConcreteMaterial,
                     steel: SteelMaterial,
                     effective_length: float = None) -> Dict:
        """
        Design reinforced concrete column according to IS 456
        """
        logger.info(f"Designing RC column {element.id} per IS 456")
        
        # Extract forces
        Pu = abs(forces.get('axial', 0))  # kN (compression)
        Mux = abs(forces.get('moment_x', 0))  # kN-m
        Muy = abs(forces.get('moment_y', 0))  # kN-m
        
        # Material properties
        fck = concrete.compressive_strength  # MPa
        fy = steel.yield_strength  # MPa
        
        # Section properties
        b = section.width  # mm
        D = section.depth  # mm
        Ag = b * D  # Gross area
        
        # Effective length
        if effective_length is None:
            lex = ley = element.length * 1000  # Convert to mm
        else:
            lex = ley = effective_length * 1000
        
        results = {
            "element_id": element.id,
            "code": self.code_name,
            "forces": {
                "Pu": Pu,
                "Mux": Mux,
                "Muy": Muy
            },
            "section_properties": {
                "width": b,
                "depth": D,
                "gross_area": Ag
            }
        }
        
        # Check slenderness
        slenderness_results = self._check_slenderness_is456(lex, ley, b, D)
        results["slenderness"] = slenderness_results
        
        # Design for axial load and moment
        if Pu > 0:
            if slenderness_results["is_short_column"]:
                design_results = self._design_short_column_is456(Pu, Mux, Muy, b, D, fck, fy)
            else:
                design_results = self._design_slender_column_is456(Pu, Mux, Muy, b, D, lex, ley, fck, fy)
            
            results["design"] = design_results
        
        # Check minimum and maximum steel
        steel_limits = self._check_steel_limits_is456(Ag, fy)
        results["steel_limits"] = steel_limits
        
        results["adequate"] = self._check_overall_adequacy(results)
        
        return results
    
    def design_slab(self,
                   element: Element,
                   forces: Dict,
                   section: ConcreteSection,
                   concrete: ConcreteMaterial,
                   steel: SteelMaterial) -> Dict:
        """
        Design reinforced concrete slab according to IS 456
        """
        logger.info(f"Designing RC slab {element.id} per IS 456")
        
        # Extract forces (per unit width)
        Mux = abs(forces.get('moment_x', 0))  # kN-m/m
        Muy = abs(forces.get('moment_y', 0))  # kN-m/m
        Vux = abs(forces.get('shear_x', 0))   # kN/m
        Vuy = abs(forces.get('shear_y', 0))   # kN/m
        
        # Material properties
        fck = concrete.compressive_strength  # MPa
        fy = steel.yield_strength  # MPa
        
        # Section properties
        D = section.thickness  # mm
        d = D - self.min_cover - 6  # Effective depth (assuming 6mm bars)
        
        results = {
            "element_id": element.id,
            "code": self.code_name,
            "forces": {
                "Mux": Mux,
                "Muy": Muy,
                "Vux": Vux,
                "Vuy": Vuy
            },
            "section_properties": {
                "thickness": D,
                "effective_depth": d
            }
        }
        
        # Design reinforcement in both directions
        if Mux > 0:
            flexural_x = self._design_slab_reinforcement_is456(Mux, 1000, d, fck, fy, "x-direction")
            results["reinforcement_x"] = flexural_x
        
        if Muy > 0:
            flexural_y = self._design_slab_reinforcement_is456(Muy, 1000, d, fck, fy, "y-direction")
            results["reinforcement_y"] = flexural_y
        
        # Check shear
        if max(Vux, Vuy) > 0:
            shear_results = self._check_slab_shear_is456(max(Vux, Vuy), 1000, d, fck)
            results["shear"] = shear_results
        
        # Check minimum reinforcement
        min_steel_slab = self._check_minimum_steel_slab_is456(D, fy)
        results["minimum_steel"] = min_steel_slab
        
        results["adequate"] = self._check_overall_adequacy(results)
        
        return results
    
    def _design_flexure_is456(self, Mu: float, b: float, d: float, fck: float, fy: float) -> Dict:
        """
        Design flexural reinforcement per IS 456
        """
        # Limiting moment of resistance
        xu_max = 0.48 * d  # For Fe415 steel
        if fy > 415:
            xu_max = 0.46 * d  # For Fe500 steel
        
        Mu_lim = 0.36 * fck * b * xu_max * (d - 0.42 * xu_max) / 1e6  # kN-m
        
        if Mu <= Mu_lim:
            # Singly reinforced section
            # Mu = 0.87*fy*As*d*(1 - fy*As/(fck*b*d))
            # Solving quadratic equation
            a = 0.87 * fy / (fck * b)
            b_coeff = -0.87 * fy * d
            c = Mu * 1e6
            
            discriminant = b_coeff**2 - 4 * a * c
            if discriminant >= 0:
                As1 = (-b_coeff - math.sqrt(discriminant)) / (2 * a)
                As2 = (-b_coeff + math.sqrt(discriminant)) / (2 * a)
                As_required = min(As1, As2) if As1 > 0 and As2 > 0 else max(As1, As2)
            else:
                As_required = Mu * 1e6 / (0.87 * fy * 0.9 * d)  # Approximate
            
            return {
                "type": "singly_reinforced",
                "Mu_lim": Mu_lim,
                "As_required": As_required,
                "As_provided": As_required * 1.1,  # 10% extra
                "compression_steel": 0,
                "xu": As_required * fy / (0.36 * fck * b),
                "adequate": True
            }
        else:
            # Doubly reinforced section
            Mu1 = Mu_lim
            Mu2 = Mu - Mu1
            
            # Compression steel
            d_dash = 50  # mm, assumed cover to compression steel
            fsc = 0.87 * fy  # Stress in compression steel
            Asc = Mu2 * 1e6 / (fsc * (d - d_dash))
            
            # Additional tension steel
            As2 = Asc
            
            # Total tension steel
            As1 = 0.36 * fck * b * xu_max / (0.87 * fy)
            As_total = As1 + As2
            
            return {
                "type": "doubly_reinforced",
                "Mu_lim": Mu_lim,
                "As_required": As_total,
                "As_provided": As_total * 1.1,
                "compression_steel": Asc,
                "xu": xu_max,
                "adequate": True
            }
    
    def _design_shear_is456(self, Vu: float, b: float, d: float, fck: float, fy: float, As: float) -> Dict:
        """
        Design shear reinforcement per IS 456
        """
        # Nominal shear stress
        tau_v = Vu * 1000 / (b * d)  # MPa
        
        # Permissible shear stress in concrete
        pt = 100 * As / (b * d)  # Percentage of tension steel
        pt = min(pt, 3.0)  # Maximum 3%
        
        # Table 19 of IS 456 (simplified)
        if fck <= 20:
            if pt <= 0.15:
                tau_c = 0.28
            elif pt <= 0.25:
                tau_c = 0.35
            elif pt <= 0.5:
                tau_c = 0.46
            elif pt <= 0.75:
                tau_c = 0.54
            elif pt <= 1.0:
                tau_c = 0.60
            elif pt <= 1.25:
                tau_c = 0.64
            elif pt <= 1.5:
                tau_c = 0.68
            elif pt <= 1.75:
                tau_c = 0.70
            elif pt <= 2.0:
                tau_c = 0.72
            elif pt <= 2.25:
                tau_c = 0.73
            elif pt <= 2.5:
                tau_c = 0.74
            elif pt <= 2.75:
                tau_c = 0.75
            else:
                tau_c = 0.75
        else:
            # For higher grade concrete, multiply by sqrt(fck/20)
            tau_c_base = 0.75  # For pt = 3%
            tau_c = tau_c_base * math.sqrt(fck / 20)
        
        # Maximum shear stress
        tau_c_max = 0.625 * math.sqrt(fck)  # MPa
        
        if tau_v <= tau_c:
            # No shear reinforcement required
            return {
                "tau_v": tau_v,
                "tau_c": tau_c,
                "shear_reinforcement_required": False,
                "stirrup_spacing": "No stirrups required",
                "adequate": True
            }
        elif tau_v <= tau_c_max:
            # Shear reinforcement required
            Vus = (tau_v - tau_c) * b * d / 1000  # kN
            
            # Assume 8mm stirrups, 2-legged
            Asv = 2 * math.pi * (8/2)**2  # mm²
            sv = 0.87 * fy * Asv * d / (Vus * 1000)  # mm
            
            # Check maximum spacing
            sv_max = min(0.75 * d, 300)  # mm
            sv = min(sv, sv_max)
            
            return {
                "tau_v": tau_v,
                "tau_c": tau_c,
                "tau_c_max": tau_c_max,
                "shear_reinforcement_required": True,
                "Vus": Vus,
                "stirrup_spacing": sv,
                "stirrup_area": Asv,
                "adequate": True
            }
        else:
            # Shear stress exceeds maximum permissible
            return {
                "tau_v": tau_v,
                "tau_c": tau_c,
                "tau_c_max": tau_c_max,
                "shear_reinforcement_required": True,
                "adequate": False,
                "error": "Shear stress exceeds maximum permissible value"
            }
    
    def _check_minimum_steel_is456(self, b: float, d: float, fy: float) -> Dict:
        """
        Check minimum steel requirements per IS 456
        """
        # Minimum tension reinforcement
        As_min = 0.85 * b * d / fy  # mm²
        
        # Maximum tension reinforcement
        As_max = 0.04 * b * d  # mm² (4% of gross area)
        
        return {
            "As_min": As_min,
            "As_max": As_max,
            "min_percentage": 0.85 / fy * 100,
            "max_percentage": 4.0
        }
    
    def _check_slenderness_is456(self, lex: float, ley: float, b: float, D: float) -> Dict:
        """
        Check column slenderness per IS 456
        """
        # Slenderness ratios
        slenderness_x = lex / b
        slenderness_y = ley / D
        max_slenderness = max(slenderness_x, slenderness_y)
        
        # Short column if slenderness ratio < 12
        is_short_column = max_slenderness < 12
        
        return {
            "lex": lex,
            "ley": ley,
            "slenderness_x": slenderness_x,
            "slenderness_y": slenderness_y,
            "max_slenderness": max_slenderness,
            "is_short_column": is_short_column,
            "slenderness_limit": 12
        }
    
    def _design_short_column_is456(self, Pu: float, Mux: float, Muy: float, 
                                  b: float, D: float, fck: float, fy: float) -> Dict:
        """
        Design short column per IS 456
        """
        Ag = b * D
        
        # Check if axial load only
        if Mux == 0 and Muy == 0:
            # Pure compression
            Pu_max = 0.4 * fck * Ag / 1000  # kN (assuming 4% steel)
            
            if Pu <= Pu_max:
                # Minimum steel
                As_min = 0.008 * Ag  # 0.8% minimum
                As_max = 0.06 * Ag   # 6% maximum
                As_required = As_min
            else:
                # Calculate required steel
                As_required = (Pu * 1000 - 0.4 * fck * Ag) / (0.67 * fy - 0.4 * fck)
                As_required = max(As_required, 0.008 * Ag)
                As_required = min(As_required, 0.06 * Ag)
            
            return {
                "load_type": "axial_only",
                "Pu_max": Pu_max,
                "As_required": As_required,
                "As_provided": As_required * 1.1,
                "steel_percentage": As_required / Ag * 100,
                "adequate": Pu <= Pu_max
            }
        else:
            # Combined axial load and moment
            # Simplified approach using interaction diagram
            
            # Balanced failure condition
            xu_bal = 0.48 * D  # For Fe415
            if fy > 415:
                xu_bal = 0.46 * D
            
            # Assume steel percentage
            p = 0.02  # 2% steel
            As = p * Ag
            
            # Check adequacy using simplified interaction
            Pu_max = 0.4 * fck * Ag / 1000 + 0.67 * fy * As / 1000
            Mu_max = 0.36 * fck * b * xu_bal * (D/2 - 0.42 * xu_bal) / 1e6
            
            # Interaction check (simplified)
            interaction_ratio = (Pu / Pu_max) + (max(Mux, Muy) / Mu_max)
            
            return {
                "load_type": "combined",
                "assumed_steel_percentage": p * 100,
                "As_assumed": As,
                "Pu_max": Pu_max,
                "Mu_max": Mu_max,
                "interaction_ratio": interaction_ratio,
                "adequate": interaction_ratio <= 1.0
            }
    
    def _design_slender_column_is456(self, Pu: float, Mux: float, Muy: float,
                                    b: float, D: float, lex: float, ley: float,
                                    fck: float, fy: float) -> Dict:
        """
        Design slender column with additional moments per IS 456
        """
        # Additional moments due to slenderness
        # Simplified approach
        
        slenderness_x = lex / b
        slenderness_y = ley / D
        
        # Additional moment factors (simplified)
        if slenderness_x > 12:
            k_x = 1 + (slenderness_x - 12) * 0.01
            Mux_additional = k_x * Mux
        else:
            Mux_additional = Mux
        
        if slenderness_y > 12:
            k_y = 1 + (slenderness_y - 12) * 0.01
            Muy_additional = k_y * Muy
        else:
            Muy_additional = Muy
        
        # Design as short column with additional moments
        short_column_results = self._design_short_column_is456(
            Pu, Mux_additional, Muy_additional, b, D, fck, fy
        )
        
        return {
            "load_type": "slender_column",
            "slenderness_factors": {
                "k_x": k_x if slenderness_x > 12 else 1.0,
                "k_y": k_y if slenderness_y > 12 else 1.0
            },
            "additional_moments": {
                "Mux_additional": Mux_additional,
                "Muy_additional": Muy_additional
            },
            **short_column_results
        }
    
    def _check_steel_limits_is456(self, Ag: float, fy: float) -> Dict:
        """
        Check steel percentage limits per IS 456
        """
        As_min = 0.008 * Ag  # 0.8% minimum
        As_max = 0.06 * Ag   # 6% maximum
        
        return {
            "As_min": As_min,
            "As_max": As_max,
            "min_percentage": 0.8,
            "max_percentage": 6.0
        }
    
    def _design_slab_reinforcement_is456(self, Mu: float, b: float, d: float, 
                                        fck: float, fy: float, direction: str) -> Dict:
        """
        Design slab reinforcement per IS 456
        """
        # Similar to beam design but for unit width
        flexural_results = self._design_flexure_is456(Mu, b, d, fck, fy)
        
        # Convert to reinforcement per meter
        As_per_meter = flexural_results["As_required"]
        
        # Bar spacing calculation
        bar_sizes = [8, 10, 12, 16]  # mm
        spacing_options = []
        
        for bar_size in bar_sizes:
            bar_area = math.pi * (bar_size/2)**2
            spacing = bar_area * 1000 / As_per_meter  # mm
            
            if 75 <= spacing <= 300:  # Practical spacing limits
                spacing_options.append({
                    "bar_size": bar_size,
                    "spacing": spacing,
                    "area_provided": bar_area * 1000 / spacing
                })
        
        # Select optimal spacing
        if spacing_options:
            optimal = min(spacing_options, key=lambda x: x["area_provided"])
        else:
            # Use minimum bar size with maximum spacing
            optimal = {
                "bar_size": 8,
                "spacing": 200,
                "area_provided": math.pi * (8/2)**2 * 1000 / 200
            }
        
        return {
            "direction": direction,
            "As_required": As_per_meter,
            "bar_size": optimal["bar_size"],
            "spacing": optimal["spacing"],
            "As_provided": optimal["area_provided"],
            "reinforcement_ratio": optimal["area_provided"] / (b * d) * 100
        }
    
    def _check_slab_shear_is456(self, Vu: float, b: float, d: float, fck: float) -> Dict:
        """
        Check slab shear per IS 456
        """
        # Nominal shear stress
        tau_v = Vu * 1000 / (b * d)  # MPa
        
        # Permissible shear stress for slabs (no shear reinforcement)
        tau_c = 0.25 * math.sqrt(fck)  # MPa (simplified)
        
        return {
            "tau_v": tau_v,
            "tau_c": tau_c,
            "adequate": tau_v <= tau_c,
            "shear_reinforcement_required": tau_v > tau_c
        }
    
    def _check_minimum_steel_slab_is456(self, D: float, fy: float) -> Dict:
        """
        Check minimum steel for slab per IS 456
        """
        # Minimum steel percentage
        if fy <= 250:
            min_percentage = 0.15
        else:
            min_percentage = 0.12
        
        As_min = min_percentage * 1000 * D / 100  # mm²/m
        
        return {
            "min_percentage": min_percentage,
            "As_min_per_meter": As_min,
            "distribution_steel": As_min * 0.2  # 20% of main steel
        }
    
    def _check_overall_adequacy(self, results: Dict) -> bool:
        """
        Check overall adequacy of the design
        """
        adequate = True
        
        # Check individual components
        for key, value in results.items():
            if isinstance(value, dict) and "adequate" in value:
                if not value["adequate"]:
                    adequate = False
                    break
        
        return adequate
    
    def get_design_summary(self, results: Dict) -> str:
        """
        Generate design summary report
        """
        summary = f"IS 456:2000 Design Summary for Element {results['element_id']}\n"
        summary += "=" * 60 + "\n\n"
        
        # Forces
        forces = results["forces"]
        summary += f"Applied Forces:\n"
        for force_type, value in forces.items():
            summary += f"  {force_type}: {value:.2f}\n"
        summary += "\n"
        
        # Design results
        if "flexural" in results:
            flex = results["flexural"]
            summary += f"Flexural Design:\n"
            summary += f"  Type: {flex['type']}\n"
            summary += f"  As required: {flex['As_required']:.0f} mm²\n"
            summary += f"  As provided: {flex['As_provided']:.0f} mm²\n"
            if flex.get('compression_steel', 0) > 0:
                summary += f"  Compression steel: {flex['compression_steel']:.0f} mm²\n"
            summary += "\n"
        
        if "shear" in results:
            shear = results["shear"]
            summary += f"Shear Design:\n"
            summary += f"  τv = {shear['tau_v']:.3f} MPa\n"
            summary += f"  τc = {shear['tau_c']:.3f} MPa\n"
            if shear['shear_reinforcement_required']:
                summary += f"  Stirrup spacing: {shear['stirrup_spacing']:.0f} mm\n"
            else:
                summary += f"  No shear reinforcement required\n"
            summary += "\n"
        
        # Overall result
        summary += f"Overall Result: {'ADEQUATE' if results['adequate'] else 'NOT ADEQUATE'}\n"
        
        return summary