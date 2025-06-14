"""
Comprehensive test suite for StruMind platform
"""

import asyncio
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, List
import uuid

class StruMindTestSuite:
    """
    Comprehensive test suite for all StruMind functionality
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.auth_token = None
        self.test_project_id = None
        self.test_results = []
        
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        print(f"[{status}] {test_name}: {details}")
    
    def test_health_endpoints(self):
        """Test health endpoints"""
        try:
            # Main health endpoint
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.log_test("Health Endpoint", "PASS", "Main health endpoint responding")
            else:
                self.log_test("Health Endpoint", "FAIL", f"Status: {response.status_code}")
            
            # API v1 health endpoint
            response = requests.get(f"{self.base_url}/api/v1/health")
            if response.status_code == 200:
                data = response.json()
                if "endpoints" in data:
                    self.log_test("API v1 Health", "PASS", f"Found {len(data['endpoints'])} endpoints")
                else:
                    self.log_test("API v1 Health", "FAIL", "Missing endpoints info")
            else:
                self.log_test("API v1 Health", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Health Endpoints", "ERROR", str(e))
    
    def test_authentication(self):
        """Test authentication system"""
        try:
            # Test user registration
            register_data = {
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "password": "testpassword123",
                "first_name": "Test",
                "last_name": "User",
                "organization_name": f"Test Organization {uuid.uuid4().hex[:8]}"
            }
            
            response = requests.post(f"{self.base_url}/api/v1/auth/register", json=register_data)
            if response.status_code in [200, 201]:
                self.log_test("User Registration", "PASS", "User registered successfully")
                
                # Test login
                login_data = {
                    "email": register_data["email"],
                    "password": register_data["password"]
                }
                
                response = requests.post(f"{self.base_url}/api/v1/auth/login", json=login_data)
                if response.status_code == 200:
                    data = response.json()
                    if "access_token" in data:
                        self.auth_token = data["access_token"]
                        self.log_test("User Login", "PASS", "Login successful, token received")
                    else:
                        self.log_test("User Login", "FAIL", "No access token in response")
                else:
                    self.log_test("User Login", "FAIL", f"Status: {response.status_code}")
            else:
                self.log_test("User Registration", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Authentication", "ERROR", str(e))
    
    def test_project_management(self):
        """Test project management functionality"""
        if not self.auth_token:
            self.log_test("Project Management", "SKIP", "No auth token available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Create project
            project_data = {
                "name": f"Test Project {uuid.uuid4().hex[:8]}",
                "description": "Automated test project",
                "project_type": "building",
                "location": "Test Location"
            }
            
            response = requests.post(f"{self.base_url}/api/v1/projects/", json=project_data, headers=headers)
            if response.status_code in [200, 201]:
                project = response.json()
                self.test_project_id = project["id"]
                self.log_test("Project Creation", "PASS", f"Project created with ID: {self.test_project_id}")
                
                # List projects
                response = requests.get(f"{self.base_url}/api/v1/projects/", headers=headers)
                if response.status_code == 200:
                    projects = response.json()
                    if "projects" in projects and len(projects["projects"]) > 0:
                        self.log_test("Project Listing", "PASS", f"Found {len(projects['projects'])} projects")
                    else:
                        self.log_test("Project Listing", "FAIL", "No projects found")
                else:
                    self.log_test("Project Listing", "FAIL", f"Status: {response.status_code}")
                
                # Get project details
                response = requests.get(f"{self.base_url}/api/v1/projects/{self.test_project_id}", headers=headers)
                if response.status_code == 200:
                    project_details = response.json()
                    if project_details["name"] == project_data["name"]:
                        self.log_test("Project Details", "PASS", "Project details retrieved correctly")
                    else:
                        self.log_test("Project Details", "FAIL", "Project details mismatch")
                else:
                    self.log_test("Project Details", "FAIL", f"Status: {response.status_code}")
                    
            else:
                self.log_test("Project Creation", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Project Management", "ERROR", str(e))
    
    def test_structural_modeling(self):
        """Test structural modeling functionality"""
        if not self.auth_token or not self.test_project_id:
            self.log_test("Structural Modeling", "SKIP", "No auth token or project ID available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Create nodes
            nodes_data = [
                {"x": 0.0, "y": 0.0, "z": 0.0, "label": "Node 1"},
                {"x": 5.0, "y": 0.0, "z": 0.0, "label": "Node 2"},
                {"x": 5.0, "y": 5.0, "z": 0.0, "label": "Node 3"},
                {"x": 0.0, "y": 5.0, "z": 0.0, "label": "Node 4"}
            ]
            
            created_nodes = []
            for node_data in nodes_data:
                response = requests.post(
                    f"{self.base_url}/api/v1/models/{self.test_project_id}/nodes", 
                    json=node_data, 
                    headers=headers
                )
                if response.status_code in [200, 201]:
                    created_nodes.append(response.json())
                else:
                    self.log_test("Node Creation", "FAIL", f"Failed to create node: {response.status_code}")
                    return
            
            self.log_test("Node Creation", "PASS", f"Created {len(created_nodes)} nodes")
            
            # Create materials
            material_data = {
                "name": "Steel S355",
                "material_type": "steel",
                "properties": {
                    "elastic_modulus": 200e9,
                    "poisson_ratio": 0.3,
                    "density": 7850,
                    "yield_strength": 355e6
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/models/{self.test_project_id}/materials", 
                json=material_data, 
                headers=headers
            )
            if response.status_code in [200, 201]:
                material = response.json()
                self.log_test("Material Creation", "PASS", f"Material created with ID: {material['id']}")
                
                # Create sections
                section_data = {
                    "name": "IPE 300",
                    "section_type": "i_section",
                    "properties": {
                        "area": 0.0053,
                        "moment_of_inertia_x": 8.356e-5,
                        "moment_of_inertia_y": 6.04e-6,
                        "torsional_constant": 2.07e-7
                    }
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/models/{self.test_project_id}/sections", 
                    json=section_data, 
                    headers=headers
                )
                if response.status_code in [200, 201]:
                    section = response.json()
                    self.log_test("Section Creation", "PASS", f"Section created with ID: {section['id']}")
                    
                    # Create elements
                    if len(created_nodes) >= 2:
                        element_data = {
                            "start_node_id": created_nodes[0]["id"],
                            "end_node_id": created_nodes[1]["id"],
                            "material_id": material["id"],
                            "section_id": section["id"],
                            "element_type": "beam"
                        }
                        
                        response = requests.post(
                            f"{self.base_url}/api/v1/models/{self.test_project_id}/elements", 
                            json=element_data, 
                            headers=headers
                        )
                        if response.status_code in [200, 201]:
                            element = response.json()
                            self.log_test("Element Creation", "PASS", f"Element created with ID: {element['id']}")
                        else:
                            self.log_test("Element Creation", "FAIL", f"Status: {response.status_code}")
                else:
                    self.log_test("Section Creation", "FAIL", f"Status: {response.status_code}")
            else:
                self.log_test("Material Creation", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Structural Modeling", "ERROR", str(e))
    
    def test_analysis_engine(self):
        """Test structural analysis functionality"""
        if not self.auth_token or not self.test_project_id:
            self.log_test("Analysis Engine", "SKIP", "No auth token or project ID available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test analysis health
            response = requests.get(f"{self.base_url}/api/v1/analysis/health", headers=headers)
            if response.status_code == 200:
                self.log_test("Analysis Health", "PASS", "Analysis service responding")
            else:
                self.log_test("Analysis Health", "FAIL", f"Status: {response.status_code}")
                return
            
            # Run linear static analysis
            analysis_data = {
                "analysis_type": "linear_static",
                "parameters": {"load_factor": 1.5},
                "load_combinations": ["DL + LL"],
                "description": "Test linear static analysis"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/analysis/{self.test_project_id}/run", 
                json=analysis_data, 
                headers=headers
            )
            if response.status_code == 200:
                analysis_result = response.json()
                self.log_test("Linear Static Analysis", "PASS", f"Analysis started with ID: {analysis_result['id']}")
                
                # Wait a moment for analysis to complete
                time.sleep(2)
                
                # Check analysis status
                response = requests.get(
                    f"{self.base_url}/api/v1/analysis/{self.test_project_id}/analyses", 
                    headers=headers
                )
                if response.status_code == 200:
                    analyses = response.json()
                    if "analyses" in analyses and len(analyses["analyses"]) > 0:
                        self.log_test("Analysis Status Check", "PASS", f"Found {len(analyses['analyses'])} analyses")
                    else:
                        self.log_test("Analysis Status Check", "FAIL", "No analyses found")
                else:
                    self.log_test("Analysis Status Check", "FAIL", f"Status: {response.status_code}")
            else:
                self.log_test("Linear Static Analysis", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Analysis Engine", "ERROR", str(e))
    
    def test_file_management(self):
        """Test file upload/download functionality"""
        if not self.auth_token or not self.test_project_id:
            self.log_test("File Management", "SKIP", "No auth token or project ID available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Create a test file
            test_content = "Test file content for StruMind platform"
            test_file_path = Path("/tmp/test_file.csv")
            test_file_path.write_text(test_content)
            
            # Upload file
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_file.csv', f, 'text/csv')}
                response = requests.post(
                    f"{self.base_url}/api/v1/files/{self.test_project_id}/upload",
                    files=files,
                    headers=headers
                )
            
            if response.status_code == 200:
                upload_result = response.json()
                file_id = upload_result["file_id"]
                self.log_test("File Upload", "PASS", f"File uploaded with ID: {file_id}")
                
                # List files
                response = requests.get(
                    f"{self.base_url}/api/v1/files/{self.test_project_id}/files",
                    headers=headers
                )
                if response.status_code == 200:
                    files_list = response.json()
                    if "files" in files_list and len(files_list["files"]) > 0:
                        self.log_test("File Listing", "PASS", f"Found {len(files_list['files'])} files")
                    else:
                        self.log_test("File Listing", "FAIL", "No files found")
                else:
                    self.log_test("File Listing", "FAIL", f"Status: {response.status_code}")
                
                # Download file
                response = requests.get(
                    f"{self.base_url}/api/v1/files/{self.test_project_id}/files/{file_id}/download",
                    headers=headers
                )
                if response.status_code == 200:
                    if response.content.decode() == test_content:
                        self.log_test("File Download", "PASS", "File downloaded correctly")
                    else:
                        self.log_test("File Download", "FAIL", "Downloaded content mismatch")
                else:
                    self.log_test("File Download", "FAIL", f"Status: {response.status_code}")
                    
            else:
                self.log_test("File Upload", "FAIL", f"Status: {response.status_code}")
            
            # Clean up
            if test_file_path.exists():
                test_file_path.unlink()
                
        except Exception as e:
            self.log_test("File Management", "ERROR", str(e))
    
    def test_export_functionality(self):
        """Test export functionality"""
        if not self.auth_token or not self.test_project_id:
            self.log_test("Export Functionality", "SKIP", "No auth token or project ID available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test PDF export
            export_data = {
                "format": "pdf",
                "include_analysis_results": True,
                "include_design_results": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/files/{self.test_project_id}/export",
                json=export_data,
                headers=headers
            )
            if response.status_code == 200:
                if response.headers.get('content-type') == 'application/pdf':
                    self.log_test("PDF Export", "PASS", f"PDF exported successfully ({len(response.content)} bytes)")
                else:
                    self.log_test("PDF Export", "FAIL", "Invalid content type")
            else:
                self.log_test("PDF Export", "FAIL", f"Status: {response.status_code}")
            
            # Test DXF export
            export_data["format"] = "dxf"
            response = requests.post(
                f"{self.base_url}/api/v1/files/{self.test_project_id}/export",
                json=export_data,
                headers=headers
            )
            if response.status_code == 200:
                self.log_test("DXF Export", "PASS", f"DXF exported successfully ({len(response.content)} bytes)")
            else:
                self.log_test("DXF Export", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Export Functionality", "ERROR", str(e))
    
    def test_design_modules(self):
        """Test design modules"""
        if not self.auth_token or not self.test_project_id:
            self.log_test("Design Modules", "SKIP", "No auth token or project ID available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            # Test design health
            response = requests.get(f"{self.base_url}/api/v1/design/health", headers=headers)
            if response.status_code == 200:
                self.log_test("Design Health", "PASS", "Design service responding")
            else:
                self.log_test("Design Health", "FAIL", f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Design Modules", "ERROR", str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("STRUMIND COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        test_methods = [
            self.test_health_endpoints,
            self.test_authentication,
            self.test_project_management,
            self.test_structural_modeling,
            self.test_analysis_engine,
            self.test_file_management,
            self.test_export_functionality,
            self.test_design_modules
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_test(test_method.__name__, "ERROR", str(e))
        
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Skipped: {skipped_tests}")
        
        if total_tests > 0:
            success_rate = (passed_tests / (total_tests - skipped_tests)) * 100 if (total_tests - skipped_tests) > 0 else 0
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("\nDETAILED RESULTS:")
        print("-" * 60)
        for result in self.test_results:
            status_symbol = {
                "PASS": "✅",
                "FAIL": "❌", 
                "ERROR": "🔥",
                "SKIP": "⏭️"
            }.get(result["status"], "❓")
            
            print(f"{status_symbol} {result['test']}: {result['details']}")
        
        # Save results to file
        report_file = Path("test_results.json")
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\nDetailed results saved to: {report_file}")
        
        # Overall assessment
        if failed_tests == 0 and error_tests == 0:
            print("\n🎉 ALL TESTS PASSED! StruMind platform is functioning correctly.")
        elif failed_tests + error_tests < total_tests * 0.2:
            print("\n✅ MOSTLY SUCCESSFUL! Minor issues detected.")
        else:
            print("\n⚠️  SIGNIFICANT ISSUES DETECTED! Review failed tests.")


if __name__ == "__main__":
    # Run comprehensive test suite
    test_suite = StruMindTestSuite()
    test_suite.run_all_tests()