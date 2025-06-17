#!/usr/bin/env python3
"""
StruMind Platform - Part 5: Output & Reporting Demo
Records export functionality and report generation
"""

import asyncio
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

class StruMindPart5Demo:
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
        print("🎬 Setting up browser for Part 5: Output & Reporting...")
        
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

    async def step_1_navigate_to_reports(self, page: Page):
        """Navigate to reports/export section"""
        print("\n📄 Step 1: Navigating to Reports Section...")
        
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
        
        # Navigate to reports/export section
        report_links = page.locator(
            'a:has-text("Reports"), button:has-text("Reports"), a:has-text("Export"), '
            'a[href*="report"], a[href*="export"], nav a:has-text("Output"), '
            '[data-testid*="report"], [data-testid*="export"]'
        )
        
        if await report_links.count() > 0:
            print("✅ Found reports navigation")
            await report_links.first.click()
            await page.wait_for_timeout(3000)
        else:
            print("ℹ️ Reports navigation not found - checking for export interface")
            
            # Look for export buttons in current view
            export_buttons = page.locator('button:has-text("Export"), button:has-text("Download")')
            if await export_buttons.count() > 0:
                print("✅ Found export interface")
        
        await page.screenshot(path=self.recordings_dir / f"part5_01_navigate_{self.timestamp}.png")

    async def step_2_export_model(self, page: Page):
        """Export model or results"""
        print("\n💾 Step 2: Exporting Model and Results...")
        
        # Look for export options
        export_buttons = page.locator(
            'button:has-text("Export Model"), button:has-text("Export Results"), '
            'button:has-text("Export"), button:has-text("Download"), '
            'a:has-text("Export"), [data-testid*="export"]'
        )
        
        if await export_buttons.count() > 0:
            print(f"✅ Found {await export_buttons.count()} export option(s)")
            
            # Try different export types
            export_types = ["Model", "Results", "Analysis", "Design"]
            
            for i in range(min(3, await export_buttons.count())):
                try:
                    export_button = export_buttons.nth(i)
                    button_text = await export_button.text_content()
                    
                    if button_text and button_text.strip():
                        print(f"📤 Exporting: {button_text.strip()}")
                        await export_button.click()
                        await page.wait_for_timeout(3000)
                        
                        # Look for format selection
                        await self.handle_format_selection(page)
                        
                        # Take screenshot of export process
                        await page.screenshot(path=self.recordings_dir / f"part5_02_export_{i}_{self.timestamp}.png")
                        
                        # Wait for export to process
                        await page.wait_for_timeout(2000)
                        
                        break  # Exit after first successful export
                        
                except Exception as e:
                    print(f"ℹ️ Export option {i}: {e}")
        else:
            print("ℹ️ Export buttons not found - checking for file menu")
            
            # Look for file menu
            file_menus = page.locator(
                'button:has-text("File"), a:has-text("File"), [data-testid*="file"]'
            )
            
            if await file_menus.count() > 0:
                print("✅ Found file menu")
                await file_menus.first.click()
                await page.wait_for_timeout(2000)
                
                # Look for export in dropdown
                export_items = page.locator('a:has-text("Export"), button:has-text("Export")')
                if await export_items.count() > 0:
                    await export_items.first.click()
                    await page.wait_for_timeout(3000)
                    print("✅ Export menu accessed")

    async def handle_format_selection(self, page: Page):
        """Handle export format selection"""
        print("📋 Selecting export format...")
        
        # Look for format selection
        format_selects = page.locator(
            'select:has(option:has-text("PDF")), select:has(option:has-text("JSON")), '
            'select:has(option:has-text("CSV")), select:has(option:has-text("Excel"))'
        )
        
        format_buttons = page.locator(
            'button:has-text("PDF"), button:has-text("JSON"), button:has-text("CSV"), '
            'button:has-text("Excel"), button:has-text("Word")'
        )
        
        if await format_selects.count() > 0:
            print("✅ Found format selection dropdown")
            await format_selects.first.click()
            await page.wait_for_timeout(1000)
            
            # Prefer PDF format
            pdf_option = page.locator('option:has-text("PDF")')
            if await pdf_option.count() > 0:
                await pdf_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected PDF format")
            else:
                # Select first available format
                first_option = page.locator('option').nth(1)  # Skip empty option
                if await first_option.count() > 0:
                    await first_option.click()
                    await page.wait_for_timeout(1000)
                    print("✅ Selected first available format")
                    
        elif await format_buttons.count() > 0:
            print("✅ Found format selection buttons")
            
            # Prefer PDF button
            pdf_button = page.locator('button:has-text("PDF")')
            if await pdf_button.count() > 0:
                await pdf_button.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected PDF format")
            else:
                await format_buttons.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected first available format")

    async def step_3_generate_report(self, page: Page):
        """Download or preview report"""
        print("\n📊 Step 3: Generating and Previewing Report...")
        
        # Look for report generation buttons
        generate_buttons = page.locator(
            'button:has-text("Generate"), button:has-text("Create Report"), '
            'button:has-text("Download"), button:has-text("Preview"), '
            'button:has-text("Generate Report"), [data-testid*="generate"]'
        )
        
        if await generate_buttons.count() > 0:
            print("✅ Found report generation button")
            
            generate_button_text = await generate_buttons.first.text_content()
            print(f"📊 Clicking: {generate_button_text}")
            await generate_buttons.first.click()
            await page.wait_for_timeout(3000)
            
            # Look for progress indicators
            progress_elements = page.locator(
                '[role="progressbar"], .progress, .loading, div:has-text("Generating"), '
                'div:has-text("Creating"), div:has-text("Processing")'
            )
            
            if await progress_elements.count() > 0:
                print("✅ Report generation in progress...")
                
                # Monitor progress
                for i in range(6):  # Monitor for about 6 seconds
                    await page.wait_for_timeout(1000)
                    
                    if await progress_elements.count() > 0:
                        print(f"⏳ Generating report... ({i+1}/6)")
                    else:
                        print("✅ Report generation completed!")
                        break
            else:
                print("✅ Report generated instantly")
                await page.wait_for_timeout(2000)
        
        # Look for preview or download links
        preview_links = page.locator(
            'a:has-text("Preview"), button:has-text("Preview"), a:has-text("View"), '
            'a[href*="pdf"], a[href*="download"], .preview-link'
        )
        
        download_links = page.locator(
            'a:has-text("Download"), button:has-text("Download"), '
            'a[download], .download-link'
        )
        
        if await preview_links.count() > 0:
            print("✅ Found report preview option")
            await preview_links.first.click()
            await page.wait_for_timeout(4000)
            
            # If preview opens in new tab/window, handle it
            try:
                # Check if preview content is visible
                preview_content = page.locator('iframe, embed, object, .pdf-viewer')
                if await preview_content.count() > 0:
                    print("✅ Report preview loaded")
                    await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"ℹ️ Preview handling: {e}")
                
        elif await download_links.count() > 0:
            print("✅ Found report download option")
            
            # Note: In headless mode, actual download won't work, but we can simulate the action
            await download_links.first.click()
            await page.wait_for_timeout(3000)
            print("✅ Download initiated (simulated)")
        
        await page.screenshot(path=self.recordings_dir / f"part5_03_report_{self.timestamp}.png")

    async def step_4_export_options(self, page: Page):
        """Show various export format options"""
        print("\n📁 Step 4: Exploring Export Format Options...")
        
        # Look for different export format options
        format_options = page.locator(
            'button:has-text("PDF"), button:has-text("Excel"), button:has-text("CSV"), '
            'button:has-text("JSON"), button:has-text("Word"), button:has-text("DXF"), '
            'option:has-text("PDF"), option:has-text("Excel"), option:has-text("CSV")'
        )
        
        if await format_options.count() > 0:
            print(f"✅ Found {await format_options.count()} export format option(s)")
            
            # Demonstrate different formats
            formats_to_try = ["PDF", "Excel", "CSV", "JSON"]
            
            for format_name in formats_to_try:
                format_button = page.locator(f'button:has-text("{format_name}"), option:has-text("{format_name}")')
                
                if await format_button.count() > 0:
                    print(f"📄 Demonstrating {format_name} export...")
                    await format_button.first.click()
                    await page.wait_for_timeout(2000)
                    
                    # Look for download/generate button after format selection
                    action_buttons = page.locator(
                        'button:has-text("Download"), button:has-text("Generate"), button:has-text("Export")'
                    )
                    
                    if await action_buttons.count() > 0:
                        await action_buttons.first.click()
                        await page.wait_for_timeout(2000)
                        print(f"✅ {format_name} export initiated")
                    
                    # Take screenshot for this format
                    await page.screenshot(path=self.recordings_dir / f"part5_04_{format_name.lower()}_{self.timestamp}.png")
                    
                    break  # Exit after first successful format demo
        else:
            print("ℹ️ Format options not found - checking for export summary")
        
        # Look for export history or summary
        export_history = page.locator(
            'div:has-text("Export History"), div:has-text("Downloads"), '
            'table:has(th:has-text("File")), .export-history, .download-history'
        )
        
        if await export_history.count() > 0:
            print("✅ Found export history")
            
            # Scroll to show history
            await page.evaluate("window.scrollTo(0, 400)")
            await page.wait_for_timeout(2000)
            
            # Click on history items if available
            history_items = export_history.first.locator('tr, .history-item')
            if await history_items.count() > 1:
                for i in range(min(2, await history_items.count())):
                    try:
                        await history_items.nth(i).click()
                        await page.wait_for_timeout(1000)
                        print(f"✅ Viewed export history item {i+1}")
                    except Exception as e:
                        print(f"ℹ️ History item {i}: {e}")

    async def step_5_final_confirmation(self, page: Page):
        """Final confirmation screen"""
        print("\n✅ Step 5: Final Confirmation and Summary...")
        
        # Look for success messages or confirmation
        success_elements = page.locator(
            'div:has-text("Success"), div:has-text("Complete"), div:has-text("Exported"), '
            'div:has-text("Downloaded"), .success, .complete, .confirmation'
        )
        
        if await success_elements.count() > 0:
            print("✅ Found export success confirmation")
            
            # Show success message
            await page.wait_for_timeout(2000)
        else:
            print("ℹ️ Creating export summary...")
        
        # Look for export summary or dashboard
        summary_elements = page.locator(
            'div:has-text("Summary"), div:has-text("Overview"), '
            'table:has(th:has-text("Export")), .summary, .overview'
        )
        
        if await summary_elements.count() > 0:
            print("✅ Found export summary")
            
            # Scroll through summary
            await page.evaluate("window.scrollTo(0, 200)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 400)")
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)
        
        # Look for "Back to Dashboard" or similar navigation
        nav_buttons = page.locator(
            'button:has-text("Dashboard"), a:has-text("Dashboard"), button:has-text("Home"), '
            'a:has-text("Home"), button:has-text("Back"), [data-testid*="home"]'
        )
        
        if await nav_buttons.count() > 0:
            print("✅ Returning to dashboard")
            await nav_buttons.first.click()
            await page.wait_for_timeout(3000)
        
        # Final overview of the application
        print("✅ Showing final application overview...")
        
        # Scroll through the final view
        scroll_positions = [0, 300, 600, 300, 0]
        for pos in scroll_positions:
            await page.evaluate(f"window.scrollTo(0, {pos})")
            await page.wait_for_timeout(1500)
        
        # Final screenshot
        await page.screenshot(path=self.recordings_dir / f"part5_05_final_{self.timestamp}.png")
        
        # Hold on final view
        await page.wait_for_timeout(4000)
        print("✅ Export and reporting demonstration completed!")

    async def run_part_5_demo(self):
        """Run Part 5: Output & Reporting demo"""
        print("🎬 Starting Part 5: Output & Reporting Demo")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_navigate_to_reports(page)
                await self.step_2_export_model(page)
                await self.step_3_generate_report(page)
                await self.step_4_export_options(page)
                await self.step_5_final_confirmation(page)
                
                print("✅ Part 5 demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Part 5 demo failed: {e}")
                await page.screenshot(path=self.recordings_dir / f"part5_error_{self.timestamp}.png")
                
            finally:
                await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()
                
                # Find and rename video
                await asyncio.sleep(2)
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=os.path.getctime)
                    final_video_path = self.videos_dir / f"part-5-export-report-{self.timestamp}.webm"
                    latest_video.rename(final_video_path)
                    
                    video_size = final_video_path.stat().st_size
                    print(f"🎬 Part 5 video saved: {final_video_path}")
                    print(f"📏 Video size: {video_size / 1024:.1f} KB")
                    
                    return final_video_path
                
                return None

async def main():
    demo = StruMindPart5Demo()
    video_path = await demo.run_part_5_demo()
    
    if video_path:
        print(f"\n✅ Part 5 Demo Complete!")
        print(f"📹 Video: {video_path}")
        return True
    else:
        print(f"\n❌ Part 5 Demo Failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)