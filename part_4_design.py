#!/usr/bin/env python3
"""
StruMind Platform - Part 4: Design Engine Demo
Records design module usage and code-based design checks
"""

import asyncio
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

class StruMindPart4Demo:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:12001"
        self.recordings_dir = Path("./recordings")
        self.videos_dir = Path("./videos")
        self.recordings_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def setup_browser(self, playwright):
        """Setup browser with video recording"""
        print("🎬 Setting up browser for Part 4: Design Engine...")
        
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

    async def step_1_navigate_to_design(self, page: Page):
        """Navigate to design module"""
        print("\n🔧 Step 1: Navigating to Design Module...")
        
        await page.goto(self.frontend_url)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        # Quick login if needed
        login_buttons = page.locator('button:has-text("Sign In"), a:has-text("Sign In")')
        if await login_buttons.count() > 0:
            await login_buttons.first.click()
            await page.wait_for_timeout(2000)
            
            email_input = page.locator('input[type="email"]')
            password_input = page.locator('input[type="password"]')
            
            if await email_input.count() > 0:
                await email_input.first.fill("demo@strumind.com")
                await password_input.first.fill("DemoPassword123!")
                await page.wait_for_timeout(500)
                
                submit_button = page.locator('button[type="submit"]')
                if await submit_button.count() > 0:
                    await submit_button.first.click()
                    await page.wait_for_timeout(3000)
        
        # Navigate to design section
        design_links = page.locator(
            'a:has-text("Design"), button:has-text("Design"), a[href*="design"], '
            'nav a:has-text("Design"), [data-testid*="design"]'
        )
        
        if await design_links.count() > 0:
            print("✅ Found design navigation")
            await design_links.first.click()
            await page.wait_for_timeout(3000)
        else:
            print("ℹ️ Design navigation not found - checking for design interface")
        
        await page.screenshot(path=self.recordings_dir / f"part4_01_navigate_{self.timestamp}.png")

    async def step_2_select_design_module(self, page: Page):
        """Select design module (RC Beam or Steel Column)"""
        print("\n🏗️ Step 2: Selecting Design Module...")
        
        # Look for design module selection
        design_modules = page.locator(
            'button:has-text("Steel"), button:has-text("Concrete"), button:has-text("RC"), '
            'button:has-text("Beam"), button:has-text("Column"), '
            'select:has(option:has-text("Steel")), select:has(option:has-text("Concrete")), '
            'card:has-text("Steel Design"), card:has-text("Concrete Design")'
        )
        
        if await design_modules.count() > 0:
            print(f"✅ Found {await design_modules.count()} design module(s)")
            
            # Try to select Steel Design first
            steel_modules = page.locator(
                'button:has-text("Steel"), option:has-text("Steel"), card:has-text("Steel")'
            )
            
            if await steel_modules.count() > 0:
                print("✅ Selecting Steel Design Module")
                await steel_modules.first.click()
                await page.wait_for_timeout(3000)
                
                # Look for steel member type selection
                steel_types = page.locator(
                    'button:has-text("Column"), button:has-text("Beam"), '
                    'option:has-text("Column"), option:has-text("Beam")'
                )
                
                if await steel_types.count() > 0:
                    print("✅ Selecting Steel Column Design")
                    # Prefer column design
                    column_option = page.locator('button:has-text("Column"), option:has-text("Column")')
                    if await column_option.count() > 0:
                        await column_option.first.click()
                        await page.wait_for_timeout(2000)
                    else:
                        await steel_types.first.click()
                        await page.wait_for_timeout(2000)
            else:
                # Try concrete design
                concrete_modules = page.locator(
                    'button:has-text("Concrete"), button:has-text("RC"), option:has-text("Concrete")'
                )
                
                if await concrete_modules.count() > 0:
                    print("✅ Selecting Concrete Design Module")
                    await concrete_modules.first.click()
                    await page.wait_for_timeout(3000)
                    
                    # Look for concrete member type
                    concrete_types = page.locator(
                        'button:has-text("Beam"), button:has-text("Column"), '
                        'option:has-text("Beam"), option:has-text("Column")'
                    )
                    
                    if await concrete_types.count() > 0:
                        print("✅ Selecting RC Beam Design")
                        beam_option = page.locator('button:has-text("Beam"), option:has-text("Beam")')
                        if await beam_option.count() > 0:
                            await beam_option.first.click()
                            await page.wait_for_timeout(2000)
                        else:
                            await concrete_types.first.click()
                            await page.wait_for_timeout(2000)
                else:
                    # Use first available module
                    print("✅ Selecting first available design module")
                    await design_modules.first.click()
                    await page.wait_for_timeout(3000)
        else:
            print("ℹ️ Design modules not found - checking for design interface")
        
        await page.screenshot(path=self.recordings_dir / f"part4_02_select_module_{self.timestamp}.png")

    async def step_3_input_parameters(self, page: Page):
        """Input parameters or auto-detect from model"""
        print("\n📝 Step 3: Inputting Design Parameters...")
        
        # Look for parameter input fields
        parameter_inputs = page.locator(
            'input[type="number"], input[name*="length"], input[name*="force"], '
            'input[name*="moment"], input[name*="load"], input[placeholder*="kN"], '
            'input[placeholder*="mm"], input[placeholder*="MPa"]'
        )
        
        if await parameter_inputs.count() > 0:
            print(f"✅ Found {await parameter_inputs.count()} parameter input(s)")
            
            # Sample design parameters
            parameters = {
                "length": "6000",      # 6m length
                "force": "500",        # 500 kN axial force
                "moment": "150",       # 150 kN-m moment
                "load": "25",          # 25 kN/m distributed load
                "width": "300",        # 300mm width
                "height": "600",       # 600mm height
                "concrete": "30",      # 30 MPa concrete
                "steel": "420"         # 420 MPa steel
            }
            
            # Fill parameter inputs
            for i in range(min(6, await parameter_inputs.count())):
                try:
                    input_field = parameter_inputs.nth(i)
                    placeholder = await input_field.get_attribute('placeholder')
                    name = await input_field.get_attribute('name')
                    
                    # Determine appropriate value based on field name/placeholder
                    value = "100"  # default
                    
                    if placeholder or name:
                        field_info = str(placeholder).lower() + str(name).lower()
                        
                        if 'length' in field_info or 'span' in field_info:
                            value = parameters["length"]
                        elif 'force' in field_info or 'axial' in field_info:
                            value = parameters["force"]
                        elif 'moment' in field_info:
                            value = parameters["moment"]
                        elif 'load' in field_info:
                            value = parameters["load"]
                        elif 'width' in field_info or 'b' in field_info:
                            value = parameters["width"]
                        elif 'height' in field_info or 'h' in field_info or 'depth' in field_info:
                            value = parameters["height"]
                        elif 'concrete' in field_info or 'fc' in field_info:
                            value = parameters["concrete"]
                        elif 'steel' in field_info or 'fy' in field_info:
                            value = parameters["steel"]
                    
                    await input_field.fill(value)
                    await page.wait_for_timeout(800)
                    print(f"✅ Set parameter {i+1}: {value}")
                    
                except Exception as e:
                    print(f"ℹ️ Parameter {i}: {e}")
        else:
            print("ℹ️ Parameter inputs not found - checking for auto-detect")
        
        # Look for auto-detect or import from model buttons
        auto_detect_buttons = page.locator(
            'button:has-text("Auto"), button:has-text("Import"), button:has-text("Detect"), '
            'button:has-text("From Model"), [data-testid*="auto"]'
        )
        
        if await auto_detect_buttons.count() > 0:
            print("✅ Found auto-detect option")
            await auto_detect_buttons.first.click()
            await page.wait_for_timeout(3000)
            print("✅ Auto-detection completed")
        
        # Look for material selection
        material_selects = page.locator(
            'select:has(option:has-text("Steel")), select:has(option:has-text("Concrete")), '
            'select[name*="material"], select[name*="grade"]'
        )
        
        if await material_selects.count() > 0:
            print("✅ Setting material properties")
            await material_selects.first.click()
            await page.wait_for_timeout(1000)
            
            # Select appropriate material
            material_options = page.locator('option:has-text("A992"), option:has-text("Grade 50"), option:has-text("C30")')
            if await material_options.count() > 0:
                await material_options.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Material selected")
        
        await page.screenshot(path=self.recordings_dir / f"part4_03_parameters_{self.timestamp}.png")

    async def step_4_run_design(self, page: Page):
        """Run code-based design"""
        print("\n🚀 Step 4: Running Code-Based Design...")
        
        # Look for design code selection
        design_codes = page.locator(
            'select:has(option:has-text("AISC")), select:has(option:has-text("ACI")), '
            'button:has-text("AISC"), button:has-text("ACI"), '
            'radio[value*="AISC"], radio[value*="ACI"]'
        )
        
        if await design_codes.count() > 0:
            print("✅ Found design code selection")
            
            # Try to select AISC for steel or ACI for concrete
            aisc_options = page.locator('option:has-text("AISC"), button:has-text("AISC"), radio[value*="AISC"]')
            aci_options = page.locator('option:has-text("ACI"), button:has-text("ACI"), radio[value*="ACI"]')
            
            if await aisc_options.count() > 0:
                print("✅ Selecting AISC 360 design code")
                await aisc_options.first.click()
                await page.wait_for_timeout(2000)
            elif await aci_options.count() > 0:
                print("✅ Selecting ACI 318 design code")
                await aci_options.first.click()
                await page.wait_for_timeout(2000)
            else:
                await design_codes.first.click()
                await page.wait_for_timeout(1000)
        
        # Look for design execution buttons
        design_run_buttons = page.locator(
            'button:has-text("Run Design"), button:has-text("Check"), button:has-text("Calculate"), '
            'button:has-text("Design"), button:has-text("Verify"), button:has-text("Analyze"), '
            '[data-testid*="run"], [data-testid*="design"]'
        )
        
        if await design_run_buttons.count() > 0:
            print("✅ Found design execution button")
            
            run_button_text = await design_run_buttons.first.text_content()
            print(f"🚀 Clicking: {run_button_text}")
            await design_run_buttons.first.click()
            await page.wait_for_timeout(3000)
            
            # Look for progress or confirmation
            progress_elements = page.locator(
                '[role="progressbar"], .progress, .loading, div:has-text("Calculating"), '
                'div:has-text("Checking"), div:has-text("Running")'
            )
            
            if await progress_elements.count() > 0:
                print("✅ Design calculation in progress...")
                await page.wait_for_timeout(5000)  # Wait for design to complete
            else:
                print("✅ Design calculation completed")
                await page.wait_for_timeout(3000)
        else:
            print("ℹ️ Design run button not found - trying API approach")
            
            # Try to trigger design via API
            try:
                response = requests.post(f"{self.backend_url}/api/v1/design/run", 
                                       json={"type": "steel_column", "code": "AISC_360"})
                if response.status_code in [200, 201]:
                    print("✅ Design triggered via API")
                    await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"ℹ️ API design: {e}")
        
        await page.screenshot(path=self.recordings_dir / f"part4_04_run_design_{self.timestamp}.png")

    async def step_5_design_results(self, page: Page):
        """Show design result summary"""
        print("\n📊 Step 5: Viewing Design Results...")
        
        # Look for design results
        result_elements = page.locator(
            'div:has-text("PASS"), div:has-text("FAIL"), div:has-text("OK"), '
            'span:has-text("Adequate"), span:has-text("Inadequate"), '
            '[class*="result"], [class*="status"], .pass, .fail, .ok'
        )
        
        if await result_elements.count() > 0:
            print(f"✅ Found {await result_elements.count()} design result(s)")
            
            # Check result status
            pass_results = page.locator('div:has-text("PASS"), span:has-text("OK"), .pass')
            fail_results = page.locator('div:has-text("FAIL"), span:has-text("INADEQUATE"), .fail')
            
            if await pass_results.count() > 0:
                print("✅ Design checks PASSED")
            elif await fail_results.count() > 0:
                print("⚠️ Design checks FAILED - optimization needed")
            else:
                print("ℹ️ Design status unclear")
        
        # Look for utilization ratios
        ratio_elements = page.locator(
            'td:has-text("%"), span:has-text("ratio"), div:has-text("utilization"), '
            'input[value*="."], [class*="ratio"], [class*="utilization"]'
        )
        
        if await ratio_elements.count() > 0:
            print(f"✅ Found {await ratio_elements.count()} utilization ratio(s)")
            
            # Scroll to show ratios
            await page.evaluate("window.scrollTo(0, 300)")
            await page.wait_for_timeout(2000)
        
        # Look for design summary table
        summary_tables = page.locator(
            'table:has(th:has-text("Check")), table:has(th:has-text("Ratio")), '
            'table:has(td:has-text("PASS")), .summary-table, .design-table'
        )
        
        if await summary_tables.count() > 0:
            print("✅ Found design summary table")
            
            # Scroll through the table
            await page.evaluate("window.scrollTo(0, 400)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 600)")
            await page.wait_for_timeout(2000)
            
            # Click on table rows to show details
            table_rows = summary_tables.first.locator('tr')
            if await table_rows.count() > 1:
                for i in range(min(3, await table_rows.count() - 1)):  # Skip header
                    try:
                        row = table_rows.nth(i + 1)
                        await row.click()
                        await page.wait_for_timeout(1500)
                        print(f"✅ Viewed design check {i+1}")
                    except Exception as e:
                        print(f"ℹ️ Table row {i}: {e}")
        
        # Look for detailed design output
        detail_sections = page.locator(
            'div:has-text("Details"), div:has-text("Calculation"), '
            'section:has-text("Design"), .details, .calculation'
        )
        
        if await detail_sections.count() > 0:
            print("✅ Found detailed design calculations")
            
            # Expand details if needed
            expand_buttons = page.locator('button:has-text("Expand"), button:has-text("Show"), button:has-text("Details")')
            if await expand_buttons.count() > 0:
                await expand_buttons.first.click()
                await page.wait_for_timeout(2000)
                print("✅ Expanded design details")
        
        # Look for design recommendations
        recommendation_elements = page.locator(
            'div:has-text("Recommendation"), div:has-text("Suggestion"), '
            'div:has-text("Optimize"), .recommendation, .suggestion'
        )
        
        if await recommendation_elements.count() > 0:
            print("✅ Found design recommendations")
            
            # Scroll to show recommendations
            await page.evaluate("window.scrollTo(0, 800)")
            await page.wait_for_timeout(2000)
        
        # Final results screenshot
        await page.screenshot(path=self.recordings_dir / f"part4_05_results_{self.timestamp}.png")
        
        # Return to top for final view
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)
        
        # Hold on final results
        await page.wait_for_timeout(4000)
        print("✅ Design results review completed!")

    async def run_part_4_demo(self):
        """Run Part 4: Design Engine demo"""
        print("🎬 Starting Part 4: Design Engine Demo")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_navigate_to_design(page)
                await self.step_2_select_design_module(page)
                await self.step_3_input_parameters(page)
                await self.step_4_run_design(page)
                await self.step_5_design_results(page)
                
                print("✅ Part 4 demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Part 4 demo failed: {e}")
                await page.screenshot(path=self.recordings_dir / f"part4_error_{self.timestamp}.png")
                
            finally:
                await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()
                
                # Find and rename video
                await asyncio.sleep(2)
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=os.path.getctime)
                    final_video_path = self.videos_dir / f"part-4-design-{self.timestamp}.webm"
                    latest_video.rename(final_video_path)
                    
                    video_size = final_video_path.stat().st_size
                    print(f"🎬 Part 4 video saved: {final_video_path}")
                    print(f"📏 Video size: {video_size / 1024:.1f} KB")
                    
                    return final_video_path
                
                return None

async def main():
    demo = StruMindPart4Demo()
    video_path = await demo.run_part_4_demo()
    
    if video_path:
        print(f"\n✅ Part 4 Demo Complete!")
        print(f"📹 Video: {video_path}")
        return True
    else:
        print(f"\n❌ Part 4 Demo Failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)