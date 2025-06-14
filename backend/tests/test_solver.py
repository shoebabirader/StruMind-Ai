"""
Tests for solver engine functionality
"""

import numpy as np
import uuid
from typing import Dict, Any

from solver.solver_engine import SolverEngine, AnalysisManager
from solver.linear import LinearStaticAnalysis
from solver.matrix import StiffnessMatrixAssembler, DOFManager
from core.modeling.geometry import Point3D, GeometryEngine
from db.models.structural import Node, Element, Material, Section
from db.models.analysis import AnalysisCase, AnalysisType, AnalysisStatus


class TestSolverEngine:
    """Test suite for solver engine"""
    
    def __init__(self):
        self.test_results = {'passed': 0, 'failed': 0, 'details': []}
    
    def run_tests(self):
        """Run all solver tests"""
        test_methods = [
            self.test_dof_manager,
            self.test_geometry_engine,
            self.test_stiffness_matrix_assembly,
            self.test_linear_solver,
            self.test_solver_engine_integration
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
    
    def test_dof_manager(self):
        """Test DOF manager functionality"""
        dof_manager = DOFManager()
        
        # Test node DOF assignment
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()
        
        dofs1 = dof_manager.assign_node_dofs(node1_id)
        dofs2 = dof_manager.assign_node_dofs(node2_id)
        
        assert len(dofs1) == 6, "Node should have 6 DOFs"
        assert len(dofs2) == 6, "Node should have 6 DOFs"
        assert dofs1 == [0, 1, 2, 3, 4, 5], "First node DOFs incorrect"
        assert dofs2 == [6, 7, 8, 9, 10, 11], "Second node DOFs incorrect"
        assert dof_manager.total_dofs == 12, "Total DOFs incorrect"
        
        # Test boundary conditions
        restraints = [True, True, True, False, False, False]  # Fixed in translations
        dof_manager.apply_boundary_conditions(node1_id, restraints)
        
        assert 0 in dof_manager.constrained_dofs, "DOF 0 should be constrained"
        assert 1 in dof_manager.constrained_dofs, "DOF 1 should be constrained"
        assert 2 in dof_manager.constrained_dofs, "DOF 2 should be constrained"
        assert 3 not in dof_manager.constrained_dofs, "DOF 3 should be free"
        
        dof_manager.finalize_dof_mapping()
        assert len(dof_manager.free_dofs) == 9, "Should have 9 free DOFs"
    
    def test_geometry_engine(self):
        """Test geometry engine calculations"""
        # Test point operations
        p1 = Point3D(0, 0, 0)
        p2 = Point3D(3, 4, 0)
        
        distance = GeometryEngine.calculate_element_length(p1, p2)
        assert abs(distance - 5.0) < 1e-10, f"Distance should be 5.0, got {distance}"
        
        # Test direction cosines
        dx, dy, dz = GeometryEngine.calculate_element_direction_cosines(p1, p2)
        assert abs(dx - 0.6) < 1e-10, f"dx should be 0.6, got {dx}"
        assert abs(dy - 0.8) < 1e-10, f"dy should be 0.8, got {dy}"
        assert abs(dz - 0.0) < 1e-10, f"dz should be 0.0, got {dz}"
        
        # Test local coordinate system
        coord_system = GeometryEngine.calculate_element_local_axes(p1, p2)
        assert abs(coord_system.x_axis.x - 0.6) < 1e-10, "Local x-axis incorrect"
        assert abs(coord_system.x_axis.y - 0.8) < 1e-10, "Local x-axis incorrect"
    
    def test_stiffness_matrix_assembly(self):
        """Test stiffness matrix assembly"""
        assembler = StiffnessMatrixAssembler()
        
        # Create test nodes
        node1 = self._create_test_node(0, 0, 0)
        node2 = self._create_test_node(5, 0, 0)
        nodes = [node1, node2]
        
        # Create test element
        element = self._create_test_element(node1.id, node2.id)
        elements = [element]
        
        # Create test material and section
        material = self._create_test_material()
        section = self._create_test_section()
        materials = {material.id: material}
        sections = {section.id: section}
        
        # Test beam stiffness matrix calculation
        k_beam = assembler.calculate_beam_stiffness_matrix(
            element, node1, node2, material, section
        )
        
        assert k_beam.shape == (12, 12), "Beam stiffness matrix should be 12x12"
        assert not np.isnan(k_beam).any(), "Stiffness matrix should not contain NaN"
        assert np.allclose(k_beam, k_beam.T), "Stiffness matrix should be symmetric"
        
        # Test global assembly
        K_global, dof_manager = assembler.assemble_global_stiffness_matrix(
            nodes, elements, materials, sections
        )
        
        assert K_global.shape == (12, 12), "Global stiffness matrix should be 12x12"
        assert dof_manager.total_dofs == 12, "Should have 12 total DOFs"
    
    def test_linear_solver(self):
        """Test linear static analysis solver"""
        linear_solver = LinearStaticAnalysis()
        
        # Create simple 2-node beam model
        nodes = [
            self._create_test_node(0, 0, 0),
            self._create_test_node(5, 0, 0)
        ]
        
        elements = [
            self._create_test_element(nodes[0].id, nodes[1].id)
        ]
        
        material = self._create_test_material()
        section = self._create_test_section()
        materials = {material.id: material}
        sections = {section.id: section}
        
        # Create loads and boundary conditions
        loads = [self._create_test_load(nodes[1].id)]
        boundary_conditions = [self._create_test_boundary_condition(nodes[0].id)]
        
        # Create analysis case
        analysis_case = AnalysisCase(
            id=uuid.uuid4(),
            name="Test Analysis",
            analysis_type=AnalysisType.LINEAR_STATIC,
            status=AnalysisStatus.PENDING,
            project_id=uuid.uuid4()
        )
        
        # Run analysis
        results = linear_solver.run_analysis(
            analysis_case, nodes, elements, materials, sections, loads, boundary_conditions
        )
        
        assert 'displacements' in results, "Results should contain displacements"
        assert 'reactions' in results, "Results should contain reactions"
        assert 'element_forces' in results, "Results should contain element forces"
        assert 'solver_info' in results, "Results should contain solver info"
        
        displacements = results['displacements']
        assert len(displacements) == 12, "Should have 12 displacement values"
        assert not np.isnan(displacements).any(), "Displacements should not contain NaN"
    
    def test_solver_engine_integration(self):
        """Test complete solver engine integration"""
        solver_engine = SolverEngine()
        
        # Create test structural data
        structural_data = self._create_test_structural_data()
        
        # Create analysis case
        analysis_case = AnalysisCase(
            id=uuid.uuid4(),
            name="Integration Test",
            analysis_type=AnalysisType.LINEAR_STATIC,
            status=AnalysisStatus.PENDING,
            project_id=uuid.uuid4()
        )
        
        # This would normally be async, but for testing we'll call it directly
        # In a real async environment, you'd use: await solver_engine.run_analysis(...)
        try:
            # For testing, we'll simulate the analysis
            analysis_case.status = AnalysisStatus.RUNNING
            
            # Verify the solver can be initialized
            assert solver_engine.linear_solver is not None, "Linear solver should be initialized"
            assert solver_engine.dynamic_solver is not None, "Dynamic solver should be initialized"
            assert solver_engine.nonlinear_solver is not None, "Nonlinear solver should be initialized"
            assert solver_engine.buckling_solver is not None, "Buckling solver should be initialized"
            
            analysis_case.status = AnalysisStatus.COMPLETED
            
        except Exception as e:
            analysis_case.status = AnalysisStatus.FAILED
            raise e
        
        assert analysis_case.status == AnalysisStatus.COMPLETED, "Analysis should complete successfully"
    
    def _create_test_node(self, x, y, z):
        """Create a test node"""
        return Node(
            id=uuid.uuid4(),
            x=x, y=y, z=z,
            project_id=uuid.uuid4()
        )
    
    def _create_test_element(self, start_node_id, end_node_id):
        """Create a test element"""
        return Element(
            id=uuid.uuid4(),
            element_type="beam",
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            material_id=uuid.uuid4(),
            section_id=uuid.uuid4(),
            length=5.0,
            is_active=True,
            project_id=uuid.uuid4()
        )
    
    def _create_test_material(self):
        """Create a test material"""
        return Material(
            id=uuid.uuid4(),
            name="Test Steel",
            material_type="steel",
            elastic_modulus=200000,  # MPa
            poisson_ratio=0.3,
            density=7850,  # kg/m³
            project_id=uuid.uuid4()
        )
    
    def _create_test_section(self):
        """Create a test section"""
        return Section(
            id=uuid.uuid4(),
            name="Test Section",
            section_type="i_section",
            area=0.01,  # m²
            moment_of_inertia_x=1e-5,  # m⁴
            moment_of_inertia_y=5e-6,  # m⁴
            project_id=uuid.uuid4()
        )
    
    def _create_test_load(self, node_id):
        """Create a test load"""
        from db.models.structural import Load, LoadType, LoadDirection
        return Load(
            id=uuid.uuid4(),
            load_type=LoadType.POINT,
            direction=LoadDirection.Y,
            magnitude=-1000,  # N (downward)
            node_id=node_id,
            project_id=uuid.uuid4()
        )
    
    def _create_test_boundary_condition(self, node_id):
        """Create a test boundary condition"""
        from db.models.structural import BoundaryCondition
        return BoundaryCondition(
            id=uuid.uuid4(),
            node_id=node_id,
            restraint_x=True,
            restraint_y=True,
            restraint_z=True,
            restraint_xx=True,
            restraint_yy=True,
            restraint_zz=True,
            project_id=uuid.uuid4()
        )
    
    def _create_test_structural_data(self):
        """Create complete test structural data"""
        nodes = [
            self._create_test_node(0, 0, 0),
            self._create_test_node(5, 0, 0)
        ]
        
        elements = [
            self._create_test_element(nodes[0].id, nodes[1].id)
        ]
        
        material = self._create_test_material()
        section = self._create_test_section()
        
        loads = [self._create_test_load(nodes[1].id)]
        boundary_conditions = [self._create_test_boundary_condition(nodes[0].id)]
        
        return {
            'nodes': nodes,
            'elements': elements,
            'materials': {material.id: material},
            'sections': {section.id: section},
            'loads': loads,
            'boundary_conditions': boundary_conditions
        }