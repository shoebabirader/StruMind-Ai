#!/usr/bin/env python3
"""
StruMind Workflow Demo - Part 2: Project Creation & Model Setup
Records the project creation and structural model setup process.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

class Part2ProjectCreation:
    def __init__(self):
        self.frontend_url = "http://localhost:12001"
        self.recordings_dir = Path("./recordings")
        self.recordings_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Demo user credentials
        self.demo_user = {
            "email": "demo@strumind.com",
            "password": "DemoPassword123!"
        }

    async def setup_browser(self, playwright):
        """Setup browser with video recording"""
        print("🎬 Setting up browser for Part 2: Project Creation...")
        
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir=str(self.recordings_dir),
            record_video_size={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        page.set_default_timeout(30000)
        
        return browser, context, page

    async def step_1_login(self, page: Page):
        """Login to access dashboard"""
        print("\n🔐 Step 1: Logging in...")
        
        await page.goto(f"{self.frontend_url}/auth/login")
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        # Fill login form
        await page.fill('input[type="email"]', self.demo_user["email"])
        await page.wait_for_timeout(1000)
        await page.fill('input[type="password"]', self.demo_user["password"])
        await page.wait_for_timeout(1000)
        
        # Submit login
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_01_dashboard_{self.timestamp}.png")
        print("✅ Successfully logged in")

    async def step_2_create_project(self, page: Page):
        """Create a new project"""
        print("\n📁 Step 2: Creating New Project...")
        
        # Look for create project button
        create_buttons = page.locator(
            'button:has-text("New Project"), button:has-text("Create Project"), '
            'a:has-text("New Project"), [data-testid="create-project"]'
        )
        
        if await create_buttons.count() > 0:
            print("✅ Found Create Project button")
            await create_buttons.first.click()
            await page.wait_for_timeout(3000)
        else:
            # Try navigating directly to projects page
            print("ℹ️ Navigating to projects page")
            await page.goto(f"{self.frontend_url}/projects/new")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

        await page.screenshot(path=self.recordings_dir / f"part2_02_project_form_{self.timestamp}.png")

    async def step_3_fill_project_details(self, page: Page):
        """Fill project details form"""
        print("\n📝 Step 3: Filling Project Details...")
        
        project_data = {
            "name": f"Demo Bridge Project {self.timestamp[-6:]}",
            "description": "A demonstration bridge structure for StruMind workflow",
            "type": "Bridge",
            "location": "Demo City, Demo State"
        }
        
        # Fill project form
        name_input = page.locator('input[name="name"], input[placeholder*="name" i]')
        if await name_input.count() > 0:
            await name_input.first.fill(project_data["name"])
            await page.wait_for_timeout(1000)
            print("✅ Entered project name")

        desc_input = page.locator('textarea[name="description"], textarea[placeholder*="description" i]')
        if await desc_input.count() > 0:
            await desc_input.first.fill(project_data["description"])
            await page.wait_for_timeout(1000)
            print("✅ Entered project description")

        # Select project type
        type_select = page.locator('select[name="type"], select[name="projectType"]')
        if await type_select.count() > 0:
            await type_select.first.select_option(project_data["type"])
            await page.wait_for_timeout(1000)
            print("✅ Selected project type")

        await page.screenshot(path=self.recordings_dir / f"part2_03_form_filled_{self.timestamp}.png")

        # Submit project creation
        submit_button = page.locator('button[type="submit"], button:has-text("Create"), button:has-text("Save")')
        if await submit_button.count() > 0:
            print("✅ Submitting project creation")
            await submit_button.first.click()
            await page.wait_for_timeout(5000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_04_project_created_{self.timestamp}.png")

    async def step_4_model_setup(self, page: Page):
        """Set up the structural model"""
        print("\n🏗️ Step 4: Setting Up Structural Model...")
        
        # Navigate to modeling section
        modeling_nav = page.locator('a:has-text("Model"), button:has-text("Model"), [data-testid="modeling"]')
        if await modeling_nav.count() > 0:
            await modeling_nav.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_05_modeling_interface_{self.timestamp}.png")
        
        # Add nodes/joints
        print("✅ Adding structural nodes...")
        add_node_button = page.locator('button:has-text("Add Node"), button:has-text("Node"), [data-testid="add-node"]')
        if await add_node_button.count() > 0:
            # Add a few nodes for demonstration
            for i in range(3):
                await add_node_button.first.click()
                await page.wait_for_timeout(1000)
                # Simulate clicking on canvas to place nodes
                canvas = page.locator('canvas, .modeling-canvas, .viewport')
                if await canvas.count() > 0:
                    await canvas.first.click(position={"x": 200 + i*150, "y": 300})
                    await page.wait_for_timeout(500)
        
        await page.screenshot(path=self.recordings_dir / f"part2_06_nodes_added_{self.timestamp}.png")
        
        # Add elements/beams
        print("✅ Adding structural elements...")
        add_element_button = page.locator('button:has-text("Add Element"), button:has-text("Beam"), [data-testid="add-element"]')
        if await add_element_button.count() > 0:
            await add_element_button.first.click()
            await page.wait_for_timeout(1000)
            # Simulate connecting nodes
            canvas = page.locator('canvas, .modeling-canvas, .viewport')
            if await canvas.count() > 0:
                await canvas.first.click(position={"x": 200, "y": 300})
                await page.wait_for_timeout(500)
                await canvas.first.click(position={"x": 350, "y": 300})
                await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_07_elements_added_{self.timestamp}.png")

    async def step_5_material_properties(self, page: Page):
        """Set material properties"""
        print("\n🔧 Step 5: Setting Material Properties...")
        
        # Navigate to materials section
        materials_nav = page.locator('a:has-text("Materials"), button:has-text("Materials"), [data-testid="materials"]')
        if await materials_nav.count() > 0:
            await materials_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Select material type
        material_select = page.locator('select[name="material"], .material-selector')
        if await material_select.count() > 0:
            await material_select.first.click()
            await page.wait_for_timeout(1000)
            # Select steel
            steel_option = page.locator('option:has-text("Steel"), .material-option:has-text("Steel")')
            if await steel_option.count() > 0:
                await steel_option.first.click()
                await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_08_materials_{self.timestamp}.png")
        print("✅ Material properties configured")

    async def step_6_loads_supports(self, page: Page):
        """Add loads and supports"""
        print("\n⚖️ Step 6: Adding Loads and Supports...")
        
        # Navigate to loads section
        loads_nav = page.locator('a:has-text("Loads"), button:has-text("Loads"), [data-testid="loads"]')
        if await loads_nav.count() > 0:
            await loads_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Add support
        support_button = page.locator('button:has-text("Add Support"), [data-testid="add-support"]')
        if await support_button.count() > 0:
            await support_button.first.click()
            await page.wait_for_timeout(1000)
            # Click on first node to add support
            canvas = page.locator('canvas, .modeling-canvas, .viewport')
            if await canvas.count() > 0:
                await canvas.first.click(position={"x": 200, "y": 300})
                await page.wait_for_timeout(1000)
        
        # Add load
        load_button = page.locator('button:has-text("Add Load"), [data-testid="add-load"]')
        if await load_button.count() > 0:
            await load_button.first.click()
            await page.wait_for_timeout(1000)
            # Click on middle node to add load
            canvas = page.locator('canvas, .modeling-canvas, .viewport')
            if await canvas.count() > 0:
                await canvas.first.click(position={"x": 350, "y": 300})
                await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_09_loads_supports_{self.timestamp}.png")
        print("✅ Loads and supports added")

    async def run_demo(self):
        """Run the complete Part 2 demo"""
        print("🎬 Starting Part 2: Project Creation & Model Setup Demo")
        print(f"📁 Recordings will be saved to: {self.recordings_dir}")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_login(page)
                await self.step_2_create_project(page)
                await self.step_3_fill_project_details(page)
                await self.step_4_model_setup(page)
                await self.step_5_material_properties(page)
                await self.step_6_loads_supports(page)
                
                print("\n✅ Part 2 Demo completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Error during demo: {e}")
                await page.screenshot(path=self.recordings_dir / f"part2_error_{self.timestamp}.png")
                
            finally:
                # Save video
                await context.close()
                await browser.close()
                
                # Rename video file
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
                    new_video_name = self.recordings_dir / f"part2_project_creation_{self.timestamp}.webm"
                    latest_video.rename(new_video_name)
                    print(f"📹 Video saved as: {new_video_name}")

if __name__ == "__main__":
    demo = Part2ProjectCreation()
    asyncio.run(demo.run_demo())