"""
Material library and validation for structural materials
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import json

from db.models.structural import Material, MaterialType
from core.exceptions import ModelError, ValidationError


class MaterialStandard(Enum):
    """Material standards"""
    # Concrete standards
    ACI_318 = "aci_318"
    IS_456 = "is_456"
    EUROCODE_2 = "eurocode_2"
    BS_8110 = "bs_8110"
    
    # Steel standards
    AISC_360 = "aisc_360"
    IS_800 = "is_800"
    EUROCODE_3 = "eurocode_3"
    BS_5950 = "bs_5950"
    
    # Timber standards
    NDS = "nds"
    EUROCODE_5 = "eurocode_5"


@dataclass
class MaterialProperties:
    """Material properties container"""
    name: str
    material_type: MaterialType
    grade: str
    standard: MaterialStandard
    
    # Basic mechanical properties
    elastic_modulus: float  # Pa
    poisson_ratio: float
    density: float  # kg/m³
    
    # Strength properties
    yield_strength: Optional[float] = None  # Pa
    ultimate_strength: Optional[float] = None  # Pa
    compressive_strength: Optional[float] = None  # Pa
    
    # Thermal properties
    thermal_expansion: Optional[float] = None  # 1/°C
    thermal_conductivity: Optional[float] = None  # W/m·K
    
    # Additional properties
    additional_properties: Optional[Dict[str, Any]] = None


class MaterialValidator:
    """Validator for material properties"""
    
    def __init__(self):
        self.validation_limits = {
            # Elastic modulus limits (Pa)
            "elastic_modulus_min": 1e6,    # 1 MPa
            "elastic_modulus_max": 1e12,   # 1 TPa
            
            # Poisson's ratio limits
            "poisson_ratio_min": -1.0,
            "poisson_ratio_max": 0.5,
            
            # Density limits (kg/m³)
            "density_min": 100,    # Very light materials
            "density_max": 20000,  # Very heavy materials
            
            # Strength limits (Pa)
            "strength_min": 1e3,   # 1 kPa
            "strength_max": 1e10,  # 10 GPa
        }
    
    def validate_basic_properties(self, props: MaterialProperties) -> List[str]:
        """Validate basic material properties"""
        errors = []
        
        # Validate elastic modulus
        if not (self.validation_limits["elastic_modulus_min"] <= 
                props.elastic_modulus <= 
                self.validation_limits["elastic_modulus_max"]):
            errors.append(f"Elastic modulus {props.elastic_modulus/1e9:.1f} GPa is out of valid range")
        
        # Validate Poisson's ratio
        if not (self.validation_limits["poisson_ratio_min"] <= 
                props.poisson_ratio <= 
                self.validation_limits["poisson_ratio_max"]):
            errors.append(f"Poisson's ratio {props.poisson_ratio} is out of valid range (-1.0 to 0.5)")
        
        # Validate density
        if not (self.validation_limits["density_min"] <= 
                props.density <= 
                self.validation_limits["density_max"]):
            errors.append(f"Density {props.density} kg/m³ is out of valid range")
        
        return errors
    
    def validate_strength_properties(self, props: MaterialProperties) -> List[str]:
        """Validate strength properties"""
        errors = []
        
        # Check yield strength
        if props.yield_strength is not None:
            if not (self.validation_limits["strength_min"] <= 
                    props.yield_strength <= 
                    self.validation_limits["strength_max"]):
                errors.append(f"Yield strength {props.yield_strength/1e6:.1f} MPa is out of valid range")
        
        # Check ultimate strength
        if props.ultimate_strength is not None:
            if not (self.validation_limits["strength_min"] <= 
                    props.ultimate_strength <= 
                    self.validation_limits["strength_max"]):
                errors.append(f"Ultimate strength {props.ultimate_strength/1e6:.1f} MPa is out of valid range")
            
            # Ultimate strength should be greater than yield strength
            if props.yield_strength is not None and props.ultimate_strength <= props.yield_strength:
                errors.append("Ultimate strength should be greater than yield strength")
        
        # Check compressive strength
        if props.compressive_strength is not None:
            if not (self.validation_limits["strength_min"] <= 
                    props.compressive_strength <= 
                    self.validation_limits["strength_max"]):
                errors.append(f"Compressive strength {props.compressive_strength/1e6:.1f} MPa is out of valid range")
        
        return errors
    
    def validate_material_type_consistency(self, props: MaterialProperties) -> List[str]:
        """Validate consistency between material type and properties"""
        errors = []
        
        if props.material_type == MaterialType.CONCRETE:
            # Concrete should have compressive strength
            if props.compressive_strength is None:
                errors.append("Concrete materials must have compressive strength defined")
            
            # Concrete typically has low tensile strength
            if props.yield_strength is not None and props.yield_strength > props.compressive_strength / 10:
                errors.append("Warning: Concrete tensile strength seems too high relative to compressive strength")
        
        elif props.material_type == MaterialType.STEEL:
            # Steel should have yield and ultimate strength
            if props.yield_strength is None:
                errors.append("Steel materials must have yield strength defined")
            if props.ultimate_strength is None:
                errors.append("Steel materials must have ultimate strength defined")
        
        elif props.material_type == MaterialType.TIMBER:
            # Timber should have compressive and tensile strengths
            if props.compressive_strength is None:
                errors.append("Timber materials should have compressive strength defined")
        
        return errors
    
    def validate_standard_compliance(self, props: MaterialProperties) -> List[str]:
        """Validate compliance with material standards"""
        errors = []
        
        # Check if material type matches standard
        concrete_standards = {MaterialStandard.ACI_318, MaterialStandard.IS_456, 
                            MaterialStandard.EUROCODE_2, MaterialStandard.BS_8110}
        steel_standards = {MaterialStandard.AISC_360, MaterialStandard.IS_800,
                         MaterialStandard.EUROCODE_3, MaterialStandard.BS_5950}
        timber_standards = {MaterialStandard.NDS, MaterialStandard.EUROCODE_5}
        
        if props.material_type == MaterialType.CONCRETE and props.standard not in concrete_standards:
            errors.append(f"Standard {props.standard.value} is not appropriate for concrete")
        elif props.material_type == MaterialType.STEEL and props.standard not in steel_standards:
            errors.append(f"Standard {props.standard.value} is not appropriate for steel")
        elif props.material_type == MaterialType.TIMBER and props.standard not in timber_standards:
            errors.append(f"Standard {props.standard.value} is not appropriate for timber")
        
        return errors


class MaterialLibrary:
    """Library of standard materials"""
    
    def __init__(self):
        self.validator = MaterialValidator()
        self._initialize_standard_materials()
    
    def _initialize_standard_materials(self):
        """Initialize library with standard materials"""
        self.standard_materials = {}
        
        # Add concrete materials
        self._add_concrete_materials()
        
        # Add steel materials
        self._add_steel_materials()
        
        # Add timber materials
        self._add_timber_materials()
    
    def _add_concrete_materials(self):
        """Add standard concrete materials"""
        # IS 456 Concrete grades
        concrete_grades_is = {
            "M15": {"fck": 15e6, "E": 22360e6},
            "M20": {"fck": 20e6, "E": 25000e6},
            "M25": {"fck": 25e6, "E": 27386e6},
            "M30": {"fck": 30e6, "E": 29580e6},
            "M35": {"fck": 35e6, "E": 31623e6},
            "M40": {"fck": 40e6, "E": 33541e6},
            "M45": {"fck": 45e6, "E": 35355e6},
            "M50": {"fck": 50e6, "E": 37081e6}
        }
        
        for grade, props in concrete_grades_is.items():
            material = MaterialProperties(
                name=f"Concrete {grade} (IS 456)",
                material_type=MaterialType.CONCRETE,
                grade=grade,
                standard=MaterialStandard.IS_456,
                elastic_modulus=props["E"],
                poisson_ratio=0.2,
                density=2500,  # kg/m³
                compressive_strength=props["fck"],
                thermal_expansion=10e-6  # 1/°C
            )
            self.standard_materials[f"concrete_is_{grade.lower()}"] = material
        
        # ACI 318 Concrete
        aci_concrete = {
            "3000": {"fc": 20.7e6, "E": 24855e6},
            "4000": {"fc": 27.6e6, "E": 28728e6},
            "5000": {"fc": 34.5e6, "E": 32043e6},
            "6000": {"fc": 41.4e6, "E": 35014e6}
        }
        
        for grade, props in aci_concrete.items():
            material = MaterialProperties(
                name=f"Concrete {grade} psi (ACI 318)",
                material_type=MaterialType.CONCRETE,
                grade=f"{grade} psi",
                standard=MaterialStandard.ACI_318,
                elastic_modulus=props["E"],
                poisson_ratio=0.2,
                density=2400,  # kg/m³
                compressive_strength=props["fc"],
                thermal_expansion=9.9e-6  # 1/°C
            )
            self.standard_materials[f"concrete_aci_{grade}"] = material
    
    def _add_steel_materials(self):
        """Add standard steel materials"""
        # IS 800 Steel grades
        steel_grades_is = {
            "Fe250": {"fy": 250e6, "fu": 410e6},
            "Fe415": {"fy": 415e6, "fu": 485e6},
            "Fe500": {"fy": 500e6, "fu": 545e6},
            "Fe550": {"fy": 550e6, "fu": 585e6}
        }
        
        for grade, props in steel_grades_is.items():
            material = MaterialProperties(
                name=f"Steel {grade} (IS 800)",
                material_type=MaterialType.STEEL,
                grade=grade,
                standard=MaterialStandard.IS_800,
                elastic_modulus=200e9,  # Pa
                poisson_ratio=0.3,
                density=7850,  # kg/m³
                yield_strength=props["fy"],
                ultimate_strength=props["fu"],
                thermal_expansion=12e-6  # 1/°C
            )
            self.standard_materials[f"steel_is_{grade.lower()}"] = material
        
        # AISC 360 Steel grades
        steel_grades_aisc = {
            "A36": {"fy": 248e6, "fu": 400e6},
            "A572_Gr50": {"fy": 345e6, "fu": 450e6},
            "A992": {"fy": 345e6, "fu": 450e6},
            "A500_GrB": {"fy": 290e6, "fu": 400e6}
        }
        
        for grade, props in steel_grades_aisc.items():
            material = MaterialProperties(
                name=f"Steel {grade} (AISC 360)",
                material_type=MaterialType.STEEL,
                grade=grade,
                standard=MaterialStandard.AISC_360,
                elastic_modulus=200e9,  # Pa
                poisson_ratio=0.3,
                density=7850,  # kg/m³
                yield_strength=props["fy"],
                ultimate_strength=props["fu"],
                thermal_expansion=11.7e-6  # 1/°C
            )
            self.standard_materials[f"steel_aisc_{grade.lower()}"] = material
    
    def _add_timber_materials(self):
        """Add standard timber materials"""
        # Common timber species
        timber_species = {
            "southern_pine": {
                "E": 12.4e9, "fc": 35e6, "ft": 20e6, "density": 590
            },
            "douglas_fir": {
                "E": 13.1e9, "fc": 40e6, "ft": 24e6, "density": 530
            },
            "oak": {
                "E": 12.0e9, "fc": 45e6, "ft": 28e6, "density": 700
            }
        }
        
        for species, props in timber_species.items():
            material = MaterialProperties(
                name=f"Timber {species.replace('_', ' ').title()}",
                material_type=MaterialType.TIMBER,
                grade="Select Structural",
                standard=MaterialStandard.NDS,
                elastic_modulus=props["E"],
                poisson_ratio=0.35,
                density=props["density"],
                compressive_strength=props["fc"],
                yield_strength=props["ft"],  # Tensile strength
                thermal_expansion=5e-6  # 1/°C
            )
            self.standard_materials[f"timber_{species}"] = material
    
    def get_material(self, material_key: str) -> Optional[MaterialProperties]:
        """Get material by key"""
        return self.standard_materials.get(material_key)
    
    def get_materials_by_type(self, material_type: MaterialType) -> List[MaterialProperties]:
        """Get all materials of specific type"""
        return [mat for mat in self.standard_materials.values() 
                if mat.material_type == material_type]
    
    def get_materials_by_standard(self, standard: MaterialStandard) -> List[MaterialProperties]:
        """Get all materials of specific standard"""
        return [mat for mat in self.standard_materials.values() 
                if mat.standard == standard]
    
    def list_available_materials(self) -> Dict[str, str]:
        """List all available materials with descriptions"""
        return {key: mat.name for key, mat in self.standard_materials.items()}
    
    def validate_material(self, material_props: MaterialProperties) -> List[str]:
        """Validate material properties"""
        errors = []
        
        # Basic properties validation
        errors.extend(self.validator.validate_basic_properties(material_props))
        
        # Strength properties validation
        errors.extend(self.validator.validate_strength_properties(material_props))
        
        # Material type consistency validation
        errors.extend(self.validator.validate_material_type_consistency(material_props))
        
        # Standard compliance validation
        errors.extend(self.validator.validate_standard_compliance(material_props))
        
        return errors
    
    def create_custom_material(self, material_props: MaterialProperties) -> Tuple[bool, List[str]]:
        """Create and validate custom material"""
        errors = self.validate_material(material_props)
        
        if not errors:
            # Generate unique key for custom material
            key = f"custom_{material_props.material_type.value}_{len(self.standard_materials)}"
            self.standard_materials[key] = material_props
            return True, []
        
        return False, errors
    
    def get_material_properties_dict(self, material_props: MaterialProperties) -> Dict[str, Any]:
        """Convert material properties to dictionary for database storage"""
        return {
            "elastic_modulus": material_props.elastic_modulus,
            "poisson_ratio": material_props.poisson_ratio,
            "density": material_props.density,
            "yield_strength": material_props.yield_strength,
            "ultimate_strength": material_props.ultimate_strength,
            "compressive_strength": material_props.compressive_strength,
            "thermal_expansion": material_props.thermal_expansion,
            "thermal_conductivity": material_props.thermal_conductivity,
            "additional_properties": material_props.additional_properties or {}
        }
    
    def calculate_derived_properties(self, material_props: MaterialProperties) -> Dict[str, float]:
        """Calculate derived material properties"""
        derived = {}
        
        # Shear modulus
        G = material_props.elastic_modulus / (2 * (1 + material_props.poisson_ratio))
        derived["shear_modulus"] = G
        
        # Bulk modulus
        K = material_props.elastic_modulus / (3 * (1 - 2 * material_props.poisson_ratio))
        derived["bulk_modulus"] = K
        
        # Unit weight
        derived["unit_weight"] = material_props.density * 9.81  # N/m³
        
        return derived