"""
Tests for design module functionality
"""

import uuid
from typing import Dict, Any

from design.steel.aisc_360 import AISC360SteelDesign
from design.concrete.is_456 import IS456ConcreteDesign
from core.modeling.elements import Element
from core.modeling.sections import SteelSection, ConcreteSection
from core.modeling.materials import SteelMaterial, ConcreteMaterial


class TestDesignModules:
    """Test suite for design modules"""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'details': []}
    
    def run_tests(self):
        """Run all design tests"""
        test_methods = [
            self.test_aisc_steel_beam_design,
            self.test_aisc_steel_column_design,
            self.test_is456_concrete_beam_design,
            self.test_is456_concrete_column_design,
            self.test_design_integration
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                self.test_results['passed'] += 1
                self.test_results['details'].append(f"✅ {test_method.__name__}")
                print(f"✅ {test_method.__name__}")
            except Exception as e:
                self.test_results['failed'] += 1
                self.test_results['details'].append(f"❌ {test_method.__name__}: {e}")
                print(f"❌ {test_method.__name__}: {e}")
        
        return self.test_results
    
    def test_aisc_steel_beam_design(self):
        """Test AISC 360 steel beam design"""
        designer = AISC360SteelDesign()
        
        # Create test beam
        element = self._create_test_beam_element()
        section = self._create_test_steel_section()
        material = self._create_test_steel_material()
        
        # Test forces
        forces = {
            'moment_y': 150000,  # N-mm (150 kN-m)
            'shear_y': 50000,    # N (50 kN)
            'axial': 0           # N
        }
        
        # Run design
        results = designer.design_beam(element, forces, section, material)
        
        # Verify results structure
        assert 'element_id' in results, "Results should contain element_id"
        assert 'code' in results, "Results should contain code"
        assert 'flexural' in results, "Results should contain flexural design"
        assert 'shear' in results, "Results should contain shear design"
        assert 'adequate' in results, "Results should contain adequacy check"
        
        # Verify flexural design
        flexural = results['flexural']
        assert 'Mn' in flexural, "Flexural results should contain nominal moment"
        assert 'phi_Mn' in flexural, "Flexural results should contain design moment"
        assert 'DCR' in flexural, "Flexural results should contain DCR"
        assert 'adequate' in flexural, "Flexural results should contain adequacy"
        
        # Verify shear design
        shear = results['shear']
        assert 'Vn' in shear, "Shear results should contain nominal shear"
        assert 'phi_Vn' in shear, "Shear results should contain design shear"
        assert 'DCR' in shear, "Shear results should contain DCR"
        
        # Check that design is adequate for reasonable loads
        assert results['adequate'], "Design should be adequate for test loads"
        assert flexural['DCR'] < 1.0, "Flexural DCR should be less than 1.0"
        assert shear['DCR'] < 1.0, "Shear DCR should be less than 1.0"
    
    def test_aisc_steel_column_design(self):
        """Test AISC 360 steel column design"""
        designer = AISC360SteelDesign()
        
        # Create test column
        element = self._create_test_column_element()
        section = self._create_test_steel_section()
        material = self._create_test_steel_material()
        
        # Test forces
        forces = {
            'axial': 500000,     # N (500 kN compression)
            'moment_x': 50000,   # N-mm (50 kN-m)
            'moment_y': 30000    # N-mm (30 kN-m)
        }
        
        # Run design
        results = designer.design_column(element, forces, section, material)
        
        # Verify results structure
        assert 'compression' in results, "Results should contain compression design"
        assert 'interaction' in results, "Results should contain interaction check"
        
        # Verify compression design
        compression = results['compression']
        assert 'Pn' in compression, "Compression results should contain nominal capacity"
        assert 'phi_Pn' in compression, "Compression results should contain design capacity"
        assert 'DCR' in compression, "Compression results should contain DCR"
        assert 'Fcr' in compression, "Compression results should contain critical stress"
        
        # Verify interaction
        interaction = results['interaction']
        assert 'interaction_ratio' in interaction, "Interaction should contain ratio"
        assert 'adequate' in interaction, "Interaction should contain adequacy"
        
        # Check adequacy
        assert results['adequate'], "Column design should be adequate"
        assert interaction['interaction_ratio'] < 1.0, "Interaction ratio should be < 1.0"
    
    def test_is456_concrete_beam_design(self):
        """Test IS 456 concrete beam design"""
        designer = IS456ConcreteDesign()
        
        # Create test beam
        element = self._create_test_beam_element()
        section = self._create_test_concrete_section()
        concrete = self._create_test_concrete_material()
        steel = self._create_test_rebar_material()
        
        # Test forces
        forces = {
            'moment_y': 100000,  # N-mm (100 kN-m)
            'shear_y': 40000     # N (40 kN)
        }
        
        # Run design
        results = designer.design_beam(element, forces, section, concrete, steel)
        
        # Verify results structure
        assert 'flexural' in results, "Results should contain flexural design"
        assert 'shear' in results, "Results should contain shear design"
        assert 'minimum_steel' in results, "Results should contain minimum steel check"
        
        # Verify flexural design
        flexural = results['flexural']
        assert 'As_required' in flexural, "Flexural should contain required steel area"
        assert 'As_provided' in flexural, "Flexural should contain provided steel area"
        assert 'type' in flexural, "Flexural should specify reinforcement type"
        
        # Verify shear design
        shear = results['shear']
        assert 'tau_v' in shear, "Shear should contain applied shear stress"
        assert 'tau_c' in shear, "Shear should contain concrete shear capacity"
        assert 'shear_reinforcement_required' in shear, "Shear should indicate if stirrups needed"
        
        # Check adequacy
        assert results['adequate'], "Concrete beam design should be adequate"
    
    def test_is456_concrete_column_design(self):
        """Test IS 456 concrete column design"""
        designer = IS456ConcreteDesign()
        
        # Create test column
        element = self._create_test_column_element()
        section = self._create_test_concrete_section()
        concrete = self._create_test_concrete_material()
        steel = self._create_test_rebar_material()
        
        # Test forces
        forces = {
            'axial': 800000,     # N (800 kN compression)
            'moment_x': 40000,   # N-mm (40 kN-m)
            'moment_y': 30000    # N-mm (30 kN-m)
        }
        
        # Run design
        results = designer.design_column(element, forces, section, concrete, steel)
        
        # Verify results structure
        assert 'slenderness' in results, "Results should contain slenderness check"
        assert 'design' in results, "Results should contain design results"
        assert 'steel_limits' in results, "Results should contain steel limits"
        
        # Verify slenderness
        slenderness = results['slenderness']
        assert 'is_short_column' in slenderness, "Slenderness should indicate if short column"
        assert 'max_slenderness' in slenderness, "Slenderness should contain max ratio"
        
        # Verify design
        design = results['design']
        assert 'load_type' in design, "Design should specify load type"
        assert 'adequate' in design, "Design should contain adequacy check"
        
        # Check adequacy
        assert results['adequate'], "Concrete column design should be adequate"
    
    def test_design_integration(self):
        """Test design module integration"""
        # Test that both design modules can be instantiated and used together
        steel_designer = AISC360SteelDesign()
        concrete_designer = IS456ConcreteDesign()
        
        # Verify code names
        assert steel_designer.code_name == "AISC 360-16", "Steel designer code name incorrect"
        assert concrete_designer.code_name == "IS 456:2000", "Concrete designer code name incorrect"
        
        # Verify resistance factors
        assert steel_designer.phi_b == 0.9, "Steel flexural resistance factor incorrect"
        assert steel_designer.phi_c == 0.9, "Steel compression resistance factor incorrect"
        assert concrete_designer.gamma_c == 1.5, "Concrete safety factor incorrect"
        assert concrete_designer.gamma_s == 1.15, "Steel safety factor incorrect"
        
        # Test summary generation
        steel_element = self._create_test_beam_element()
        steel_section = self._create_test_steel_section()
        steel_material = self._create_test_steel_material()
        
        forces = {'moment_y': 100000, 'shear_y': 30000, 'axial': 0}
        steel_results = steel_designer.design_beam(steel_element, forces, steel_section, steel_material)
        
        summary = steel_designer.get_design_summary(steel_results)
        assert isinstance(summary, str), "Design summary should be a string"
        assert "AISC 360" in summary, "Summary should mention design code"
        assert "Element" in summary, "Summary should mention element"
    
    def _create_test_beam_element(self):
        """Create a test beam element"""
        return Element(
            id=uuid.uuid4(),
            element_type="beam",
            start_node_id=uuid.uuid4(),
            end_node_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            section_id=uuid.uuid4(),
            length=6.0,  # 6 meters
            is_active=True,
            project_id=uuid.uuid4()
        )
    
    def _create_test_column_element(self):
        """Create a test column element"""
        return Element(
            id=uuid.uuid4(),
            element_type="column",
            start_node_id=uuid.uuid4(),
            end_node_id=uuid.uuid4(),
            material_id=uuid.uuid4(),
            section_id=uuid.uuid4(),
            length=3.5,  # 3.5 meters
            is_active=True,
            project_id=uuid.uuid4()
        )
    
    def _create_test_steel_section(self):
        """Create a test steel section"""
        return SteelSection(
            id=uuid.uuid4(),
            name="W14x22",
            section_type="i_section",
            area=0.0042,  # m²
            moment_of_inertia_x=9.77e-5,  # m⁴
            moment_of_inertia_y=2.09e-5,  # m⁴
            depth=0.349,  # m
            flange_width=0.127,  # m
            flange_thickness=0.0111,  # m
            web_thickness=0.0071,  # m
            section_modulus_x=0.000560,  # m³
            plastic_section_modulus_x=0.000630,  # m³
            radius_of_gyration_x=0.152,  # m
            radius_of_gyration_y=0.0704,  # m
            project_id=uuid.uuid4()
        )
    
    def _create_test_concrete_section(self):
        """Create a test concrete section"""
        return ConcreteSection(
            id=uuid.uuid4(),
            name="300x500 RC Section",
            section_type="rectangular",
            area=0.15,  # m²
            moment_of_inertia_x=3.125e-3,  # m⁴
            moment_of_inertia_y=1.125e-3,  # m⁴
            width=0.3,  # m
            depth=0.5,  # m
            project_id=uuid.uuid4()
        )
    
    def _create_test_steel_material(self):
        """Create a test steel material"""
        return SteelMaterial(
            id=uuid.uuid4(),
            name="A992 Steel",
            material_type="steel",
            elastic_modulus=200000,  # MPa
            poisson_ratio=0.3,
            density=7850,  # kg/m³
            yield_strength=345,  # MPa
            ultimate_strength=450,  # MPa
            project_id=uuid.uuid4()
        )
    
    def _create_test_concrete_material(self):
        """Create a test concrete material"""
        return ConcreteMaterial(
            id=uuid.uuid4(),
            name="M25 Concrete",
            material_type="concrete",
            elastic_modulus=25000,  # MPa
            poisson_ratio=0.2,
            density=2400,  # kg/m³
            compressive_strength=25,  # MPa
            tensile_strength=2.5,  # MPa
            project_id=uuid.uuid4()
        )
    
    def _create_test_rebar_material(self):
        """Create a test rebar material"""
        return SteelMaterial(
            id=uuid.uuid4(),
            name="Fe415 Rebar",
            material_type="steel",
            elastic_modulus=200000,  # MPa
            poisson_ratio=0.3,
            density=7850,  # kg/m³
            yield_strength=415,  # MPa
            ultimate_strength=500,  # MPa
            project_id=uuid.uuid4()
        )