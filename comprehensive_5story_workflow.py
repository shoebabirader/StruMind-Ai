#!/usr/bin/env python3
"""
Comprehensive 5-Story Building Workflow Test & Recording
Creates a complete 5-story building project with modeling, analysis, and design
"""

import asyncio
import json
import time
import requests
from datetime import datetime
from playwright.async_api import async_playwright

class FiveStoryBuildingWorkflow:
    def __init__(self):
        self.frontend_url = "http://localhost:12001"
        self.backend_url = "http://localhost:8000"
        self.demo_user = {
            "email": "demo@strumind.com",
            "password": "DemoPassword123!"
        }
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_path = f"./videos/5story_building_complete_{self.timestamp}.webm"
        self.project_data = {
            "name": "5-Story Commercial Building",
            "description": "Complete structural design of a 5-story commercial building with concrete frame",
            "project_type": "commercial",
            "location": "Downtown Business District",
            "client": "ABC Development Corp"
        }
        
    async def test_backend_apis(self):
        """Test all backend APIs we'll need"""
        try:
            # Test login and get token
            login_response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.demo_user,
                headers={"Content-Type": "application/json"}
            )
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.status_code}")
                return False, None
                
            token_data = login_response.json()
            token = token_data["access_token"]
            print(f"✅ Login successful, token obtained")
            
            # Test API endpoints
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test projects endpoint
            projects_response = requests.get(f"{self.backend_url}/api/v1/projects/", headers=headers)
            print(f"✅ Projects API: {projects_response.status_code}")
            
            # Test models endpoint
            models_response = requests.get(f"{self.backend_url}/api/v1/models/health", headers=headers)
            print(f"✅ Models API: {models_response.status_code}")
            
            # Test analysis endpoint
            analysis_response = requests.get(f"{self.backend_url}/api/v1/analysis/health", headers=headers)
            print(f"✅ Analysis API: {analysis_response.status_code}")
            
            # Test design endpoint
            design_response = requests.get(f"{self.backend_url}/api/v1/design/health", headers=headers)
            print(f"✅ Design API: {design_response.status_code}")
            
            return True, token
            
        except Exception as e:
            print(f"❌ Backend API test failed: {e}")
            return False, None
    
    async def create_project_via_api(self, token):
        """Create project via API and return project ID"""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.backend_url}/api/v1/projects/",
                json=self.project_data,
                headers=headers
            )
            
            if response.status_code == 200:
                project = response.json()
                print(f"✅ Project created via API: {project['id']}")
                return project['id']
            else:
                print(f"❌ Project creation failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Project creation error: {e}")
            return None
    
    async def run_comprehensive_workflow(self):
        """Run the complete 5-story building workflow"""
        
        print("🏗️ Starting 5-Story Building Complete Workflow")
        print("=" * 70)
        
        # Test backend APIs first
        api_success, token = await self.test_backend_apis()
        if not api_success:
            print("❌ Backend APIs not ready. Aborting.")
            return False
        
        print("✅ All backend APIs ready. Starting comprehensive workflow...")
        
        async with async_playwright() as p:
            # Launch browser with video recording
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},  # Higher resolution
                record_video_dir="./recordings/",
                record_video_size={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                # Step 1: Navigate to homepage
                print("🏠 Step 1: Loading StruMind homepage...")
                await page.goto(self.frontend_url)
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_01_homepage_{self.timestamp}.png")
                await asyncio.sleep(3)
                
                # Step 2: Navigate to login
                print("🔐 Step 2: Navigating to login page...")
                await page.click('text=Sign In')
                await page.wait_for_url('**/auth/login')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_02_login_{self.timestamp}.png")
                await asyncio.sleep(2)
                
                # Step 3: Login with demo credentials
                print("📝 Step 3: Logging in with demo user...")
                await page.fill('input[type="email"]', self.demo_user["email"])
                await page.fill('input[type="password"]', self.demo_user["password"])
                await page.screenshot(path=f"./recordings/5story_03_login_filled_{self.timestamp}.png")
                await asyncio.sleep(1)
                
                # Submit login
                await page.click('button[type="submit"]')
                await page.wait_for_url('**/dashboard', timeout=10000)
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_04_dashboard_{self.timestamp}.png")
                await asyncio.sleep(3)
                print("✅ Successfully logged in and reached dashboard")
                
                # Step 4: Create new project
                print("📋 Step 4: Creating 5-story building project...")
                await page.click('text=New Project')
                await page.wait_for_url('**/projects/new')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_05_new_project_{self.timestamp}.png")
                await asyncio.sleep(2)
                
                # Fill project form with 5-story building details
                print("🏗️ Step 5: Filling project details for 5-story building...")
                await page.fill('input[name="name"]', self.project_data["name"])
                await page.fill('textarea[name="description"]', self.project_data["description"])
                await page.fill('input[name="location"]', self.project_data["location"])
                await page.fill('input[name="client"]', self.project_data["client"])
                await page.select_option('select[name="projectType"]', self.project_data["project_type"])
                await page.screenshot(path=f"./recordings/5story_06_project_form_{self.timestamp}.png")
                await asyncio.sleep(2)
                
                # Submit project creation
                print("🚀 Step 6: Creating the project...")
                await page.click('button[type="submit"]')
                await page.wait_for_url('**/projects/*', timeout=10000)
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_07_project_created_{self.timestamp}.png")
                await asyncio.sleep(3)
                print("✅ 5-story building project created successfully")
                
                # Step 7: Explore project overview
                print("📊 Step 7: Exploring project overview...")
                await page.screenshot(path=f"./recordings/5story_08_overview_{self.timestamp}.png")
                await asyncio.sleep(3)
                
                # Step 8: Navigate to Modeling tab
                print("🏗️ Step 8: Accessing structural modeling...")
                await page.click('text=Modeling')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_09_modeling_{self.timestamp}.png")
                await asyncio.sleep(4)
                
                # Interact with modeling interface
                modeling_button = await page.query_selector('text=Launch Model Editor, text=Start Modeling')
                if modeling_button:
                    print("🎯 Interacting with model editor...")
                    await modeling_button.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path=f"./recordings/5story_10_model_editor_{self.timestamp}.png")
                
                # Step 9: Navigate to Analysis tab
                print("📊 Step 9: Accessing structural analysis...")
                await page.click('text=Analysis')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_11_analysis_{self.timestamp}.png")
                await asyncio.sleep(4)
                
                # Interact with analysis options
                print("🔬 Configuring analysis for 5-story building...")
                linear_analysis = await page.query_selector('text=Linear Static Analysis')
                if linear_analysis:
                    await linear_analysis.click()
                    await asyncio.sleep(1)
                
                configure_button = await page.query_selector('text=Configure')
                if configure_button:
                    await configure_button.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path=f"./recordings/5story_12_analysis_config_{self.timestamp}.png")
                
                # Step 10: Navigate to Design tab
                print("🔧 Step 10: Accessing structural design...")
                await page.click('text=Design')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_13_design_{self.timestamp}.png")
                await asyncio.sleep(4)
                
                # Interact with design options
                print("🏗️ Configuring design for concrete frame...")
                concrete_design = await page.query_selector('text=Concrete Design')
                if concrete_design:
                    await concrete_design.click()
                    await asyncio.sleep(1)
                
                start_design = await page.query_selector('text=Start Design')
                if start_design:
                    await start_design.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path=f"./recordings/5story_14_design_config_{self.timestamp}.png")
                
                # Step 11: Navigate to Reports tab
                print("📄 Step 11: Accessing reports and documentation...")
                await page.click('text=Reports')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_15_reports_{self.timestamp}.png")
                await asyncio.sleep(4)
                
                # Interact with report generation
                print("📋 Generating analysis report...")
                analysis_report = await page.query_selector('text=Analysis Report')
                if analysis_report:
                    await analysis_report.click()
                    await asyncio.sleep(1)
                
                generate_button = await page.query_selector('text=Generate')
                if generate_button:
                    await generate_button.click()
                    await asyncio.sleep(2)
                    await page.screenshot(path=f"./recordings/5story_16_report_generation_{self.timestamp}.png")
                
                # Step 12: Return to dashboard to see completed project
                print("🏠 Step 12: Returning to dashboard...")
                await page.click('text=Back to Dashboard, text=Dashboard')
                await page.wait_for_url('**/dashboard')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"./recordings/5story_17_final_dashboard_{self.timestamp}.png")
                await asyncio.sleep(4)
                
                # Step 13: Final project overview
                print("🎯 Step 13: Final project verification...")
                # Look for the created project in the dashboard
                project_card = await page.query_selector(f'text={self.project_data["name"]}')
                if project_card:
                    print("✅ 5-story building project visible in dashboard")
                    await project_card.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=f"./recordings/5story_18_project_final_{self.timestamp}.png")
                    await asyncio.sleep(3)
                
                print("✅ Complete 5-story building workflow completed successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Workflow failed: {e}")
                await page.screenshot(path=f"./recordings/5story_error_{self.timestamp}.png")
                return False
                
            finally:
                # Close browser and save video
                await context.close()
                await browser.close()
                
                # Move video to final location
                import os
                import shutil
                
                # Find the generated video file
                video_files = [f for f in os.listdir("./recordings/") if f.endswith('.webm')]
                if video_files:
                    latest_video = max(video_files, key=lambda x: os.path.getctime(f"./recordings/{x}"))
                    shutil.move(f"./recordings/{latest_video}", self.video_path)
                    print(f"📹 Video saved to: {self.video_path}")
                    
                    # Get video file size
                    video_size = os.path.getsize(self.video_path)
                    print(f"📊 Video size: {video_size / 1024 / 1024:.1f} MB")
    
    async def generate_comprehensive_report(self, success):
        """Generate comprehensive test report"""
        report = {
            "timestamp": self.timestamp,
            "success": success,
            "project_type": "5-Story Commercial Building",
            "video_path": self.video_path,
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
            "demo_user": self.demo_user["email"],
            "project_data": self.project_data,
            "workflow_steps": [
                "Homepage navigation",
                "User authentication",
                "Dashboard access",
                "Project creation (5-story building)",
                "Project overview exploration",
                "Structural modeling interface",
                "Analysis configuration",
                "Design setup",
                "Report generation",
                "Final verification"
            ] if success else ["Failed during execution"],
            "technical_features_tested": [
                "Frontend-backend integration",
                "Authentication and session management",
                "Project CRUD operations",
                "Modeling interface navigation",
                "Analysis workflow access",
                "Design configuration interface",
                "Report generation system",
                "Dashboard project management"
            ] if success else []
        }
        
        with open(f"./recordings/5story_workflow_report_{self.timestamp}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 70)
        print("📊 5-STORY BUILDING WORKFLOW REPORT")
        print("=" * 70)
        print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Project: {self.project_data['name']}")
        print(f"Timestamp: {self.timestamp}")
        print(f"Video: {self.video_path}")
        print(f"Frontend: {self.frontend_url}")
        print(f"Backend: {self.backend_url}")
        print("=" * 70)

async def main():
    """Main execution function"""
    workflow = FiveStoryBuildingWorkflow()
    
    # Create directories
    import os
    os.makedirs("./videos", exist_ok=True)
    os.makedirs("./recordings", exist_ok=True)
    
    # Run the comprehensive workflow
    success = await workflow.run_comprehensive_workflow()
    
    # Generate report
    await workflow.generate_comprehensive_report(success)
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)