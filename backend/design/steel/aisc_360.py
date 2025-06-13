"""
AISC 360 Steel Design Implementation
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from ...core.modeling.elements import Element
from ...core.modeling.sections import SteelSection
from ...core.modeling.materials import SteelMaterial

logger = logging.getLogger(__name__)


class AISC360SteelDesign:
    """
    AISC 360 steel design implementation
    """
    
    def __init__(self):
        self.code_name = "AISC 360-16"
        self.phi_b = 0.9  # Flexural resistance factor
        self.phi_c = 0.9  # Compression resistance factor
        self.phi_t = 0.9  # Tension resistance factor
        self.phi_v = 0.9  # Shear resistance factor
        
    def design_beam(self, 
                   element: Element,
                   forces: Dict,
                   section: SteelSection,
                   material: SteelMaterial,
                   unbraced_length: float = None) -> Dict:
        """
        Design steel beam according to AISC 360
        """
        logger.info(f"Designing beam {element.id} per AISC 360")
        
        # Extract forces
        Mu = max(abs(forces.get('moment_y', 0)), abs(forces.get('moment_z', 0)))  # kip-in
        Vu = max(abs(forces.get('shear_y', 0)), abs(forces.get('shear_z', 0)))   # kip
        Pu = abs(forces.get('axial', 0))  # kip (compression positive)
        
        # Material properties
        Fy = material.yield_strength  # ksi
        Fu = material.ultimate_strength  # ksi
        E = material.elastic_modulus  # ksi
        
        # Section properties
        d = section.depth  # in
        bf = section.flange_width  # in
        tf = section.flange_thickness  # in
        tw = section.web_thickness  # in
        Ix = section.moment_of_inertia_x  # in^4
        Sx = section.section_modulus_x  # in^3
        Zx = section.plastic_section_modulus_x  # in^3
        rx = section.radius_of_gyration_x  # in
        ry = section.radius_of_gyration_y  # in
        
        # Unbraced length
        if unbraced_length is None:
            Lb = element.length * 12  # Convert to inches
        else:
            Lb = unbraced_length * 12
        
        results = {
            "element_id": element.id,
            "code": self.code_name,
            "forces": {
                "Mu": Mu,
                "Vu": Vu, 
                "Pu": Pu
            }
        }
        
        # Flexural design
        if Mu > 0:
            flexural_results = self._design_flexure(Mu, section, material, Lb)
            results["flexural"] = flexural_results
        
        # Shear design
        if Vu > 0:
            shear_results = self._design_shear(Vu, section, material)
            results["shear"] = shear_results
        
        # Combined loading check
        if Mu > 0 and Pu > 0:
            interaction_results = self._check_beam_column_interaction(
                Pu, Mu, section, material, Lb
            )
            results["interaction"] = interaction_results
        
        # Overall adequacy
        results["adequate"] = self._check_overall_adequacy(results)
        
        return results
    
    def design_column(self,
                     element: Element,
                     forces: Dict,
                     section: SteelSection,
                     material: SteelMaterial,
                     effective_length_x: float = None,
                     effective_length_y: float = None) -> Dict:
        """
        Design steel column according to AISC 360
        """
        logger.info(f"Designing column {element.id} per AISC 360")
        
        # Extract forces
        Pu = abs(forces.get('axial', 0))  # kip (compression)
        Mux = abs(forces.get('moment_x', 0))  # kip-in
        Muy = abs(forces.get('moment_y', 0))  # kip-in
        
        # Effective lengths
        if effective_length_x is None:
            Lx = element.length * 12  # Convert to inches
        else:
            Lx = effective_length_x * 12
            
        if effective_length_y is None:
            Ly = element.length * 12
        else:
            Ly = effective_length_y * 12
        
        results = {
            "element_id": element.id,
            "code": self.code_name,
            "forces": {
                "Pu": Pu,
                "Mux": Mux,
                "Muy": Muy
            }
        }
        
        # Compression design
        if Pu > 0:
            compression_results = self._design_compression(Pu, section, material, Lx, Ly)
            results["compression"] = compression_results
        
        # Beam-column interaction
        if Pu > 0 and (Mux > 0 or Muy > 0):
            interaction_results = self._check_beam_column_interaction_biaxial(
                Pu, Mux, Muy, section, material, Lx, Ly
            )
            results["interaction"] = interaction_results
        
        results["adequate"] = self._check_overall_adequacy(results)
        
        return results
    
    def _design_flexure(self, 
                       Mu: float,
                       section: SteelSection,
                       material: SteelMaterial,
                       Lb: float) -> Dict:
        """
        Design for flexure per AISC 360 Chapter F
        """
        Fy = material.yield_strength
        E = material.elastic_modulus
        
        # Section properties
        Zx = section.plastic_section_modulus_x
        Sx = section.section_modulus_x
        ry = section.radius_of_gyration_y
        
        # Lateral-torsional buckling parameters
        Mp = Fy * Zx  # Plastic moment
        
        # Limiting laterally unbraced lengths
        Lp = 1.76 * ry * math.sqrt(E / Fy)  # Compact limit
        
        # For simplicity, assume doubly symmetric I-shape
        c = 1.0  # For doubly symmetric sections
        Sx_c = Sx  # Section modulus about x-axis
        J = section.torsional_constant if hasattr(section, 'torsional_constant') else 0.1
        ho = section.depth - section.flange_thickness  # Distance between flange centroids
        
        # Elastic lateral-torsional buckling moment
        Lr = 1.95 * ry * (E / (0.7 * Fy)) * math.sqrt(J * c / (Sx_c * ho) + 
                                                       math.sqrt((J * c / (Sx_c * ho))**2 + 
                                                               6.76 * (0.7 * Fy / E)**2))
        
        # Determine nominal flexural strength
        if Lb <= Lp:
            # Compact section, full plastic moment
            Mn = Mp
            limit_state = "Yielding"
        elif Lb <= Lr:
            # Inelastic lateral-torsional buckling
            Cb = 1.0  # Conservative assumption
            Mn = Cb * (Mp - (Mp - 0.7 * Fy * Sx) * (Lb - Lp) / (Lr - Lp))
            limit_state = "Inelastic LTB"
        else:
            # Elastic lateral-torsional buckling
            Cb = 1.0
            Fcr = (Cb * math.pi**2 * E) / ((Lb / ry)**2) * math.sqrt(1 + 0.078 * (J * c / (Sx_c * ho)) * (Lb / ry)**2)
            Mn = Fcr * Sx
            limit_state = "Elastic LTB"
        
        # Design strength
        phi_Mn = self.phi_b * Mn
        
        # Demand-to-capacity ratio
        DCR = Mu / phi_Mn if phi_Mn > 0 else float('inf')
        
        return {
            "Mn": Mn,
            "phi_Mn": phi_Mn,
            "Mu": Mu,
            "DCR": DCR,
            "limit_state": limit_state,
            "Lb": Lb,
            "Lp": Lp,
            "Lr": Lr,
            "adequate": DCR <= 1.0
        }
    
    def _design_shear(self,
                     Vu: float,
                     section: SteelSection,
                     material: SteelMaterial) -> Dict:
        """
        Design for shear per AISC 360 Chapter G
        """
        Fy = material.yield_strength
        E = material.elastic_modulus
        
        # Web properties
        h = section.depth - 2 * section.flange_thickness  # Clear height of web
        tw = section.web_thickness
        
        # Web slenderness
        h_tw = h / tw
        
        # Shear buckling coefficient
        kv = 5.0  # For unstiffened webs
        
        # Critical web slenderness ratios
        lambda_w1 = 1.10 * math.sqrt(kv * E / Fy)
        lambda_w2 = 1.37 * math.sqrt(kv * E / Fy)
        
        # Nominal shear strength
        Aw = section.depth * tw  # Web area
        
        if h_tw <= lambda_w1:
            # Web yielding
            Vn = 0.6 * Fy * Aw
            limit_state = "Shear yielding"
        elif h_tw <= lambda_w2:
            # Inelastic shear buckling
            Vn = 0.6 * Fy * Aw * (lambda_w1 / (h_tw))
            limit_state = "Inelastic shear buckling"
        else:
            # Elastic shear buckling
            Vn = 0.6 * Fy * Aw * (lambda_w1 / (h_tw))**2
            limit_state = "Elastic shear buckling"
        
        # Design strength
        phi_Vn = self.phi_v * Vn
        
        # Demand-to-capacity ratio
        DCR = Vu / phi_Vn if phi_Vn > 0 else float('inf')
        
        return {
            "Vn": Vn,
            "phi_Vn": phi_Vn,
            "Vu": Vu,
            "DCR": DCR,
            "limit_state": limit_state,
            "h_tw": h_tw,
            "adequate": DCR <= 1.0
        }
    
    def _design_compression(self,
                           Pu: float,
                           section: SteelSection,
                           material: SteelMaterial,
                           Lx: float,
                           Ly: float) -> Dict:
        """
        Design for compression per AISC 360 Chapter E
        """
        Fy = material.yield_strength
        E = material.elastic_modulus
        
        # Section properties
        A = section.area
        rx = section.radius_of_gyration_x
        ry = section.radius_of_gyration_y
        
        # Slenderness ratios
        KL_r_x = Lx / rx  # Assuming K = 1.0
        KL_r_y = Ly / ry
        KL_r = max(KL_r_x, KL_r_y)  # Governing slenderness ratio
        
        # Elastic buckling stress
        Fe = math.pi**2 * E / (KL_r)**2
        
        # Critical stress
        lambda_c = math.sqrt(Fy / Fe)
        
        if lambda_c <= 1.5:
            # Inelastic buckling
            Fcr = (0.658**(lambda_c**2)) * Fy
            limit_state = "Inelastic buckling"
        else:
            # Elastic buckling
            Fcr = 0.877 * Fe
            limit_state = "Elastic buckling"
        
        # Nominal compressive strength
        Pn = Fcr * A
        
        # Design strength
        phi_Pn = self.phi_c * Pn
        
        # Demand-to-capacity ratio
        DCR = Pu / phi_Pn if phi_Pn > 0 else float('inf')
        
        return {
            "Pn": Pn,
            "phi_Pn": phi_Pn,
            "Pu": Pu,
            "DCR": DCR,
            "limit_state": limit_state,
            "KL_r": KL_r,
            "Fcr": Fcr,
            "adequate": DCR <= 1.0
        }
    
    def _check_beam_column_interaction(self,
                                      Pu: float,
                                      Mu: float,
                                      section: SteelSection,
                                      material: SteelMaterial,
                                      Lb: float) -> Dict:
        """
        Check beam-column interaction per AISC 360 Chapter H
        """
        # Get individual capacities
        compression_results = self._design_compression(Pu, section, material, Lb, Lb)
        flexural_results = self._design_flexure(Mu, section, material, Lb)
        
        phi_Pn = compression_results["phi_Pn"]
        phi_Mn = flexural_results["phi_Mn"]
        
        # Interaction equations
        if Pu / phi_Pn >= 0.2:
            # Equation H1-1a
            interaction_ratio = Pu / phi_Pn + (8.0/9.0) * (Mu / phi_Mn)
        else:
            # Equation H1-1b
            interaction_ratio = Pu / (2.0 * phi_Pn) + Mu / phi_Mn
        
        return {
            "interaction_ratio": interaction_ratio,
            "equation_used": "H1-1a" if Pu / phi_Pn >= 0.2 else "H1-1b",
            "adequate": interaction_ratio <= 1.0,
            "phi_Pn": phi_Pn,
            "phi_Mn": phi_Mn
        }
    
    def _check_beam_column_interaction_biaxial(self,
                                              Pu: float,
                                              Mux: float,
                                              Muy: float,
                                              section: SteelSection,
                                              material: SteelMaterial,
                                              Lx: float,
                                              Ly: float) -> Dict:
        """
        Check biaxial beam-column interaction
        """
        # This is a simplified implementation
        # Full biaxial interaction is more complex
        
        compression_results = self._design_compression(Pu, section, material, Lx, Ly)
        phi_Pn = compression_results["phi_Pn"]
        
        # Approximate flexural capacities
        Zx = section.plastic_section_modulus_x
        Zy = getattr(section, 'plastic_section_modulus_y', Zx * 0.5)  # Approximate
        
        phi_Mnx = self.phi_b * material.yield_strength * Zx
        phi_Mny = self.phi_b * material.yield_strength * Zy
        
        # Simplified interaction equation
        if Pu / phi_Pn >= 0.2:
            interaction_ratio = Pu / phi_Pn + (8.0/9.0) * (Mux / phi_Mnx + Muy / phi_Mny)
        else:
            interaction_ratio = Pu / (2.0 * phi_Pn) + (Mux / phi_Mnx + Muy / phi_Mny)
        
        return {
            "interaction_ratio": interaction_ratio,
            "adequate": interaction_ratio <= 1.0,
            "phi_Pn": phi_Pn,
            "phi_Mnx": phi_Mnx,
            "phi_Mny": phi_Mny
        }
    
    def _check_overall_adequacy(self, results: Dict) -> bool:
        """
        Check overall adequacy of the design
        """
        adequate = True
        
        # Check individual limit states
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
        summary = f"AISC 360 Design Summary for Element {results['element_id']}\n"
        summary += "=" * 50 + "\n\n"
        
        # Forces
        forces = results["forces"]
        summary += f"Applied Forces:\n"
        summary += f"  Axial: {forces.get('Pu', 0):.1f} kip\n"
        summary += f"  Moment: {forces.get('Mu', 0):.1f} kip-in\n"
        summary += f"  Shear: {forces.get('Vu', 0):.1f} kip\n\n"
        
        # Design results
        if "flexural" in results:
            flex = results["flexural"]
            summary += f"Flexural Design:\n"
            summary += f"  φMn = {flex['phi_Mn']:.1f} kip-in\n"
            summary += f"  DCR = {flex['DCR']:.3f}\n"
            summary += f"  Limit State: {flex['limit_state']}\n\n"
        
        if "shear" in results:
            shear = results["shear"]
            summary += f"Shear Design:\n"
            summary += f"  φVn = {shear['phi_Vn']:.1f} kip\n"
            summary += f"  DCR = {shear['DCR']:.3f}\n"
            summary += f"  Limit State: {shear['limit_state']}\n\n"
        
        if "compression" in results:
            comp = results["compression"]
            summary += f"Compression Design:\n"
            summary += f"  φPn = {comp['phi_Pn']:.1f} kip\n"
            summary += f"  DCR = {comp['DCR']:.3f}\n"
            summary += f"  Limit State: {comp['limit_state']}\n\n"
        
        if "interaction" in results:
            inter = results["interaction"]
            summary += f"Interaction Check:\n"
            summary += f"  Interaction Ratio = {inter['interaction_ratio']:.3f}\n"
            summary += f"  Equation: {inter.get('equation_used', 'N/A')}\n\n"
        
        # Overall result
        summary += f"Overall Result: {'ADEQUATE' if results['adequate'] else 'NOT ADEQUATE'}\n"
        
        return summary