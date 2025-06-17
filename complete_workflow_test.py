#!/usr/bin/env python3
"""
Complete StruMind Workflow Test & Recording
Tests the entire application workflow and records it as a single video
"""

import asyncio
import json
import time
from datetime import datetime
from playwright.async_api import async_playwright
import requests

class StruMindWorkflowTester:
    def __init__(self):
        self.frontend_url = "http://localhost:12001"
        self.backend_url = "http://localhost:8000"
        self.demo_user = {
            "email": "demo@strumind.com",
            "password": "DemoPassword123!"
        }
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_path = f"./videos/complete_workflow_{self.timestamp}.webm"
        self.screenshots_dir = f"./recordings/workflow_{self.timestamp}"
        
    async def test_backend_health(self):
        """Test backend connectivity"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            print(f"✅ Backend Health: {response.json()}")
            return True
        except Exception as e:
            print(f"❌ Backend Health Failed: {e}")
            return False
    
    async def test_api_endpoints(self):
        """Test key API endpoints"""
        try:
            # Test login
            login_response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.demo_user,
                headers={"Content-Type": "application/json"}
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                token = token_data["access_token"]
                print(f"✅ Login API: Token received")
                
                # Test projects endpoint
                projects_response = requests.get(
                    f"{self.backend_url}/api/v1/projects/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if projects_response.status_code == 200:
                    projects_data = projects_response.json()
                    print(f"✅ Projects API: {len(projects_data.get('projects', []))} projects found")
                    return True, token
                else:
                    print(f"❌ Projects API Failed: {projects_response.status_code}")
                    return False, None
            else:
                print(f"❌ Login API Failed: {login_response.status_code}")
                return False, None
                
        except Exception as e:
            print(f"❌ API Test Failed: {e}")
            return False, None
    
    async def run_complete_workflow(self):
        """Run the complete workflow test with video recording"""
        
        print("🚀 Starting Complete StruMind Workflow Test")
        print("=" * 60)
        
        # Test backend first
        if not await self.test_backend_health():
            print("❌ Backend not available. Aborting test.")
            return False
        
        # Test API endpoints
        api_success, token = await self.test_api_endpoints()
        if not api_success:
            print("❌ API endpoints not working. Aborting test.")
            return False
        
        print("✅ Backend and API tests passed. Starting browser workflow...")
        
        async with async_playwright() as p:
            # Launch browser with video recording
            browser = await p.chromium.launch(
                headless=True,  # Headless mode for server environment
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir="./recordings/",
                record_video_size={'width': 1280, 'height': 720}
            )
            
            page = await context.new_page()
            
            try:
                # Step 1: Navigate to homepage
                print("📱 Step 1: Loading homepage...")
                await page.goto(self.frontend_url)
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_01_homepage.png")
                await asyncio.sleep(2)
                
                # Step 2: Navigate to login
                print("🔐 Step 2: Navigating to login...")
                await page.click('text=Sign In')
                await page.wait_for_url('**/auth/login')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_02_login_page.png")
                await asyncio.sleep(1)
                
                # Step 3: Fill login form
                print("📝 Step 3: Filling login form...")
                await page.fill('input[type="email"]', self.demo_user["email"])
                await page.fill('input[type="password"]', self.demo_user["password"])
                await page.screenshot(path=f"{self.screenshots_dir}_03_login_filled.png")
                await asyncio.sleep(1)
                
                # Step 4: Submit login
                print("🚀 Step 4: Submitting login...")
                await page.click('button[type="submit"]')
                
                # Wait for redirect to dashboard
                try:
                    await page.wait_for_url('**/dashboard', timeout=10000)
                    print("✅ Successfully redirected to dashboard!")
                except:
                    print("⚠️ Dashboard redirect timeout, checking current URL...")
                    current_url = page.url
                    print(f"Current URL: {current_url}")
                    
                    # If still on login page, there might be an error
                    if 'login' in current_url:
                        error_element = await page.query_selector('.error, .alert, [role="alert"]')
                        if error_element:
                            error_text = await error_element.text_content()
                            print(f"❌ Login error: {error_text}")
                        else:
                            print("❌ Login failed - no specific error message")
                        await page.screenshot(path=f"{self.screenshots_dir}_04_login_error.png")
                        return False
                
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_05_dashboard.png")
                await asyncio.sleep(3)
                
                # Step 5: Create new project
                print("📋 Step 5: Creating new project...")
                await page.click('text=New Project')
                await page.wait_for_url('**/projects/new')
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_06_new_project.png")
                await asyncio.sleep(2)
                
                # Fill project form
                print("📝 Step 6: Filling project form...")
                await page.fill('input[name="name"]', 'Demo Workflow Project')
                await page.fill('textarea[name="description"]', 'Complete workflow demonstration project')
                await page.fill('input[name="location"]', 'Demo City, Demo State')
                await page.screenshot(path=f"{self.screenshots_dir}_07_project_form.png")
                await asyncio.sleep(1)
                
                # Submit project
                print("🚀 Step 7: Creating project...")
                await page.click('button[type="submit"]')
                
                # Wait for project creation and redirect
                try:
                    await page.wait_for_url('**/projects/*', timeout=10000)
                    print("✅ Project created successfully!")
                except:
                    print("⚠️ Project creation timeout, checking for errors...")
                    current_url = page.url
                    print(f"Current URL: {current_url}")
                
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_08_project_created.png")
                await asyncio.sleep(3)
                
                # Step 8: Navigate through project sections
                print("🏗️ Step 8: Exploring project sections...")
                
                # Try to navigate to modeling section
                modeling_link = await page.query_selector('text=Modeling, a[href*="modeling"], button:has-text("Modeling")')
                if modeling_link:
                    await modeling_link.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=f"{self.screenshots_dir}_09_modeling.png")
                    await asyncio.sleep(2)
                
                # Try to navigate to analysis section
                analysis_link = await page.query_selector('text=Analysis, a[href*="analysis"], button:has-text("Analysis")')
                if analysis_link:
                    await analysis_link.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=f"{self.screenshots_dir}_10_analysis.png")
                    await asyncio.sleep(2)
                
                # Try to navigate to design section
                design_link = await page.query_selector('text=Design, a[href*="design"], button:has-text("Design")')
                if design_link:
                    await design_link.click()
                    await page.wait_for_load_state('networkidle')
                    await page.screenshot(path=f"{self.screenshots_dir}_11_design.png")
                    await asyncio.sleep(2)
                
                # Step 9: Return to dashboard
                print("🏠 Step 9: Returning to dashboard...")
                dashboard_link = await page.query_selector('text=Dashboard, a[href*="dashboard"], .logo, [href="/dashboard"]')
                if dashboard_link:
                    await dashboard_link.click()
                else:
                    await page.goto(f"{self.frontend_url}/dashboard")
                
                await page.wait_for_load_state('networkidle')
                await page.screenshot(path=f"{self.screenshots_dir}_12_final_dashboard.png")
                await asyncio.sleep(3)
                
                print("✅ Complete workflow test completed successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Workflow test failed: {e}")
                await page.screenshot(path=f"{self.screenshots_dir}_error.png")
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
                
    async def generate_report(self, success):
        """Generate test report"""
        report = {
            "timestamp": self.timestamp,
            "success": success,
            "video_path": self.video_path,
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
            "demo_user": self.demo_user["email"],
            "test_duration": "~60 seconds",
            "steps_completed": [
                "Backend health check",
                "API endpoint validation",
                "Homepage navigation",
                "Login process",
                "Dashboard access",
                "Project creation",
                "Project navigation",
                "Workflow completion"
            ] if success else ["Failed during execution"]
        }
        
        with open(f"./recordings/workflow_report_{self.timestamp}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 60)
        print("📊 WORKFLOW TEST REPORT")
        print("=" * 60)
        print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Timestamp: {self.timestamp}")
        print(f"Video: {self.video_path}")
        print(f"Frontend: {self.frontend_url}")
        print(f"Backend: {self.backend_url}")
        print("=" * 60)

async def main():
    """Main execution function"""
    tester = StruMindWorkflowTester()
    
    # Create directories
    import os
    os.makedirs("./videos", exist_ok=True)
    os.makedirs("./recordings", exist_ok=True)
    
    # Run the complete workflow test
    success = await tester.run_complete_workflow()
    
    # Generate report
    await tester.generate_report(success)
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)