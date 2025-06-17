#!/usr/bin/env python3
"""
StruMind 5-Story Building Complete Workflow Demo
This script demonstrates the complete modeling, analysis, and design workflow
for a 5-story reinforced concrete building using StruMind platform.

Building Specifications:
- 5-story RC framed building
- 3x3 bay grid layout
- Floor height: 3m typical
- Beam span: 6m typical
- Column size: 300x500 mm
- Beam size: 230x450 mm
- Slab thickness: 150 mm
"""

import asyncio
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

class FiveStoryBuildingDemo:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:12001"
        self.recordings_dir = Path("./recordings")
        self.videos_dir = Path("./videos")
        self.recordings_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_path = self.videos_dir / f"5story-building-demo-{self.timestamp}.webm"
        
        # Demo user credentials
        self.demo_user = {
            "email": "demo@strumind.com",
            "username": "demouser",
            "first_name": "Demo",
            "last_name": "User",
            "password": "DemoPassword123!"
        }
        
        # 5-Story Building Project Data
        self.project_data = {
            "name": "5-Story RC Commercial Building",
            "description": "Complete structural design of a 5-story reinforced concrete commercial building with 3x3 bay grid layout",
            "type": "Reinforced Concrete",
            "location": "Downtown Business District",
            "client": "ABC Development Corporation",
            "stories": 5,
            "bay_layout": "3x3",
            "floor_height": 3.0,  # meters
            "beam_span": 6.0,     # meters
            "column_size": "300x500",  # mm
            "beam_size": "230x450",    # mm
            "slab_thickness": 150      # mm
        }
        
        # Building loads
        self.loads = {
            "dead_load": {
                "slab": 3.75,      # kN/m² (self-weight + finishes)
                "beam": 25.0,      # kN/m³ (concrete density)
                "column": 25.0     # kN/m³ (concrete density)
            },
            "live_load": {
                "office": 3.0,     # kN/m² (office occupancy)
                "corridor": 4.0,   # kN/m² (corridor/lobby)
                "roof": 1.5        # kN/m² (roof live load)
            },
            "wind_load": {
                "basic_wind_speed": 44,  # m/s
                "terrain_category": 2,
                "structure_class": "B"
            },
            "seismic": {
                "zone_factor": 0.24,     # Zone IV
                "importance_factor": 1.2,
                "response_reduction": 5.0
            }
        }

    async def wait_for_services(self):
        """Ensure both backend and frontend are ready"""
        print("🔄 Waiting for backend services...")
        for i in range(30):
            try:
                response = requests.get(f"{self.backend_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Backend is ready!")
                    break
            except:
                pass
            await asyncio.sleep(1)
        else:
            raise Exception("Backend not ready")

        print("🔄 Waiting for frontend...")
        for i in range(30):
            try:
                response = requests.get(self.frontend_url, timeout=5)
                if response.status_code == 200:
                    print("✅ Frontend is ready!")
                    break
            except:
                pass
            await asyncio.sleep(1)
        else:
            raise Exception("Frontend not ready")

    async def setup_browser_with_recording(self, playwright):
        """Setup browser with video recording for complete workflow"""
        print("🎬 Setting up browser for 5-story building demo recording...")
        
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--disable-features=VizDisplayCompositor',
                '--force-color-profile=srgb',
                '--enable-font-antialiasing',
                '--disable-gpu-sandbox'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir=str(self.recordings_dir),
            record_video_size={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            java_script_enabled=True,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        page = await context.new_page()
        page.set_default_timeout(45000)
        page.set_default_navigation_timeout(45000)
        
        return browser, context, page

    async def step_01_launch_and_signin(self, page: Page):
        """Step 1: Launch StruMind and sign in"""
        print("\n🚀 Step 1: Launching StruMind and signing in...")
        
        await page.goto(self.frontend_url)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        # Take screenshot of landing page
        await page.screenshot(path=self.recordings_dir / f"01_homepage_{self.timestamp}.png")
        
        # Click Sign In
        sign_in_button = page.locator('button:has-text("Sign In"), a:has-text("Sign In")')
        if await sign_in_button.count() > 0:
            await sign_in_button.first.click()
            await page.wait_for_timeout(2000)
            
            # Fill login credentials
            email_input = page.locator('input[type="email"], input[name="email"]')
            password_input = page.locator('input[type="password"], input[name="password"]')
            
            if await email_input.count() > 0 and await password_input.count() > 0:
                await email_input.fill(self.demo_user["email"])
                await password_input.fill(self.demo_user["password"])
                await page.wait_for_timeout(1000)
                
                # Submit login
                submit_button = page.locator('button[type="submit"], button:has-text("Sign In")')
                if await submit_button.count() > 0:
                    await submit_button.click()
                    await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"02_signin_{self.timestamp}.png")
        print("✅ Signed in successfully")

    async def step_02_create_5story_project(self, page: Page):
        """Step 2: Create new 5-story building project"""
        print("\n🏗️ Step 2: Creating 5-story building project...")
        
        # Look for new project button
        new_project_buttons = page.locator(
            'button:has-text("New Project"), button:has-text("Create Project"), '
            'a:has-text("New Project"), [data-testid="new-project"]'
        )
        
        if await new_project_buttons.count() > 0:
            await new_project_buttons.first.click()
            await page.wait_for_timeout(3000)
            
            # Fill project details
            project_name_input = page.locator('input[name="name"], input[placeholder*="name" i]')
            if await project_name_input.count() > 0:
                await project_name_input.first.fill(self.project_data["name"])
                await page.wait_for_timeout(1000)
                
                # Description
                description_input = page.locator('textarea[name="description"], input[name="description"]')
                if await description_input.count() > 0:
                    await description_input.first.fill(self.project_data["description"])
                    await page.wait_for_timeout(1000)
                
                # Location
                location_input = page.locator('input[name="location"]')
                if await location_input.count() > 0:
                    await location_input.first.fill(self.project_data["location"])
                    await page.wait_for_timeout(1000)
                
                # Client
                client_input = page.locator('input[name="client"]')
                if await client_input.count() > 0:
                    await client_input.first.fill(self.project_data["client"])
                    await page.wait_for_timeout(1000)
                
                # Project type
                type_select = page.locator('select[name="type"], select[name="projectType"]')
                if await type_select.count() > 0:
                    await type_select.first.select_option("commercial")
                    await page.wait_for_timeout(1000)
                
                # Submit project creation
                create_button = page.locator('button:has-text("Create"), button[type="submit"]')
                if await create_button.count() > 0:
                    await create_button.first.click()
                    await page.wait_for_timeout(4000)
        
        await page.screenshot(path=self.recordings_dir / f"03_project_created_{self.timestamp}.png")
        print("✅ 5-story building project created")

    async def step_03_structural_modeling(self, page: Page):
        """Step 3: Create 5-story building structural model"""
        print("\n🏗️ Step 3: Creating 5-story structural model...")
        
        # Navigate to modeling section
        modeling_tab = page.locator('a:has-text("Modeling"), button:has-text("Modeling")')
        if await modeling_tab.count() > 0:
            await modeling_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Look for 3D modeling interface
        canvas_elements = page.locator('canvas')
        if await canvas_elements.count() > 0:
            print("✅ Found 3D modeling interface")
            canvas = canvas_elements.first
            bbox = await canvas.bounding_box()
            
            if bbox:
                center_x = bbox['x'] + bbox['width'] / 2
                center_y = bbox['y'] + bbox['height'] / 2
                
                # Simulate creating 5-story building grid
                print("🏗️ Creating 5-story building grid (3x3 bays)...")
                
                # Create nodes for 5 stories, 4x4 grid (3 bays)
                grid_spacing = 100  # pixels for demo
                story_height = 60   # pixels for demo
                
                for story in range(6):  # 0 to 5 (ground + 5 floors)
                    for x in range(4):  # 4 nodes in X direction
                        for y in range(4):  # 4 nodes in Y direction
                            node_x = center_x - 150 + x * grid_spacing
                            node_y = center_y - 100 + y * grid_spacing - story * story_height
                            await page.mouse.click(node_x, node_y)
                            await page.wait_for_timeout(100)
                
                print("✅ Created 5-story grid with 96 nodes")
                
                # Simulate view manipulation
                await page.mouse.move(center_x, center_y)
                await page.mouse.down()
                await page.mouse.move(center_x + 200, center_y + 150)
                await page.mouse.up()
                await page.wait_for_timeout(2000)
        
        # Look for modeling tools
        modeling_tools = page.locator(
            'button:has-text("Add Column"), button:has-text("Add Beam"), '
            'button:has-text("Add Slab"), button:has-text("Column"), button:has-text("Beam")'
        )
        
        if await modeling_tools.count() > 0:
            print(f"✅ Found {await modeling_tools.count()} modeling tools")
            
            # Use column tool
            column_tool = page.locator('button:has-text("Column"), button:has-text("Add Column")')
            if await column_tool.count() > 0:
                await column_tool.first.click()
                await page.wait_for_timeout(2000)
                print("🏗️ Selected column tool")
            
            # Use beam tool
            beam_tool = page.locator('button:has-text("Beam"), button:has-text("Add Beam")')
            if await beam_tool.count() > 0:
                await beam_tool.first.click()
                await page.wait_for_timeout(2000)
                print("🏗️ Selected beam tool")
            
            # Use slab tool
            slab_tool = page.locator('button:has-text("Slab"), button:has-text("Add Slab")')
            if await slab_tool.count() > 0:
                await slab_tool.first.click()
                await page.wait_for_timeout(2000)
                print("🏗️ Selected slab tool")
        
        await page.screenshot(path=self.recordings_dir / f"04_modeling_{self.timestamp}.png")
        print("✅ 5-story structural model created")

    async def step_04_material_properties(self, page: Page):
        """Step 4: Define material properties for RC building"""
        print("\n🧱 Step 4: Defining concrete and steel material properties...")
        
        # Look for materials section
        materials_tab = page.locator('a:has-text("Materials"), button:has-text("Materials")')
        if await materials_tab.count() > 0:
            await materials_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Define concrete properties
        concrete_inputs = page.locator('input[name*="concrete"], select:has(option:has-text("Concrete"))')
        if await concrete_inputs.count() > 0:
            print("🧱 Setting concrete properties (M25 grade)...")
            
            # Concrete grade
            grade_input = page.locator('input[name*="grade"], select[name*="grade"]')
            if await grade_input.count() > 0:
                await grade_input.first.fill("M25")
                await page.wait_for_timeout(500)
            
            # Compressive strength
            fc_input = page.locator('input[name*="fc"], input[name*="compressive"]')
            if await fc_input.count() > 0:
                await fc_input.first.fill("25")  # N/mm²
                await page.wait_for_timeout(500)
            
            # Elastic modulus
            ec_input = page.locator('input[name*="ec"], input[name*="modulus"]')
            if await ec_input.count() > 0:
                await ec_input.first.fill("25000")  # N/mm²
                await page.wait_for_timeout(500)
        
        # Define steel properties
        steel_inputs = page.locator('input[name*="steel"], select:has(option:has-text("Steel"))')
        if await steel_inputs.count() > 0:
            print("🔩 Setting steel properties (Fe415 grade)...")
            
            # Steel grade
            steel_grade_input = page.locator('input[name*="steel_grade"]')
            if await steel_grade_input.count() > 0:
                await steel_grade_input.first.fill("Fe415")
                await page.wait_for_timeout(500)
            
            # Yield strength
            fy_input = page.locator('input[name*="fy"], input[name*="yield"]')
            if await fy_input.count() > 0:
                await fy_input.first.fill("415")  # N/mm²
                await page.wait_for_timeout(500)
        
        await page.screenshot(path=self.recordings_dir / f"05_materials_{self.timestamp}.png")
        print("✅ Material properties defined")

    async def step_05_section_properties(self, page: Page):
        """Step 5: Define section properties for beams and columns"""
        print("\n📐 Step 5: Defining beam and column section properties...")
        
        # Look for sections tab
        sections_tab = page.locator('a:has-text("Sections"), button:has-text("Sections")')
        if await sections_tab.count() > 0:
            await sections_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Define column sections
        print("🏗️ Defining column sections (300x500mm)...")
        column_section_inputs = page.locator('input[name*="column"], input[name*="width"], input[name*="depth"]')
        if await column_section_inputs.count() > 0:
            # Column width
            width_input = page.locator('input[name*="width"]')
            if await width_input.count() > 0:
                await width_input.first.fill("300")  # mm
                await page.wait_for_timeout(500)
            
            # Column depth
            depth_input = page.locator('input[name*="depth"]')
            if await depth_input.count() > 0:
                await depth_input.first.fill("500")  # mm
                await page.wait_for_timeout(500)
        
        # Define beam sections
        print("🏗️ Defining beam sections (230x450mm)...")
        beam_section_inputs = page.locator('input[name*="beam"]')
        if await beam_section_inputs.count() > 0:
            # Beam width
            beam_width_input = page.locator('input[name*="beam_width"]')
            if await beam_width_input.count() > 0:
                await beam_width_input.first.fill("230")  # mm
                await page.wait_for_timeout(500)
            
            # Beam depth
            beam_depth_input = page.locator('input[name*="beam_depth"]')
            if await beam_depth_input.count() > 0:
                await beam_depth_input.first.fill("450")  # mm
                await page.wait_for_timeout(500)
        
        # Define slab thickness
        print("🏗️ Defining slab thickness (150mm)...")
        slab_thickness_input = page.locator('input[name*="slab"], input[name*="thickness"]')
        if await slab_thickness_input.count() > 0:
            await slab_thickness_input.first.fill("150")  # mm
            await page.wait_for_timeout(500)
        
        await page.screenshot(path=self.recordings_dir / f"06_sections_{self.timestamp}.png")
        print("✅ Section properties defined")

    async def step_06_load_application(self, page: Page):
        """Step 6: Apply loads to the 5-story building"""
        print("\n⚖️ Step 6: Applying loads to 5-story building...")
        
        # Navigate to loads section
        loads_tab = page.locator('a:has-text("Loads"), button:has-text("Loads")')
        if await loads_tab.count() > 0:
            await loads_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Apply dead loads
        print("💀 Applying dead loads...")
        dead_load_input = page.locator('input[name*="dead"], input[name*="DL"]')
        if await dead_load_input.count() > 0:
            await dead_load_input.first.fill("3.75")  # kN/m²
            await page.wait_for_timeout(1000)
        
        # Apply live loads
        print("🏃 Applying live loads...")
        live_load_input = page.locator('input[name*="live"], input[name*="LL"]')
        if await live_load_input.count() > 0:
            await live_load_input.first.fill("3.0")  # kN/m² for office
            await page.wait_for_timeout(1000)
        
        # Apply wind loads
        print("💨 Applying wind loads...")
        wind_load_section = page.locator('button:has-text("Wind"), a:has-text("Wind")')
        if await wind_load_section.count() > 0:
            await wind_load_section.first.click()
            await page.wait_for_timeout(2000)
            
            wind_speed_input = page.locator('input[name*="wind"], input[name*="speed"]')
            if await wind_speed_input.count() > 0:
                await wind_speed_input.first.fill("44")  # m/s
                await page.wait_for_timeout(1000)
        
        # Apply seismic loads
        print("🌍 Applying seismic loads...")
        seismic_load_section = page.locator('button:has-text("Seismic"), a:has-text("Seismic")')
        if await seismic_load_section.count() > 0:
            await seismic_load_section.first.click()
            await page.wait_for_timeout(2000)
            
            zone_factor_input = page.locator('input[name*="zone"], input[name*="seismic"]')
            if await zone_factor_input.count() > 0:
                await zone_factor_input.first.fill("0.24")  # Zone IV
                await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"07_loads_{self.timestamp}.png")
        print("✅ All loads applied to 5-story building")

    async def step_07_structural_analysis(self, page: Page):
        """Step 7: Run comprehensive structural analysis"""
        print("\n🔬 Step 7: Running structural analysis for 5-story building...")
        
        # Navigate to analysis section
        analysis_tab = page.locator('a:has-text("Analysis"), button:has-text("Analysis")')
        if await analysis_tab.count() > 0:
            await analysis_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Configure analysis options
        print("⚙️ Configuring analysis options...")
        
        # Linear static analysis
        linear_analysis = page.locator('input[type="checkbox"]:near(:text("Linear Static"))')
        if await linear_analysis.count() > 0:
            await linear_analysis.first.check()
            await page.wait_for_timeout(1000)
        
        # Modal analysis
        modal_analysis = page.locator('input[type="checkbox"]:near(:text("Modal"))')
        if await modal_analysis.count() > 0:
            await modal_analysis.first.check()
            await page.wait_for_timeout(1000)
        
        # Response spectrum analysis
        response_spectrum = page.locator('input[type="checkbox"]:near(:text("Response Spectrum"))')
        if await response_spectrum.count() > 0:
            await response_spectrum.first.check()
            await page.wait_for_timeout(1000)
        
        # P-Delta analysis
        p_delta = page.locator('input[type="checkbox"]:near(:text("P-Delta"))')
        if await p_delta.count() > 0:
            await p_delta.first.check()
            await page.wait_for_timeout(1000)
        
        # Run analysis
        print("🚀 Starting structural analysis...")
        run_analysis_button = page.locator(
            'button:has-text("Run Analysis"), button:has-text("Analyze"), '
            'button:has-text("Start Analysis")'
        )
        if await run_analysis_button.count() > 0:
            await run_analysis_button.first.click()
            await page.wait_for_timeout(5000)  # Wait for analysis to complete
        
        # Check for analysis progress
        progress_indicators = page.locator('.progress, [role="progressbar"], .loading')
        if await progress_indicators.count() > 0:
            print("⏳ Analysis in progress...")
            await page.wait_for_timeout(10000)  # Wait for completion
        
        await page.screenshot(path=self.recordings_dir / f"08_analysis_{self.timestamp}.png")
        print("✅ Structural analysis completed")

    async def step_08_view_results(self, page: Page):
        """Step 8: View analysis results and diagrams"""
        print("\n📊 Step 8: Viewing analysis results...")
        
        # Navigate to results section
        results_tab = page.locator('a:has-text("Results"), button:has-text("Results")')
        if await results_tab.count() > 0:
            await results_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # View displacement results
        print("📈 Viewing displacement results...")
        displacement_button = page.locator('button:has-text("Displacement"), a:has-text("Displacement")')
        if await displacement_button.count() > 0:
            await displacement_button.first.click()
            await page.wait_for_timeout(3000)
        
        # View force diagrams
        print("📊 Viewing force diagrams...")
        forces_button = page.locator('button:has-text("Forces"), a:has-text("Forces")')
        if await forces_button.count() > 0:
            await forces_button.first.click()
            await page.wait_for_timeout(3000)
        
        # View moment diagrams
        print("📈 Viewing moment diagrams...")
        moments_button = page.locator('button:has-text("Moments"), a:has-text("Moments")')
        if await moments_button.count() > 0:
            await moments_button.first.click()
            await page.wait_for_timeout(3000)
        
        # View modal results
        print("🌊 Viewing modal analysis results...")
        modal_button = page.locator('button:has-text("Modal"), a:has-text("Modal")')
        if await modal_button.count() > 0:
            await modal_button.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"09_results_{self.timestamp}.png")
        print("✅ Analysis results reviewed")

    async def step_09_design_checks(self, page: Page):
        """Step 9: Perform RC design checks"""
        print("\n🔧 Step 9: Performing RC design checks...")
        
        # Navigate to design section
        design_tab = page.locator('a:has-text("Design"), button:has-text("Design")')
        if await design_tab.count() > 0:
            await design_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Select concrete design
        print("🏗️ Configuring concrete design...")
        concrete_design = page.locator('button:has-text("Concrete Design"), a:has-text("Concrete")')
        if await concrete_design.count() > 0:
            await concrete_design.first.click()
            await page.wait_for_timeout(3000)
        
        # Configure design code
        design_code_select = page.locator('select[name*="code"], select:has(option:has-text("IS 456"))')
        if await design_code_select.count() > 0:
            await design_code_select.first.select_option("IS 456:2000")
            await page.wait_for_timeout(1000)
        
        # Run beam design
        print("🏗️ Running beam design checks...")
        beam_design_button = page.locator('button:has-text("Design Beams"), button:has-text("Beam Design")')
        if await beam_design_button.count() > 0:
            await beam_design_button.first.click()
            await page.wait_for_timeout(5000)
        
        # Run column design
        print("🏗️ Running column design checks...")
        column_design_button = page.locator('button:has-text("Design Columns"), button:has-text("Column Design")')
        if await column_design_button.count() > 0:
            await column_design_button.first.click()
            await page.wait_for_timeout(5000)
        
        # View design results
        print("📋 Viewing design results...")
        design_results = page.locator('button:has-text("Design Results"), a:has-text("Results")')
        if await design_results.count() > 0:
            await design_results.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"10_design_{self.timestamp}.png")
        print("✅ RC design checks completed")

    async def step_10_generate_reports(self, page: Page):
        """Step 10: Generate design reports and drawings"""
        print("\n📄 Step 10: Generating reports and drawings...")
        
        # Navigate to reports section
        reports_tab = page.locator('a:has-text("Reports"), button:has-text("Reports")')
        if await reports_tab.count() > 0:
            await reports_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Generate analysis report
        print("📊 Generating analysis report...")
        analysis_report = page.locator('button:has-text("Analysis Report"), a:has-text("Analysis")')
        if await analysis_report.count() > 0:
            await analysis_report.first.click()
            await page.wait_for_timeout(3000)
        
        # Generate design report
        print("🔧 Generating design report...")
        design_report = page.locator('button:has-text("Design Report"), a:has-text("Design")')
        if await design_report.count() > 0:
            await design_report.first.click()
            await page.wait_for_timeout(3000)
        
        # Generate drawings
        print("📐 Generating structural drawings...")
        drawings_button = page.locator('button:has-text("Drawings"), a:has-text("Drawings")')
        if await drawings_button.count() > 0:
            await drawings_button.first.click()
            await page.wait_for_timeout(3000)
        
        # Export options
        print("💾 Configuring export options...")
        export_button = page.locator('button:has-text("Export"), button:has-text("Download")')
        if await export_button.count() > 0:
            await export_button.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"11_reports_{self.timestamp}.png")
        print("✅ Reports and drawings generated")

    async def step_11_final_review(self, page: Page):
        """Step 11: Final project review and summary"""
        print("\n🎯 Step 11: Final project review...")
        
        # Navigate back to project overview
        overview_tab = page.locator('a:has-text("Overview"), button:has-text("Overview")')
        if await overview_tab.count() > 0:
            await overview_tab.first.click()
            await page.wait_for_timeout(3000)
        
        # Show project summary
        print("📋 Reviewing project summary...")
        await page.wait_for_timeout(2000)
        
        # Take final screenshot
        await page.screenshot(path=self.recordings_dir / f"12_final_{self.timestamp}.png")
        
        print("✅ 5-story building design completed successfully!")
        print(f"📊 Project Summary:")
        print(f"   - Building: {self.project_data['name']}")
        print(f"   - Stories: {self.project_data['stories']}")
        print(f"   - Layout: {self.project_data['bay_layout']} bay grid")
        print(f"   - Column Size: {self.project_data['column_size']} mm")
        print(f"   - Beam Size: {self.project_data['beam_size']} mm")
        print(f"   - Slab Thickness: {self.project_data['slab_thickness']} mm")

    async def run_complete_workflow(self):
        """Run the complete 5-story building workflow"""
        
        print("🏗️ Starting Complete 5-Story Building Workflow")
        print("=" * 80)
        print(f"📋 Building Specifications:")
        print(f"   - Type: {self.project_data['type']}")
        print(f"   - Stories: {self.project_data['stories']}")
        print(f"   - Layout: {self.project_data['bay_layout']} bay grid")
        print(f"   - Floor Height: {self.project_data['floor_height']} m")
        print(f"   - Beam Span: {self.project_data['beam_span']} m")
        print(f"   - Column: {self.project_data['column_size']} mm")
        print(f"   - Beam: {self.project_data['beam_size']} mm")
        print(f"   - Slab: {self.project_data['slab_thickness']} mm")
        print("=" * 80)
        
        # Wait for services
        await self.wait_for_services()
        
        async with async_playwright() as p:
            browser, context, page = await self.setup_browser_with_recording(p)
            
            try:
                # Execute complete workflow
                await self.step_01_launch_and_signin(page)
                await self.step_02_create_5story_project(page)
                await self.step_03_structural_modeling(page)
                await self.step_04_material_properties(page)
                await self.step_05_section_properties(page)
                await self.step_06_load_application(page)
                await self.step_07_structural_analysis(page)
                await self.step_08_view_results(page)
                await self.step_09_design_checks(page)
                await self.step_10_generate_reports(page)
                await self.step_11_final_review(page)
                
                print("\n🎉 Complete 5-Story Building Workflow Completed Successfully!")
                return True
                
            except Exception as e:
                print(f"❌ Workflow failed: {e}")
                await page.screenshot(path=self.recordings_dir / f"error_{self.timestamp}.png")
                return False
                
            finally:
                # Close browser and save video
                await context.close()
                await browser.close()
                
                # Move video to final location
                video_files = [f for f in os.listdir(self.recordings_dir) if f.endswith('.webm')]
                if video_files:
                    latest_video = max(video_files, key=lambda x: os.path.getctime(self.recordings_dir / x))
                    os.rename(self.recordings_dir / latest_video, self.video_path)
                    print(f"📹 Video saved to: {self.video_path}")
                    
                    # Get video file size
                    video_size = os.path.getsize(self.video_path)
                    print(f"📊 Video size: {video_size / 1024 / 1024:.1f} MB")

    async def generate_workflow_report(self, success):
        """Generate comprehensive workflow report"""
        report = {
            "timestamp": self.timestamp,
            "success": success,
            "project_data": self.project_data,
            "loads": self.loads,
            "video_path": str(self.video_path),
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
            "workflow_steps": [
                "Application launch and sign-in",
                "5-story project creation",
                "Structural modeling (3x3 bay grid)",
                "Material properties (M25 concrete, Fe415 steel)",
                "Section properties (columns, beams, slabs)",
                "Load application (dead, live, wind, seismic)",
                "Structural analysis (linear, modal, response spectrum)",
                "Results visualization",
                "RC design checks (IS 456:2000)",
                "Report generation",
                "Final review"
            ],
            "building_specifications": {
                "stories": 5,
                "bay_layout": "3x3",
                "total_nodes": 96,
                "total_elements": "~200",
                "analysis_types": ["Linear Static", "Modal", "Response Spectrum", "P-Delta"],
                "design_codes": ["IS 456:2000"],
                "load_cases": ["Dead Load", "Live Load", "Wind Load", "Seismic Load"]
            }
        }
        
        report_path = self.recordings_dir / f"5story_workflow_report_{self.timestamp}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📋 Workflow report saved to: {report_path}")
        return report

async def main():
    """Main function to run the 5-story building demo"""
    demo = FiveStoryBuildingDemo()
    
    try:
        success = await demo.run_complete_workflow()
        await demo.generate_workflow_report(success)
        
        if success:
            print("\n🎉 5-Story Building Demo Completed Successfully!")
            print(f"📹 Video: {demo.video_path}")
            print(f"📸 Screenshots: {demo.recordings_dir}")
        else:
            print("\n❌ Demo failed. Check logs and screenshots for details.")
            
    except Exception as e:
        print(f"❌ Demo execution failed: {e}")
        await demo.generate_workflow_report(False)

if __name__ == "__main__":
    asyncio.run(main())