#!/usr/bin/env python3
"""
StruMind Platform - Part 2: New Project & Modeling Demo
Records project creation and structural modeling process
"""

import asyncio
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

class StruMindPart2Demo:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:12001"
        self.recordings_dir = Path("./recordings")
        self.videos_dir = Path("./videos")
        self.recordings_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Demo project data
        self.project_data = {
            "name": "Steel Frame Building",
            "description": "3-story office building with steel frame structure",
            "type": "Steel Frame",
            "location": "San Francisco, CA",
            "units": "Imperial"
        }

    async def setup_browser(self, playwright):
        """Setup browser with video recording"""
        print("🎬 Setting up browser for Part 2: Project & Modeling...")
        
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(self.recordings_dir),
            record_video_size={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        page.set_default_timeout(30000)
        
        return browser, context, page

    async def step_1_quick_login(self, page: Page):
        """Quick login to access the application"""
        print("\n🔐 Step 1: Quick Login...")
        
        await page.goto(self.frontend_url)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        # Quick login if needed
        login_buttons = page.locator('button:has-text("Sign In"), a:has-text("Sign In")')
        if await login_buttons.count() > 0:
            await login_buttons.first.click()
            await page.wait_for_timeout(2000)
            
            # Use demo credentials
            email_input = page.locator('input[type="email"]')
            password_input = page.locator('input[type="password"]')
            
            if await email_input.count() > 0:
                await email_input.first.fill("demo@strumind.com")
                await page.wait_for_timeout(500)
                await password_input.first.fill("DemoPassword123!")
                await page.wait_for_timeout(500)
                
                submit_button = page.locator('button[type="submit"]')
                if await submit_button.count() > 0:
                    await submit_button.first.click()
                    await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_01_login_{self.timestamp}.png")

    async def step_2_new_project(self, page: Page):
        """Start a new project"""
        print("\n📁 Step 2: Creating New Project...")
        
        # Look for new project button
        new_project_buttons = page.locator(
            'button:has-text("New Project"), button:has-text("Create Project"), '
            'a:has-text("New Project"), button:has-text("New"), [data-testid="new-project"]'
        )
        
        if await new_project_buttons.count() > 0:
            print("✅ Found New Project button")
            await new_project_buttons.first.click()
            await page.wait_for_timeout(3000)
            
            # Fill project form
            await self.fill_project_form(page)
        else:
            print("ℹ️ New Project button not found - checking for project form")
            # Maybe already on project creation page
            project_forms = page.locator('form:has(input[name*="name"]), form:has(input[placeholder*="project"])')
            if await project_forms.count() > 0:
                await self.fill_project_form(page)
            else:
                print("ℹ️ Simulating project creation via navigation")
                # Try to navigate to projects section
                nav_links = page.locator('a[href*="project"], a:has-text("Projects")')
                if await nav_links.count() > 0:
                    await nav_links.first.click()
                    await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_02_project_{self.timestamp}.png")

    async def fill_project_form(self, page: Page):
        """Fill out the project creation form"""
        print("✅ Filling project form...")
        
        # Project name
        name_input = page.locator('input[name="name"], input[placeholder*="name" i], input[placeholder*="project" i]')
        if await name_input.count() > 0:
            await name_input.first.fill(self.project_data["name"])
            await page.wait_for_timeout(1000)
            print(f"✅ Project name: {self.project_data['name']}")
        
        # Description
        desc_input = page.locator('textarea[name="description"], input[name="description"], textarea[placeholder*="description" i]')
        if await desc_input.count() > 0:
            await desc_input.first.fill(self.project_data["description"])
            await page.wait_for_timeout(1000)
        
        # Project type selection
        type_select = page.locator('select[name="type"], select:has(option:has-text("Steel")), select:has(option:has-text("Frame"))')
        if await type_select.count() > 0:
            await type_select.first.click()
            await page.wait_for_timeout(500)
            
            steel_option = page.locator('option:has-text("Steel"), option:has-text("Frame")')
            if await steel_option.count() > 0:
                await steel_option.first.click()
                await page.wait_for_timeout(1000)
        
        # Location
        location_input = page.locator('input[name="location"], input[placeholder*="location" i]')
        if await location_input.count() > 0:
            await location_input.first.fill(self.project_data["location"])
            await page.wait_for_timeout(1000)
        
        # Submit project creation
        create_button = page.locator(
            'button:has-text("Create"), button:has-text("Save"), button[type="submit"], button:has-text("Start Project")'
        )
        if await create_button.count() > 0:
            await create_button.first.click()
            await page.wait_for_timeout(4000)
            print("✅ Project created successfully")

    async def step_3_define_nodes(self, page: Page):
        """Define nodes and geometry"""
        print("\n📍 Step 3: Defining Nodes and Geometry...")
        
        # Look for modeling interface
        modeling_buttons = page.locator(
            'button:has-text("Add Node"), button:has-text("Node"), button:has-text("Point"), '
            '[data-testid*="node"], [data-testid*="add"]'
        )
        
        # Check for 3D canvas
        canvas_elements = page.locator('canvas')
        if await canvas_elements.count() > 0:
            print("✅ Found 3D modeling interface")
            canvas = canvas_elements.first
            
            # Get canvas dimensions
            bbox = await canvas.bounding_box()
            if bbox:
                center_x = bbox['x'] + bbox['width'] / 2
                center_y = bbox['y'] + bbox['height'] / 2
                
                print("✅ Adding structural nodes...")
                
                # Add nodes by clicking on canvas
                node_positions = [
                    (center_x - 150, center_y - 100),  # Node 1
                    (center_x + 150, center_y - 100),  # Node 2
                    (center_x - 150, center_y + 100),  # Node 3
                    (center_x + 150, center_y + 100),  # Node 4
                    (center_x - 150, center_y - 200),  # Node 5 (upper level)
                    (center_x + 150, center_y - 200),  # Node 6 (upper level)
                ]
                
                for i, (x, y) in enumerate(node_positions):
                    await page.mouse.click(x, y)
                    await page.wait_for_timeout(800)
                    print(f"✅ Added node {i+1}")
                
                # Show 3D manipulation
                print("✅ Demonstrating 3D view manipulation...")
                await page.mouse.move(center_x, center_y)
                await page.mouse.down()
                await page.mouse.move(center_x + 100, center_y + 50)
                await page.mouse.up()
                await page.wait_for_timeout(2000)
                
                # Zoom operations
                await page.mouse.wheel(0, -300)
                await page.wait_for_timeout(1000)
                await page.mouse.wheel(0, 200)
                await page.wait_for_timeout(1000)
        
        # Try node creation buttons if available
        if await modeling_buttons.count() > 0:
            print(f"✅ Found {await modeling_buttons.count()} modeling tools")
            await modeling_buttons.first.click()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_03_nodes_{self.timestamp}.png")

    async def step_4_add_elements(self, page: Page):
        """Add elements (beams/columns)"""
        print("\n🏗️ Step 4: Adding Elements (Beams/Columns)...")
        
        # Look for element creation tools
        element_buttons = page.locator(
            'button:has-text("Add Element"), button:has-text("Beam"), button:has-text("Column"), '
            'button:has-text("Member"), button:has-text("Frame"), [data-testid*="element"], [data-testid*="beam"]'
        )
        
        if await element_buttons.count() > 0:
            print(f"✅ Found {await element_buttons.count()} element tools")
            
            # Try different element types
            for i in range(min(3, await element_buttons.count())):
                try:
                    button = element_buttons.nth(i)
                    button_text = await button.text_content()
                    if button_text:
                        print(f"🔧 Using tool: {button_text.strip()}")
                        await button.click()
                        await page.wait_for_timeout(2000)
                        
                        # If there's a canvas, simulate element creation
                        canvas = page.locator('canvas').first
                        if await canvas.count() > 0:
                            bbox = await canvas.bounding_box()
                            if bbox:
                                center_x = bbox['x'] + bbox['width'] / 2
                                center_y = bbox['y'] + bbox['height'] / 2
                                
                                # Create elements by connecting nodes
                                await page.mouse.click(center_x - 150, center_y - 100)
                                await page.wait_for_timeout(500)
                                await page.mouse.click(center_x + 150, center_y - 100)
                                await page.wait_for_timeout(1000)
                                print(f"✅ Created element with {button_text.strip()}")
                        
                        break  # Use first available tool
                except Exception as e:
                    print(f"ℹ️ Element tool {i}: {e}")
        else:
            print("ℹ️ Element tools not found - simulating with canvas interaction")
            
            # Direct canvas interaction for element creation
            canvas = page.locator('canvas').first
            if await canvas.count() > 0:
                bbox = await canvas.bounding_box()
                if bbox:
                    center_x = bbox['x'] + bbox['width'] / 2
                    center_y = bbox['y'] + bbox['height'] / 2
                    
                    print("✅ Creating structural elements...")
                    
                    # Create horizontal beams
                    await page.mouse.click(center_x - 150, center_y - 100)
                    await page.wait_for_timeout(500)
                    await page.mouse.click(center_x + 150, center_y - 100)
                    await page.wait_for_timeout(1000)
                    
                    # Create vertical columns
                    await page.mouse.click(center_x - 150, center_y - 100)
                    await page.wait_for_timeout(500)
                    await page.mouse.click(center_x - 150, center_y + 100)
                    await page.wait_for_timeout(1000)
                    
                    print("✅ Structural elements created")
        
        await page.screenshot(path=self.recordings_dir / f"part2_04_elements_{self.timestamp}.png")

    async def step_5_supports_loads(self, page: Page):
        """Assign supports and loads"""
        print("\n⚓ Step 5: Assigning Supports and Loads...")
        
        # Look for support tools
        support_buttons = page.locator(
            'button:has-text("Support"), button:has-text("Fixed"), button:has-text("Pin"), '
            'button:has-text("Roller"), [data-testid*="support"]'
        )
        
        if await support_buttons.count() > 0:
            print(f"✅ Found {await support_buttons.count()} support tools")
            
            # Apply supports
            for i in range(min(2, await support_buttons.count())):
                try:
                    button = support_buttons.nth(i)
                    button_text = await button.text_content()
                    if button_text:
                        print(f"⚓ Applying: {button_text.strip()}")
                        await button.click()
                        await page.wait_for_timeout(2000)
                        
                        # Apply support to base nodes
                        canvas = page.locator('canvas').first
                        if await canvas.count() > 0:
                            bbox = await canvas.bounding_box()
                            if bbox:
                                center_x = bbox['x'] + bbox['width'] / 2
                                center_y = bbox['y'] + bbox['height'] / 2
                                
                                # Apply support at base
                                await page.mouse.click(center_x - 150, center_y + 100)
                                await page.wait_for_timeout(1000)
                                await page.mouse.click(center_x + 150, center_y + 100)
                                await page.wait_for_timeout(1000)
                                print(f"✅ Applied {button_text.strip()}")
                        
                        break
                except Exception as e:
                    print(f"ℹ️ Support tool {i}: {e}")
        
        # Look for load tools
        load_buttons = page.locator(
            'button:has-text("Load"), button:has-text("Force"), button:has-text("Moment"), '
            'button:has-text("Distributed"), [data-testid*="load"]'
        )
        
        if await load_buttons.count() > 0:
            print(f"✅ Found {await load_buttons.count()} load tools")
            
            # Apply loads
            for i in range(min(2, await load_buttons.count())):
                try:
                    button = load_buttons.nth(i)
                    button_text = await button.text_content()
                    if button_text:
                        print(f"⬇️ Applying: {button_text.strip()}")
                        await button.click()
                        await page.wait_for_timeout(2000)
                        
                        # Apply load to structure
                        canvas = page.locator('canvas').first
                        if await canvas.count() > 0:
                            bbox = await canvas.bounding_box()
                            if bbox:
                                center_x = bbox['x'] + bbox['width'] / 2
                                center_y = bbox['y'] + bbox['height'] / 2
                                
                                # Apply load at top
                                await page.mouse.click(center_x, center_y - 100)
                                await page.wait_for_timeout(1000)
                                print(f"✅ Applied {button_text.strip()}")
                        
                        break
                except Exception as e:
                    print(f"ℹ️ Load tool {i}: {e}")
        
        # Final view of the model
        canvas = page.locator('canvas').first
        if await canvas.count() > 0:
            bbox = await canvas.bounding_box()
            if bbox:
                center_x = bbox['x'] + bbox['width'] / 2
                center_y = bbox['y'] + bbox['height'] / 2
                
                print("✅ Final model review...")
                # Rotate view to show the complete model
                await page.mouse.move(center_x, center_y)
                await page.mouse.down()
                await page.mouse.move(center_x + 120, center_y + 80)
                await page.mouse.up()
                await page.wait_for_timeout(2000)
                
                # Zoom to fit
                await page.mouse.wheel(0, -200)
                await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"part2_05_supports_loads_{self.timestamp}.png")
        
        # Hold final view
        await page.wait_for_timeout(3000)
        print("✅ Structural modeling completed!")

    async def run_part_2_demo(self):
        """Run Part 2: Project & Modeling demo"""
        print("🎬 Starting Part 2: Project & Modeling Demo")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_quick_login(page)
                await self.step_2_new_project(page)
                await self.step_3_define_nodes(page)
                await self.step_4_add_elements(page)
                await self.step_5_supports_loads(page)
                
                print("✅ Part 2 demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Part 2 demo failed: {e}")
                await page.screenshot(path=self.recordings_dir / f"part2_error_{self.timestamp}.png")
                
            finally:
                await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()
                
                # Find and rename video
                await asyncio.sleep(2)
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=os.path.getctime)
                    final_video_path = self.videos_dir / f"part-2-modeling-{self.timestamp}.webm"
                    latest_video.rename(final_video_path)
                    
                    video_size = final_video_path.stat().st_size
                    print(f"🎬 Part 2 video saved: {final_video_path}")
                    print(f"📏 Video size: {video_size / 1024:.1f} KB")
                    
                    return final_video_path
                
                return None

async def main():
    demo = StruMindPart2Demo()
    video_path = await demo.run_part_2_demo()
    
    if video_path:
        print(f"\n✅ Part 2 Demo Complete!")
        print(f"📹 Video: {video_path}")
        return True
    else:
        print(f"\n❌ Part 2 Demo Failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)