#!/usr/bin/env python3
"""
StruMind Workflow Demo - Part 3: Structural Analysis
Records the structural analysis process and results visualization.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

class Part3StructuralAnalysis:
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
        print("🎬 Setting up browser for Part 3: Structural Analysis...")
        
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

    async def step_1_navigate_to_analysis(self, page: Page):
        """Navigate to analysis section"""
        print("\n🔬 Step 1: Navigating to Analysis...")
        
        # Login first
        await page.goto(f"{self.frontend_url}/auth/login")
        await page.wait_for_load_state('networkidle')
        await page.fill('input[type="email"]', self.demo_user["email"])
        await page.fill('input[type="password"]', self.demo_user["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Navigate to analysis section
        analysis_nav = page.locator('a:has-text("Analysis"), button:has-text("Analysis"), [data-testid="analysis"]')
        if await analysis_nav.count() > 0:
            await analysis_nav.first.click()
            await page.wait_for_timeout(3000)
        else:
            # Try direct navigation
            await page.goto(f"{self.frontend_url}/analysis")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_01_analysis_page_{self.timestamp}.png")
        print("✅ Navigated to analysis section")

    async def step_2_select_analysis_type(self, page: Page):
        """Select analysis type and parameters"""
        print("\n⚙️ Step 2: Configuring Analysis Parameters...")
        
        # Select analysis type
        analysis_type_select = page.locator('select[name="analysisType"], .analysis-type-selector')
        if await analysis_type_select.count() > 0:
            await analysis_type_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select static analysis
            static_option = page.locator('option:has-text("Static"), .analysis-option:has-text("Static")')
            if await static_option.count() > 0:
                await static_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected Static Analysis")
        
        # Configure analysis parameters
        tolerance_input = page.locator('input[name="tolerance"], input[placeholder*="tolerance" i]')
        if await tolerance_input.count() > 0:
            await tolerance_input.first.fill("0.001")
            await page.wait_for_timeout(1000)
        
        iterations_input = page.locator('input[name="maxIterations"], input[placeholder*="iterations" i]')
        if await iterations_input.count() > 0:
            await iterations_input.first.fill("100")
            await page.wait_for_timeout(1000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_02_analysis_config_{self.timestamp}.png")
        print("✅ Analysis parameters configured")

    async def step_3_run_analysis(self, page: Page):
        """Run the structural analysis"""
        print("\n🚀 Step 3: Running Structural Analysis...")
        
        # Click run analysis button
        run_button = page.locator('button:has-text("Run Analysis"), button:has-text("Start Analysis"), [data-testid="run-analysis"]')
        if await run_button.count() > 0:
            print("✅ Starting analysis...")
            await run_button.first.click()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_03_analysis_started_{self.timestamp}.png")
        
        # Wait for analysis progress
        print("⏳ Waiting for analysis to complete...")
        
        # Look for progress indicators
        progress_bar = page.locator('.progress-bar, .analysis-progress, [data-testid="progress"]')
        if await progress_bar.count() > 0:
            # Wait for progress to complete
            for i in range(10):
                await page.wait_for_timeout(1000)
                progress_text = await page.locator('.progress-text, .status-text').text_content() if await page.locator('.progress-text, .status-text').count() > 0 else ""
                if "complete" in progress_text.lower() or "finished" in progress_text.lower():
                    break
        else:
            # Wait a reasonable time for analysis
            await page.wait_for_timeout(8000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_04_analysis_progress_{self.timestamp}.png")
        print("✅ Analysis completed")

    async def step_4_view_results(self, page: Page):
        """View and explore analysis results"""
        print("\n📊 Step 4: Viewing Analysis Results...")
        
        # Navigate to results section
        results_nav = page.locator('a:has-text("Results"), button:has-text("Results"), [data-testid="results"]')
        if await results_nav.count() > 0:
            await results_nav.first.click()
            await page.wait_for_timeout(3000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_05_results_overview_{self.timestamp}.png")
        
        # View different result types
        result_types = ["Displacement", "Stress", "Forces", "Reactions"]
        
        for result_type in result_types:
            result_tab = page.locator(f'button:has-text("{result_type}"), .result-tab:has-text("{result_type}")')
            if await result_tab.count() > 0:
                print(f"✅ Viewing {result_type} results")
                await result_tab.first.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=self.recordings_dir / f"part3_06_{result_type.lower()}_results_{self.timestamp}.png")
        
        print("✅ Results exploration completed")

    async def step_5_export_results(self, page: Page):
        """Export analysis results"""
        print("\n💾 Step 5: Exporting Results...")
        
        # Look for export button
        export_button = page.locator('button:has-text("Export"), button:has-text("Download"), [data-testid="export-results"]')
        if await export_button.count() > 0:
            await export_button.first.click()
            await page.wait_for_timeout(2000)
            
            # Select export format
            format_select = page.locator('select[name="format"], .export-format-selector')
            if await format_select.count() > 0:
                await format_select.first.select_option("PDF")
                await page.wait_for_timeout(1000)
            
            # Confirm export
            confirm_export = page.locator('button:has-text("Export"), button:has-text("Download"), .export-confirm')
            if await confirm_export.count() > 0:
                await confirm_export.first.click()
                await page.wait_for_timeout(3000)
                print("✅ Results exported")
        
        await page.screenshot(path=self.recordings_dir / f"part3_07_export_complete_{self.timestamp}.png")

    async def step_6_analysis_summary(self, page: Page):
        """Show analysis summary and insights"""
        print("\n📋 Step 6: Analysis Summary...")
        
        # Navigate to summary section
        summary_nav = page.locator('a:has-text("Summary"), button:has-text("Summary"), [data-testid="summary"]')
        if await summary_nav.count() > 0:
            await summary_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Show key metrics
        metrics_section = page.locator('.metrics, .analysis-metrics, .summary-stats')
        if await metrics_section.count() > 0:
            await metrics_section.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part3_08_analysis_summary_{self.timestamp}.png")
        print("✅ Analysis summary reviewed")

    async def run_demo(self):
        """Run the complete Part 3 demo"""
        print("🎬 Starting Part 3: Structural Analysis Demo")
        print(f"📁 Recordings will be saved to: {self.recordings_dir}")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_navigate_to_analysis(page)
                await self.step_2_select_analysis_type(page)
                await self.step_3_run_analysis(page)
                await self.step_4_view_results(page)
                await self.step_5_export_results(page)
                await self.step_6_analysis_summary(page)
                
                print("\n✅ Part 3 Demo completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Error during demo: {e}")
                await page.screenshot(path=self.recordings_dir / f"part3_error_{self.timestamp}.png")
                
            finally:
                # Save video
                await context.close()
                await browser.close()
                
                # Rename video file
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
                    new_video_name = self.recordings_dir / f"part3_structural_analysis_{self.timestamp}.webm"
                    latest_video.rename(new_video_name)
                    print(f"📹 Video saved as: {new_video_name}")

if __name__ == "__main__":
    demo = Part3StructuralAnalysis()
    asyncio.run(demo.run_demo())