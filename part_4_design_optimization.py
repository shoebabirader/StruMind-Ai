#!/usr/bin/env python3
"""
StruMind Workflow Demo - Part 4: Design Optimization
Records the design optimization and code compliance checking process.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

class Part4DesignOptimization:
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
        print("🎬 Setting up browser for Part 4: Design Optimization...")
        
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

    async def step_1_navigate_to_design(self, page: Page):
        """Navigate to design optimization section"""
        print("\n🎯 Step 1: Navigating to Design Optimization...")
        
        # Login first
        await page.goto(f"{self.frontend_url}/auth/login")
        await page.wait_for_load_state('networkidle')
        await page.fill('input[type="email"]', self.demo_user["email"])
        await page.fill('input[type="password"]', self.demo_user["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Navigate to design section
        design_nav = page.locator('a:has-text("Design"), button:has-text("Design"), [data-testid="design"]')
        if await design_nav.count() > 0:
            await design_nav.first.click()
            await page.wait_for_timeout(3000)
        else:
            # Try direct navigation
            await page.goto(f"{self.frontend_url}/design")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part4_01_design_page_{self.timestamp}.png")
        print("✅ Navigated to design optimization section")

    async def step_2_select_design_code(self, page: Page):
        """Select design code and standards"""
        print("\n📋 Step 2: Selecting Design Code and Standards...")
        
        # Select design code
        code_select = page.locator('select[name="designCode"], .design-code-selector')
        if await code_select.count() > 0:
            await code_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select AISC (American Institute of Steel Construction)
            aisc_option = page.locator('option:has-text("AISC"), .code-option:has-text("AISC")')
            if await aisc_option.count() > 0:
                await aisc_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected AISC design code")
        
        # Select load combinations
        load_combo_select = page.locator('select[name="loadCombinations"], .load-combo-selector')
        if await load_combo_select.count() > 0:
            await load_combo_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select LRFD (Load and Resistance Factor Design)
            lrfd_option = page.locator('option:has-text("LRFD"), .combo-option:has-text("LRFD")')
            if await lrfd_option.count() > 0:
                await lrfd_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected LRFD load combinations")
        
        await page.screenshot(path=self.recordings_dir / f"part4_02_design_standards_{self.timestamp}.png")

    async def step_3_optimization_parameters(self, page: Page):
        """Set optimization parameters and objectives"""
        print("\n⚙️ Step 3: Setting Optimization Parameters...")
        
        # Set optimization objective
        objective_select = page.locator('select[name="objective"], .optimization-objective')
        if await objective_select.count() > 0:
            await objective_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select minimize weight
            weight_option = page.locator('option:has-text("Minimize Weight"), .objective-option:has-text("Weight")')
            if await weight_option.count() > 0:
                await weight_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Set objective to minimize weight")
        
        # Set constraints
        deflection_limit = page.locator('input[name="deflectionLimit"], input[placeholder*="deflection" i]')
        if await deflection_limit.count() > 0:
            await deflection_limit.first.fill("L/250")
            await page.wait_for_timeout(1000)
            print("✅ Set deflection limit")
        
        stress_ratio = page.locator('input[name="stressRatio"], input[placeholder*="stress" i]')
        if await stress_ratio.count() > 0:
            await stress_ratio.first.fill("0.9")
            await page.wait_for_timeout(1000)
            print("✅ Set stress ratio limit")
        
        await page.screenshot(path=self.recordings_dir / f"part4_03_optimization_params_{self.timestamp}.png")

    async def step_4_member_sizing(self, page: Page):
        """Configure member sizing options"""
        print("\n📏 Step 4: Configuring Member Sizing...")
        
        # Select member types to optimize
        beam_checkbox = page.locator('input[name="optimizeBeams"], .member-type:has-text("Beams") input')
        if await beam_checkbox.count() > 0:
            await beam_checkbox.first.check()
            await page.wait_for_timeout(1000)
            print("✅ Enabled beam optimization")
        
        column_checkbox = page.locator('input[name="optimizeColumns"], .member-type:has-text("Columns") input')
        if await column_checkbox.count() > 0:
            await column_checkbox.first.check()
            await page.wait_for_timeout(1000)
            print("✅ Enabled column optimization")
        
        # Set section database
        section_db = page.locator('select[name="sectionDatabase"], .section-database-selector')
        if await section_db.count() > 0:
            await section_db.first.click()
            await page.wait_for_timeout(1000)
            
            # Select AISC shapes
            aisc_shapes = page.locator('option:has-text("AISC Shapes"), .db-option:has-text("AISC")')
            if await aisc_shapes.count() > 0:
                await aisc_shapes.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected AISC section database")
        
        await page.screenshot(path=self.recordings_dir / f"part4_04_member_sizing_{self.timestamp}.png")

    async def step_5_run_optimization(self, page: Page):
        """Run the design optimization"""
        print("\n🚀 Step 5: Running Design Optimization...")
        
        # Click run optimization button
        optimize_button = page.locator('button:has-text("Optimize"), button:has-text("Run Optimization"), [data-testid="run-optimization"]')
        if await optimize_button.count() > 0:
            print("✅ Starting optimization...")
            await optimize_button.first.click()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part4_05_optimization_started_{self.timestamp}.png")
        
        # Wait for optimization progress
        print("⏳ Waiting for optimization to complete...")
        
        # Look for progress indicators
        progress_bar = page.locator('.progress-bar, .optimization-progress, [data-testid="progress"]')
        if await progress_bar.count() > 0:
            # Wait for progress to complete
            for i in range(15):
                await page.wait_for_timeout(1000)
                progress_text = await page.locator('.progress-text, .status-text').text_content() if await page.locator('.progress-text, .status-text').count() > 0 else ""
                if "complete" in progress_text.lower() or "finished" in progress_text.lower():
                    break
        else:
            # Wait a reasonable time for optimization
            await page.wait_for_timeout(12000)
        
        await page.screenshot(path=self.recordings_dir / f"part4_06_optimization_progress_{self.timestamp}.png")
        print("✅ Optimization completed")

    async def step_6_review_results(self, page: Page):
        """Review optimization results"""
        print("\n📊 Step 6: Reviewing Optimization Results...")
        
        # Navigate to optimization results
        results_nav = page.locator('a:has-text("Optimization Results"), .optimization-results-tab')
        if await results_nav.count() > 0:
            await results_nav.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part4_07_optimization_results_{self.timestamp}.png")
        
        # View different result categories
        result_categories = ["Weight Reduction", "Code Compliance", "Member Sizes", "Cost Analysis"]
        
        for category in result_categories:
            category_tab = page.locator(f'button:has-text("{category}"), .result-category:has-text("{category}")')
            if await category_tab.count() > 0:
                print(f"✅ Viewing {category}")
                await category_tab.first.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=self.recordings_dir / f"part4_08_{category.lower().replace(' ', '_')}_results_{self.timestamp}.png")
        
        print("✅ Optimization results reviewed")

    async def step_7_code_compliance_check(self, page: Page):
        """Perform code compliance verification"""
        print("\n✅ Step 7: Code Compliance Verification...")
        
        # Navigate to compliance check
        compliance_nav = page.locator('a:has-text("Code Check"), button:has-text("Compliance"), [data-testid="code-check"]')
        if await compliance_nav.count() > 0:
            await compliance_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Run compliance check
        check_button = page.locator('button:has-text("Run Check"), button:has-text("Verify Compliance")')
        if await check_button.count() > 0:
            await check_button.first.click()
            await page.wait_for_timeout(5000)
            print("✅ Code compliance check completed")
        
        await page.screenshot(path=self.recordings_dir / f"part4_09_code_compliance_{self.timestamp}.png")

    async def run_demo(self):
        """Run the complete Part 4 demo"""
        print("🎬 Starting Part 4: Design Optimization Demo")
        print(f"📁 Recordings will be saved to: {self.recordings_dir}")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_navigate_to_design(page)
                await self.step_2_select_design_code(page)
                await self.step_3_optimization_parameters(page)
                await self.step_4_member_sizing(page)
                await self.step_5_run_optimization(page)
                await self.step_6_review_results(page)
                await self.step_7_code_compliance_check(page)
                
                print("\n✅ Part 4 Demo completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Error during demo: {e}")
                await page.screenshot(path=self.recordings_dir / f"part4_error_{self.timestamp}.png")
                
            finally:
                # Save video
                await context.close()
                await browser.close()
                
                # Rename video file
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
                    new_video_name = self.recordings_dir / f"part4_design_optimization_{self.timestamp}.webm"
                    latest_video.rename(new_video_name)
                    print(f"📹 Video saved as: {new_video_name}")

if __name__ == "__main__":
    demo = Part4DesignOptimization()
    asyncio.run(demo.run_demo())