"""
Section library and calculator for structural cross-sections
"""

import math
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from db.models.structural import Section, SectionType
from core.exceptions import ModelError, ValidationError


@dataclass
class SectionProperties:
    """Section properties container"""
    name: str
    section_type: SectionType
    designation: str
    
    # Geometric properties
    area: float  # m²
    moment_inertia_y: float  # m⁴
    moment_inertia_z: float  # m⁴
    moment_inertia_x: Optional[float] = None  # m⁴ (torsional)
    section_modulus_y: Optional[float] = None  # m³
    section_modulus_z: Optional[float] = None  # m³
    radius_gyration_y: Optional[float] = None  # m
    radius_gyration_z: Optional[float] = None  # m
    
    # Shear properties
    shear_area_y: Optional[float] = None  # m²
    shear_area_z: Optional[float] = None  # m²
    
    # Dimensions
    dimensions: Dict[str, float] = None
    
    # Additional properties
    additional_properties: Optional[Dict[str, Any]] = None


class SectionCalculator:
    """Calculator for section properties"""
    
    @staticmethod
    def calculate_rectangular_section(width: float, height: float) -> SectionProperties:
        """Calculate properties for rectangular section"""
        if width <= 0 or height <= 0:
            raise ModelError("Width and height must be positive")
        
        area = width * height
        iy = width * height**3 / 12  # About y-axis (strong axis)
        iz = height * width**3 / 12  # About z-axis (weak axis)
        
        # Section moduli
        sy = iy / (height / 2)
        sz = iz / (width / 2)
        
        # Radii of gyration
        ry = math.sqrt(iy / area)
        rz = math.sqrt(iz / area)
        
        # Torsional constant (approximate for rectangle)
        if width >= height:
            a, b = width, height
        else:
            a, b = height, width
        
        beta = b / a
        if beta <= 0.5:
            alpha = 0.333 * (1 - 0.21 * beta * (1 - beta**4 / 12))
        else:
            alpha = 0.333 * (1 - 0.105 * beta * (1 - beta**4 / 12))
        
        j = alpha * a * b**3
        
        # Shear areas (approximate)
        shear_area_y = 5/6 * area  # For shear in y-direction
        shear_area_z = 5/6 * area  # For shear in z-direction
        
        return SectionProperties(
            name=f"Rectangular {width*1000:.0f}x{height*1000:.0f}",
            section_type=SectionType.RECTANGULAR,
            designation=f"{width*1000:.0f}x{height*1000:.0f}",
            area=area,
            moment_inertia_y=iy,
            moment_inertia_z=iz,
            moment_inertia_x=j,
            section_modulus_y=sy,
            section_modulus_z=sz,
            radius_gyration_y=ry,
            radius_gyration_z=rz,
            shear_area_y=shear_area_y,
            shear_area_z=shear_area_z,
            dimensions={
                "width": width,
                "height": height
            }
        )
    
    @staticmethod
    def calculate_circular_section(diameter: float) -> SectionProperties:
        """Calculate properties for circular section"""
        if diameter <= 0:
            raise ModelError("Diameter must be positive")
        
        radius = diameter / 2
        area = math.pi * radius**2
        i = math.pi * radius**4 / 4  # Same for both axes
        j = math.pi * radius**4 / 2  # Torsional constant
        
        # Section modulus
        s = i / radius
        
        # Radius of gyration
        r_gyration = radius / 2
        
        # Shear area
        shear_area = 9 * area / 10  # For circular sections
        
        return SectionProperties(
            name=f"Circular D{diameter*1000:.0f}",
            section_type=SectionType.CIRCULAR,
            designation=f"D{diameter*1000:.0f}",
            area=area,
            moment_inertia_y=i,
            moment_inertia_z=i,
            moment_inertia_x=j,
            section_modulus_y=s,
            section_modulus_z=s,
            radius_gyration_y=r_gyration,
            radius_gyration_z=r_gyration,
            shear_area_y=shear_area,
            shear_area_z=shear_area,
            dimensions={
                "diameter": diameter
            }
        )
    
    @staticmethod
    def calculate_i_section(depth: float, width: float, flange_thickness: float, 
                          web_thickness: float) -> SectionProperties:
        """Calculate properties for I-section"""
        if any(dim <= 0 for dim in [depth, width, flange_thickness, web_thickness]):
            raise ModelError("All dimensions must be positive")
        
        if flange_thickness >= depth / 2:
            raise ModelError("Flange thickness too large for given depth")
        
        if web_thickness >= width:
            raise ModelError("Web thickness too large for given width")
        
        # Area calculation
        flange_area = 2 * width * flange_thickness
        web_area = (depth - 2 * flange_thickness) * web_thickness
        area = flange_area + web_area
        
        # Moment of inertia about y-axis (strong axis)
        # Flanges contribution
        flange_centroid_distance = (depth - flange_thickness) / 2
        iy_flanges = 2 * (width * flange_thickness**3 / 12 + 
                         width * flange_thickness * flange_centroid_distance**2)
        
        # Web contribution
        web_height = depth - 2 * flange_thickness
        iy_web = web_thickness * web_height**3 / 12
        
        iy = iy_flanges + iy_web
        
        # Moment of inertia about z-axis (weak axis)
        iz_flanges = 2 * flange_thickness * width**3 / 12
        iz_web = web_height * web_thickness**3 / 12
        iz = iz_flanges + iz_web
        
        # Section moduli
        sy = iy / (depth / 2)
        sz = iz / (width / 2)
        
        # Radii of gyration
        ry = math.sqrt(iy / area)
        rz = math.sqrt(iz / area)
        
        # Torsional constant (approximate)
        j = (2 * width * flange_thickness**3 + 
             (depth - 2 * flange_thickness) * web_thickness**3) / 3
        
        # Shear areas
        shear_area_y = area * web_thickness / width  # Approximate
        shear_area_z = area  # Conservative estimate
        
        return SectionProperties(
            name=f"I-Section {depth*1000:.0f}x{width*1000:.0f}x{flange_thickness*1000:.0f}x{web_thickness*1000:.0f}",
            section_type=SectionType.I_SECTION,
            designation=f"I{depth*1000:.0f}x{width*1000:.0f}",
            area=area,
            moment_inertia_y=iy,
            moment_inertia_z=iz,
            moment_inertia_x=j,
            section_modulus_y=sy,
            section_modulus_z=sz,
            radius_gyration_y=ry,
            radius_gyration_z=rz,
            shear_area_y=shear_area_y,
            shear_area_z=shear_area_z,
            dimensions={
                "depth": depth,
                "width": width,
                "flange_thickness": flange_thickness,
                "web_thickness": web_thickness
            }
        )
    
    @staticmethod
    def calculate_channel_section(depth: float, width: float, flange_thickness: float,
                                web_thickness: float) -> SectionProperties:
        """Calculate properties for channel section"""
        if any(dim <= 0 for dim in [depth, width, flange_thickness, web_thickness]):
            raise ModelError("All dimensions must be positive")
        
        # Area calculation
        flange_area = 2 * width * flange_thickness
        web_area = (depth - 2 * flange_thickness) * web_thickness
        area = flange_area + web_area
        
        # Centroid calculation (distance from web face)
        flange_moment = 2 * (width * flange_thickness) * (width / 2)
        web_moment = web_area * (web_thickness / 2)
        centroid_z = (flange_moment + web_moment) / area
        
        # Moment of inertia about y-axis (strong axis)
        iy_flanges = 2 * width * flange_thickness**3 / 12
        web_height = depth - 2 * flange_thickness
        iy_web = web_thickness * web_height**3 / 12
        iy = iy_flanges + iy_web
        
        # Moment of inertia about z-axis (weak axis) - about centroid
        iz_flanges = 2 * (flange_thickness * width**3 / 12 + 
                         width * flange_thickness * (width/2 - centroid_z)**2)
        iz_web = web_height * web_thickness**3 / 12 + web_area * (web_thickness/2 - centroid_z)**2
        iz = iz_flanges + iz_web
        
        # Section moduli
        sy = iy / (depth / 2)
        sz_left = iz / centroid_z
        sz_right = iz / (width - centroid_z)
        sz = min(sz_left, sz_right)  # Governing section modulus
        
        # Radii of gyration
        ry = math.sqrt(iy / area)
        rz = math.sqrt(iz / area)
        
        # Torsional constant (approximate)
        j = (2 * width * flange_thickness**3 + 
             (depth - 2 * flange_thickness) * web_thickness**3) / 3
        
        return SectionProperties(
            name=f"Channel {depth*1000:.0f}x{width*1000:.0f}x{flange_thickness*1000:.0f}x{web_thickness*1000:.0f}",
            section_type=SectionType.CHANNEL,
            designation=f"C{depth*1000:.0f}x{width*1000:.0f}",
            area=area,
            moment_inertia_y=iy,
            moment_inertia_z=iz,
            moment_inertia_x=j,
            section_modulus_y=sy,
            section_modulus_z=sz,
            radius_gyration_y=ry,
            radius_gyration_z=rz,
            dimensions={
                "depth": depth,
                "width": width,
                "flange_thickness": flange_thickness,
                "web_thickness": web_thickness,
                "centroid_z": centroid_z
            }
        )
    
    @staticmethod
    def calculate_tube_rectangular(width: float, height: float, thickness: float) -> SectionProperties:
        """Calculate properties for rectangular tube section"""
        if width <= 0 or height <= 0 or thickness <= 0:
            raise ModelError("All dimensions must be positive")
        
        if thickness >= min(width, height) / 2:
            raise ModelError("Wall thickness too large")
        
        # Outer and inner dimensions
        width_inner = width - 2 * thickness
        height_inner = height - 2 * thickness
        
        # Area calculation
        area_outer = width * height
        area_inner = width_inner * height_inner
        area = area_outer - area_inner
        
        # Moment of inertia
        iy_outer = width * height**3 / 12
        iy_inner = width_inner * height_inner**3 / 12
        iy = iy_outer - iy_inner
        
        iz_outer = height * width**3 / 12
        iz_inner = height_inner * width_inner**3 / 12
        iz = iz_outer - iz_inner
        
        # Section moduli
        sy = iy / (height / 2)
        sz = iz / (width / 2)
        
        # Radii of gyration
        ry = math.sqrt(iy / area)
        rz = math.sqrt(iz / area)
        
        # Torsional constant (thin-walled approximation)
        perimeter = 2 * (width_inner + height_inner)
        area_enclosed = width_inner * height_inner
        j = 4 * area_enclosed**2 * thickness / perimeter
        
        return SectionProperties(
            name=f"Rectangular Tube {width*1000:.0f}x{height*1000:.0f}x{thickness*1000:.0f}",
            section_type=SectionType.TUBE_RECTANGULAR,
            designation=f"RHS{width*1000:.0f}x{height*1000:.0f}x{thickness*1000:.0f}",
            area=area,
            moment_inertia_y=iy,
            moment_inertia_z=iz,
            moment_inertia_x=j,
            section_modulus_y=sy,
            section_modulus_z=sz,
            radius_gyration_y=ry,
            radius_gyration_z=rz,
            dimensions={
                "width": width,
                "height": height,
                "thickness": thickness,
                "width_inner": width_inner,
                "height_inner": height_inner
            }
        )
    
    @staticmethod
    def calculate_tube_circular(diameter: float, thickness: float) -> SectionProperties:
        """Calculate properties for circular tube section"""
        if diameter <= 0 or thickness <= 0:
            raise ModelError("Diameter and thickness must be positive")
        
        if thickness >= diameter / 2:
            raise ModelError("Wall thickness too large")
        
        # Outer and inner radii
        radius_outer = diameter / 2
        radius_inner = radius_outer - thickness
        
        # Area calculation
        area = math.pi * (radius_outer**2 - radius_inner**2)
        
        # Moment of inertia
        i = math.pi * (radius_outer**4 - radius_inner**4) / 4
        
        # Torsional constant
        j = math.pi * (radius_outer**4 - radius_inner**4) / 2
        
        # Section modulus
        s = i / radius_outer
        
        # Radius of gyration
        r_gyration = math.sqrt(i / area)
        
        return SectionProperties(
            name=f"Circular Tube D{diameter*1000:.0f}x{thickness*1000:.0f}",
            section_type=SectionType.TUBE_CIRCULAR,
            designation=f"CHS{diameter*1000:.0f}x{thickness*1000:.0f}",
            area=area,
            moment_inertia_y=i,
            moment_inertia_z=i,
            moment_inertia_x=j,
            section_modulus_y=s,
            section_modulus_z=s,
            radius_gyration_y=r_gyration,
            radius_gyration_z=r_gyration,
            dimensions={
                "diameter": diameter,
                "thickness": thickness,
                "diameter_inner": 2 * radius_inner
            }
        )


class SectionLibrary:
    """Library of standard sections"""
    
    def __init__(self):
        self.calculator = SectionCalculator()
        self.standard_sections = {}
        self._initialize_standard_sections()
    
    def _initialize_standard_sections(self):
        """Initialize library with standard sections"""
        # Add standard I-sections (AISC W-shapes)
        self._add_aisc_w_sections()
        
        # Add standard channels
        self._add_standard_channels()
        
        # Add standard tubes
        self._add_standard_tubes()
        
        # Add standard rectangular sections
        self._add_standard_rectangular()
    
    def _add_aisc_w_sections(self):
        """Add AISC W-shape sections"""
        # Common W-shapes with dimensions in meters
        w_shapes = {
            "W14x22": {"d": 0.349, "bf": 0.127, "tf": 0.0095, "tw": 0.0058},
            "W14x30": {"d": 0.355, "bf": 0.171, "tf": 0.0095, "tw": 0.0064},
            "W16x26": {"d": 0.399, "bf": 0.140, "tf": 0.0095, "tw": 0.0061},
            "W18x35": {"d": 0.449, "bf": 0.152, "tf": 0.0111, "tw": 0.0071},
            "W21x44": {"d": 0.525, "bf": 0.165, "tf": 0.0111, "tw": 0.0089},
            "W24x55": {"d": 0.603, "bf": 0.178, "tf": 0.0127, "tw": 0.0102},
        }
        
        for designation, dims in w_shapes.items():
            section = self.calculator.calculate_i_section(
                dims["d"], dims["bf"], dims["tf"], dims["tw"]
            )
            section.name = f"AISC {designation}"
            section.designation = designation
            self.standard_sections[f"aisc_{designation.lower()}"] = section
    
    def _add_standard_channels(self):
        """Add standard channel sections"""
        channels = {
            "C150x75": {"d": 0.150, "bf": 0.075, "tf": 0.008, "tw": 0.006},
            "C200x75": {"d": 0.200, "bf": 0.075, "tf": 0.009, "tw": 0.007},
            "C250x90": {"d": 0.250, "bf": 0.090, "tf": 0.010, "tw": 0.008},
        }
        
        for designation, dims in channels.items():
            section = self.calculator.calculate_channel_section(
                dims["d"], dims["bf"], dims["tf"], dims["tw"]
            )
            section.name = f"Channel {designation}"
            section.designation = designation
            self.standard_sections[f"channel_{designation.lower()}"] = section
    
    def _add_standard_tubes(self):
        """Add standard tube sections"""
        # Rectangular tubes
        rhs_sections = {
            "RHS100x50x5": {"w": 0.100, "h": 0.050, "t": 0.005},
            "RHS150x100x6": {"w": 0.150, "h": 0.100, "t": 0.006},
            "RHS200x100x8": {"w": 0.200, "h": 0.100, "t": 0.008},
        }
        
        for designation, dims in rhs_sections.items():
            section = self.calculator.calculate_tube_rectangular(
                dims["w"], dims["h"], dims["t"]
            )
            section.name = f"RHS {designation}"
            section.designation = designation
            self.standard_sections[f"rhs_{designation.lower()}"] = section
        
        # Circular tubes
        chs_sections = {
            "CHS89x5": {"d": 0.089, "t": 0.005},
            "CHS114x6": {"d": 0.114, "t": 0.006},
            "CHS168x8": {"d": 0.168, "t": 0.008},
        }
        
        for designation, dims in chs_sections.items():
            section = self.calculator.calculate_tube_circular(
                dims["d"], dims["t"]
            )
            section.name = f"CHS {designation}"
            section.designation = designation
            self.standard_sections[f"chs_{designation.lower()}"] = section
    
    def _add_standard_rectangular(self):
        """Add standard rectangular sections"""
        rectangles = {
            "300x500": {"w": 0.300, "h": 0.500},
            "400x600": {"w": 0.400, "h": 0.600},
            "500x800": {"w": 0.500, "h": 0.800},
        }
        
        for designation, dims in rectangles.items():
            section = self.calculator.calculate_rectangular_section(
                dims["w"], dims["h"]
            )
            section.name = f"Rectangular {designation}"
            section.designation = designation
            self.standard_sections[f"rect_{designation}"] = section
    
    def get_section(self, section_key: str) -> Optional[SectionProperties]:
        """Get section by key"""
        return self.standard_sections.get(section_key)
    
    def get_sections_by_type(self, section_type: SectionType) -> List[SectionProperties]:
        """Get all sections of specific type"""
        return [sec for sec in self.standard_sections.values() 
                if sec.section_type == section_type]
    
    def list_available_sections(self) -> Dict[str, str]:
        """List all available sections with descriptions"""
        return {key: sec.name for key, sec in self.standard_sections.items()}
    
    def create_custom_section(self, section_type: SectionType, 
                            dimensions: Dict[str, float]) -> SectionProperties:
        """Create custom section with given dimensions"""
        if section_type == SectionType.RECTANGULAR:
            return self.calculator.calculate_rectangular_section(
                dimensions["width"], dimensions["height"]
            )
        elif section_type == SectionType.CIRCULAR:
            return self.calculator.calculate_circular_section(
                dimensions["diameter"]
            )
        elif section_type == SectionType.I_SECTION:
            return self.calculator.calculate_i_section(
                dimensions["depth"], dimensions["width"],
                dimensions["flange_thickness"], dimensions["web_thickness"]
            )
        elif section_type == SectionType.CHANNEL:
            return self.calculator.calculate_channel_section(
                dimensions["depth"], dimensions["width"],
                dimensions["flange_thickness"], dimensions["web_thickness"]
            )
        elif section_type == SectionType.TUBE_RECTANGULAR:
            return self.calculator.calculate_tube_rectangular(
                dimensions["width"], dimensions["height"], dimensions["thickness"]
            )
        elif section_type == SectionType.TUBE_CIRCULAR:
            return self.calculator.calculate_tube_circular(
                dimensions["diameter"], dimensions["thickness"]
            )
        else:
            raise ModelError(f"Unsupported section type: {section_type}")
    
    def get_section_properties_dict(self, section_props: SectionProperties) -> Dict[str, Any]:
        """Convert section properties to dictionary for database storage"""
        return {
            "area": section_props.area,
            "moment_inertia_y": section_props.moment_inertia_y,
            "moment_inertia_z": section_props.moment_inertia_z,
            "moment_inertia_x": section_props.moment_inertia_x,
            "section_modulus_y": section_props.section_modulus_y,
            "section_modulus_z": section_props.section_modulus_z,
            "radius_gyration_y": section_props.radius_gyration_y,
            "radius_gyration_z": section_props.radius_gyration_z,
            "shear_area_y": section_props.shear_area_y,
            "shear_area_z": section_props.shear_area_z,
            "dimensions": section_props.dimensions,
            "additional_properties": section_props.additional_properties or {}
        }