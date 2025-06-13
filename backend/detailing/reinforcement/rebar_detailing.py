"""
Reinforcement detailing for concrete elements
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

from ...core.modeling.elements import Element
from ...core.modeling.materials import ConcreteMaterial, SteelMaterial
from ...db.models.design import ConcreteDesignResult

logger = logging.getLogger(__name__)


class RebarDetailing:
    """
    Reinforcement detailing for concrete structural elements
    """
    
    def __init__(self):
        self.cover = 40  # mm, concrete cover
        self.min_bar_spacing = 25  # mm
        self.max_bar_spacing = 300  # mm
        self.standard_bar_sizes = [8, 10, 12, 16, 20, 25, 32, 40]  # mm
        
    def detail_beam_reinforcement(self, 
                                 element: Element,
                                 design_result: ConcreteDesignResult,
                                 concrete: ConcreteMaterial,
                                 steel: SteelMaterial) -> Dict:
        """
        Detail reinforcement for concrete beam
        """
        logger.info(f"Detailing beam reinforcement for element: {element.id}")
        
        # Extract design requirements
        As_req_pos = design_result.reinforcement_area_positive  # mm²
        As_req_neg = design_result.reinforcement_area_negative  # mm²
        Av_req = design_result.shear_reinforcement_area  # mm²/m
        
        # Beam dimensions
        width = element.section.width  # mm
        depth = element.section.depth  # mm
        length = element.length * 1000  # Convert to mm
        
        # Design longitudinal reinforcement
        main_rebar_pos = self._design_main_reinforcement(As_req_pos, width, depth, "bottom")
        main_rebar_neg = self._design_main_reinforcement(As_req_neg, width, depth, "top")
        
        # Design shear reinforcement
        shear_rebar = self._design_shear_reinforcement(Av_req, width, depth, length)
        
        # Generate bar bending schedule
        bar_schedule = self._generate_bar_schedule([main_rebar_pos, main_rebar_neg, shear_rebar])
        
        # Calculate development lengths
        development_lengths = self._calculate_development_lengths(
            main_rebar_pos, main_rebar_neg, concrete, steel
        )
        
        detailing_result = {
            "element_id": element.id,
            "main_reinforcement": {
                "positive": main_rebar_pos,
                "negative": main_rebar_neg
            },
            "shear_reinforcement": shear_rebar,
            "development_lengths": development_lengths,
            "bar_schedule": bar_schedule,
            "total_steel_weight": self._calculate_total_steel_weight(bar_schedule),
            "reinforcement_ratio": self._calculate_reinforcement_ratio(
                As_req_pos + As_req_neg, width, depth
            )
        }
        
        return detailing_result
    
    def detail_column_reinforcement(self,
                                   element: Element,
                                   design_result: ConcreteDesignResult,
                                   concrete: ConcreteMaterial,
                                   steel: SteelMaterial) -> Dict:
        """
        Detail reinforcement for concrete column
        """
        logger.info(f"Detailing column reinforcement for element: {element.id}")
        
        # Extract design requirements
        As_req = design_result.reinforcement_area_total  # mm²
        
        # Column dimensions
        width = element.section.width  # mm
        depth = element.section.depth  # mm
        height = element.length * 1000  # Convert to mm
        
        # Design main reinforcement
        main_rebar = self._design_column_main_reinforcement(As_req, width, depth)
        
        # Design ties/stirrups
        ties = self._design_column_ties(width, depth, main_rebar["bar_size"])
        
        # Generate bar schedule
        bar_schedule = self._generate_bar_schedule([main_rebar, ties])
        
        # Calculate splice lengths
        splice_lengths = self._calculate_splice_lengths(main_rebar, concrete, steel)
        
        detailing_result = {
            "element_id": element.id,
            "main_reinforcement": main_rebar,
            "ties": ties,
            "splice_lengths": splice_lengths,
            "bar_schedule": bar_schedule,
            "total_steel_weight": self._calculate_total_steel_weight(bar_schedule),
            "reinforcement_ratio": self._calculate_reinforcement_ratio(
                As_req, width, depth
            )
        }
        
        return detailing_result
    
    def detail_slab_reinforcement(self,
                                 element: Element,
                                 design_result: ConcreteDesignResult,
                                 concrete: ConcreteMaterial,
                                 steel: SteelMaterial) -> Dict:
        """
        Detail reinforcement for concrete slab
        """
        logger.info(f"Detailing slab reinforcement for element: {element.id}")
        
        # Extract design requirements
        As_req_x = design_result.reinforcement_area_x  # mm²/m
        As_req_y = design_result.reinforcement_area_y  # mm²/m
        
        # Slab dimensions
        thickness = element.section.thickness  # mm
        
        # Design reinforcement in both directions
        rebar_x = self._design_slab_reinforcement(As_req_x, thickness, "x-direction")
        rebar_y = self._design_slab_reinforcement(As_req_y, thickness, "y-direction")
        
        # Generate bar schedule
        bar_schedule = self._generate_bar_schedule([rebar_x, rebar_y])
        
        detailing_result = {
            "element_id": element.id,
            "reinforcement_x": rebar_x,
            "reinforcement_y": rebar_y,
            "bar_schedule": bar_schedule,
            "total_steel_weight": self._calculate_total_steel_weight(bar_schedule),
            "reinforcement_ratio_x": As_req_x / (1000 * thickness),
            "reinforcement_ratio_y": As_req_y / (1000 * thickness)
        }
        
        return detailing_result
    
    def _design_main_reinforcement(self, 
                                  As_req: float,
                                  width: float,
                                  depth: float,
                                  location: str) -> Dict:
        """
        Design main reinforcement for beam
        """
        if As_req <= 0:
            return {
                "bar_size": 0,
                "bar_count": 0,
                "area_provided": 0,
                "spacing": 0,
                "location": location
            }
        
        # Try different bar sizes to find optimal arrangement
        best_arrangement = None
        min_cost = float('inf')
        
        for bar_size in self.standard_bar_sizes:
            bar_area = math.pi * (bar_size/2)**2  # mm²
            
            # Calculate number of bars needed
            num_bars = math.ceil(As_req / bar_area)
            
            # Check if bars fit in the section
            available_width = width - 2 * self.cover - bar_size
            min_spacing = max(bar_size, self.min_bar_spacing)
            required_width = (num_bars - 1) * min_spacing
            
            if required_width <= available_width:
                # Calculate actual spacing
                if num_bars > 1:
                    spacing = available_width / (num_bars - 1)
                else:
                    spacing = 0
                
                # Calculate cost (simplified: based on total steel volume)
                total_area = num_bars * bar_area
                cost = total_area * bar_size  # Larger bars cost more per unit area
                
                if cost < min_cost:
                    min_cost = cost
                    best_arrangement = {
                        "bar_size": bar_size,
                        "bar_count": num_bars,
                        "area_provided": total_area,
                        "spacing": spacing,
                        "location": location
                    }
        
        if best_arrangement is None:
            # Use multiple layers if needed
            logger.warning(f"Single layer reinforcement not sufficient for As_req = {As_req}")
            # Implement multi-layer logic here
            best_arrangement = {
                "bar_size": self.standard_bar_sizes[-1],  # Use largest bar
                "bar_count": math.ceil(As_req / (math.pi * (self.standard_bar_sizes[-1]/2)**2)),
                "area_provided": As_req * 1.1,  # 10% extra
                "spacing": self.min_bar_spacing,
                "location": location,
                "layers": 2
            }
        
        return best_arrangement
    
    def _design_shear_reinforcement(self,
                                   Av_req: float,
                                   width: float,
                                   depth: float,
                                   length: float) -> Dict:
        """
        Design shear reinforcement (stirrups) for beam
        """
        if Av_req <= 0:
            # Minimum shear reinforcement
            Av_req = 0.75 * math.sqrt(25) * width / 420  # Minimum as per code
        
        # Standard stirrup configurations
        stirrup_configs = [
            {"legs": 2, "bar_size": 8},
            {"legs": 2, "bar_size": 10},
            {"legs": 4, "bar_size": 8},
            {"legs": 4, "bar_size": 10}
        ]
        
        best_config = None
        min_cost = float('inf')
        
        for config in stirrup_configs:
            bar_area = math.pi * (config["bar_size"]/2)**2  # mm²
            Av_provided_per_stirrup = config["legs"] * bar_area
            
            # Calculate required spacing
            spacing = Av_provided_per_stirrup / Av_req * 1000  # mm
            
            # Check spacing limits
            max_spacing = min(depth/2, 300)  # mm
            min_spacing = max(config["bar_size"] * 8, 75)  # mm
            
            if min_spacing <= spacing <= max_spacing:
                # Calculate number of stirrups
                num_stirrups = math.ceil(length / spacing)
                
                # Calculate stirrup length (perimeter + hooks)
                stirrup_length = 2 * (width + depth - 4 * self.cover) + 2 * 150  # mm (150mm for hooks)
                
                # Calculate cost
                total_length = num_stirrups * stirrup_length
                cost = total_length * config["bar_size"]
                
                if cost < min_cost:
                    min_cost = cost
                    best_config = {
                        "bar_size": config["bar_size"],
                        "legs": config["legs"],
                        "spacing": spacing,
                        "area_provided": Av_provided_per_stirrup,
                        "stirrup_length": stirrup_length,
                        "num_stirrups": num_stirrups
                    }
        
        if best_config is None:
            # Use minimum configuration
            best_config = {
                "bar_size": 8,
                "legs": 2,
                "spacing": 200,  # mm
                "area_provided": 2 * math.pi * (8/2)**2,
                "stirrup_length": 2 * (width + depth - 4 * self.cover) + 300,
                "num_stirrups": math.ceil(length / 200)
            }
        
        return best_config
    
    def _design_column_main_reinforcement(self,
                                         As_req: float,
                                         width: float,
                                         depth: float) -> Dict:
        """
        Design main reinforcement for column
        """
        # Minimum reinforcement ratio
        min_ratio = 0.01
        gross_area = width * depth
        As_min = min_ratio * gross_area
        As_req = max(As_req, As_min)
        
        # Try different bar arrangements
        arrangements = []
        
        for bar_size in self.standard_bar_sizes:
            bar_area = math.pi * (bar_size/2)**2
            num_bars = math.ceil(As_req / bar_area)
            
            # Check minimum number of bars (4 for rectangular columns)
            num_bars = max(num_bars, 4)
            
            # Check if bars fit
            if self._check_column_bar_fit(num_bars, bar_size, width, depth):
                arrangements.append({
                    "bar_size": bar_size,
                    "bar_count": num_bars,
                    "area_provided": num_bars * bar_area,
                    "arrangement": self._get_column_bar_arrangement(num_bars, width, depth)
                })
        
        # Select best arrangement (minimum steel area that satisfies requirements)
        best_arrangement = min(arrangements, key=lambda x: x["area_provided"])
        
        return best_arrangement
    
    def _design_column_ties(self,
                           width: float,
                           depth: float,
                           main_bar_size: float) -> Dict:
        """
        Design ties for column
        """
        # Tie bar size (typically 1/4 of main bar size, minimum 6mm)
        tie_size = max(6, main_bar_size / 4)
        tie_size = min(self.standard_bar_sizes, key=lambda x: abs(x - tie_size))
        
        # Tie spacing
        spacing = min(
            16 * main_bar_size,  # 16 times main bar diameter
            48 * tie_size,       # 48 times tie bar diameter
            min(width, depth),   # Least dimension of column
            300                  # Maximum 300mm
        )
        
        # Tie configuration
        tie_length = 2 * (width + depth - 4 * self.cover) + 2 * 150  # mm (150mm for hooks)
        
        return {
            "bar_size": tie_size,
            "spacing": spacing,
            "tie_length": tie_length,
            "hook_length": 150
        }
    
    def _design_slab_reinforcement(self,
                                  As_req: float,
                                  thickness: float,
                                  direction: str) -> Dict:
        """
        Design reinforcement for slab in one direction
        """
        # Try different bar sizes and spacings
        best_arrangement = None
        min_cost = float('inf')
        
        for bar_size in self.standard_bar_sizes[:6]:  # Use smaller bars for slabs
            bar_area = math.pi * (bar_size/2)**2  # mm²
            
            # Calculate required spacing for 1m width
            spacing = bar_area * 1000 / As_req  # mm
            
            # Check spacing limits
            max_spacing = min(3 * thickness, 400)  # mm
            min_spacing = max(bar_size, 75)  # mm
            
            if min_spacing <= spacing <= max_spacing:
                # Calculate actual area provided
                area_provided = bar_area * 1000 / spacing  # mm²/m
                
                # Calculate cost (steel volume per m²)
                cost = area_provided * bar_size
                
                if cost < min_cost:
                    min_cost = cost
                    best_arrangement = {
                        "bar_size": bar_size,
                        "spacing": spacing,
                        "area_provided": area_provided,
                        "direction": direction
                    }
        
        if best_arrangement is None:
            # Use minimum reinforcement
            bar_size = 10  # mm
            spacing = 200  # mm
            bar_area = math.pi * (bar_size/2)**2
            best_arrangement = {
                "bar_size": bar_size,
                "spacing": spacing,
                "area_provided": bar_area * 1000 / spacing,
                "direction": direction
            }
        
        return best_arrangement
    
    def _check_column_bar_fit(self,
                             num_bars: int,
                             bar_size: float,
                             width: float,
                             depth: float) -> bool:
        """
        Check if bars fit in column section
        """
        # Simplified check - assumes bars are arranged around perimeter
        perimeter_space = 2 * (width + depth - 4 * self.cover - 2 * bar_size)
        required_space = num_bars * (bar_size + self.min_bar_spacing)
        
        return required_space <= perimeter_space
    
    def _get_column_bar_arrangement(self,
                                   num_bars: int,
                                   width: float,
                                   depth: float) -> str:
        """
        Get description of column bar arrangement
        """
        if num_bars == 4:
            return "4 bars at corners"
        elif num_bars <= 8:
            return f"{num_bars} bars around perimeter"
        else:
            return f"{num_bars} bars in multiple layers"
    
    def _calculate_development_lengths(self,
                                      main_rebar_pos: Dict,
                                      main_rebar_neg: Dict,
                                      concrete: ConcreteMaterial,
                                      steel: SteelMaterial) -> Dict:
        """
        Calculate development lengths for reinforcement
        """
        fck = concrete.compressive_strength  # MPa
        fy = steel.yield_strength  # MPa
        
        development_lengths = {}
        
        for location, rebar in [("positive", main_rebar_pos), ("negative", main_rebar_neg)]:
            if rebar["bar_count"] > 0:
                db = rebar["bar_size"]  # mm
                
                # Basic development length (simplified formula)
                ld_basic = (fy * db) / (4 * math.sqrt(fck))
                
                # Modification factors (simplified)
                alpha = 1.0  # Bar location factor
                beta = 1.0   # Coating factor
                gamma = 1.0  # Bar size factor
                lambda_factor = 1.0  # Lightweight concrete factor
                
                ld = ld_basic * alpha * beta * gamma * lambda_factor
                
                # Minimum development length
                ld_min = max(300, 12 * db)  # mm
                ld = max(ld, ld_min)
                
                development_lengths[location] = {
                    "basic_length": ld_basic,
                    "design_length": ld,
                    "minimum_length": ld_min
                }
        
        return development_lengths
    
    def _calculate_splice_lengths(self,
                                 main_rebar: Dict,
                                 concrete: ConcreteMaterial,
                                 steel: SteelMaterial) -> Dict:
        """
        Calculate splice lengths for column reinforcement
        """
        if main_rebar["bar_count"] == 0:
            return {}
        
        fck = concrete.compressive_strength  # MPa
        fy = steel.yield_strength  # MPa
        db = main_rebar["bar_size"]  # mm
        
        # Compression splice length
        lsc = max(
            0.24 * fy * db / math.sqrt(fck),
            0.043 * fy * db,
            200  # mm minimum
        )
        
        # Tension splice length (typically 1.3 times compression splice)
        lst = 1.3 * lsc
        
        return {
            "compression_splice": lsc,
            "tension_splice": lst,
            "bar_size": db
        }
    
    def _generate_bar_schedule(self, rebar_groups: List[Dict]) -> List[Dict]:
        """
        Generate bar bending schedule
        """
        schedule = []
        mark_number = 1
        
        for group in rebar_groups:
            if group.get("bar_count", 0) > 0:
                schedule_item = {
                    "mark": f"R{mark_number}",
                    "bar_size": group["bar_size"],
                    "quantity": group["bar_count"],
                    "length": self._calculate_bar_length(group),
                    "total_length": group["bar_count"] * self._calculate_bar_length(group),
                    "weight": self._calculate_bar_weight(group),
                    "shape": self._get_bar_shape(group)
                }
                schedule.append(schedule_item)
                mark_number += 1
        
        return schedule
    
    def _calculate_bar_length(self, rebar: Dict) -> float:
        """
        Calculate individual bar length including hooks and bends
        """
        # This is simplified - actual calculation depends on bar shape and hooks
        base_length = rebar.get("length", 6000)  # mm, default 6m
        
        # Add hook lengths if applicable
        if "hook_length" in rebar:
            base_length += 2 * rebar["hook_length"]
        
        return base_length
    
    def _calculate_bar_weight(self, rebar: Dict) -> float:
        """
        Calculate weight of reinforcement group
        """
        bar_size = rebar["bar_size"]  # mm
        bar_count = rebar["bar_count"]
        bar_length = self._calculate_bar_length(rebar)  # mm
        
        # Steel density: 7850 kg/m³
        bar_area = math.pi * (bar_size/2)**2  # mm²
        volume = bar_area * bar_length * bar_count  # mm³
        weight = volume * 7.85e-6  # kg (7850 kg/m³ = 7.85e-6 kg/mm³)
        
        return weight
    
    def _get_bar_shape(self, rebar: Dict) -> str:
        """
        Get bar shape description
        """
        if "stirrup_length" in rebar:
            return "Rectangular stirrup"
        elif rebar.get("location") == "top":
            return "Straight with hooks"
        elif rebar.get("location") == "bottom":
            return "Straight"
        else:
            return "Straight"
    
    def _calculate_total_steel_weight(self, bar_schedule: List[Dict]) -> float:
        """
        Calculate total steel weight from bar schedule
        """
        return sum(item["weight"] for item in bar_schedule)
    
    def _calculate_reinforcement_ratio(self,
                                      As_provided: float,
                                      width: float,
                                      depth: float) -> float:
        """
        Calculate reinforcement ratio
        """
        gross_area = width * depth  # mm²
        return As_provided / gross_area if gross_area > 0 else 0