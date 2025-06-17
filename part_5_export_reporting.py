#!/usr/bin/env python3
"""
StruMind Workflow Demo - Part 5: Export & Reporting
Records the final export, reporting, and project completion process.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

class Part5ExportReporting:
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
        print("🎬 Setting up browser for Part 5: Export & Reporting...")
        
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

    async def step_1_navigate_to_reports(self, page: Page):
        """Navigate to reports and export section"""
        print("\n📄 Step 1: Navigating to Reports & Export...")
        
        # Login first
        await page.goto(f"{self.frontend_url}/auth/login")
        await page.wait_for_load_state('networkidle')
        await page.fill('input[type="email"]', self.demo_user["email"])
        await page.fill('input[type="password"]', self.demo_user["password"])
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_timeout(3000)
        
        # Navigate to reports section
        reports_nav = page.locator('a:has-text("Reports"), button:has-text("Reports"), [data-testid="reports"]')
        if await reports_nav.count() > 0:
            await reports_nav.first.click()
            await page.wait_for_timeout(3000)
        else:
            # Try direct navigation
            await page.goto(f"{self.frontend_url}/reports")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part5_01_reports_page_{self.timestamp}.png")
        print("✅ Navigated to reports section")

    async def step_2_generate_analysis_report(self, page: Page):
        """Generate comprehensive analysis report"""
        print("\n📊 Step 2: Generating Analysis Report...")
        
        # Select report type
        report_type_select = page.locator('select[name="reportType"], .report-type-selector')
        if await report_type_select.count() > 0:
            await report_type_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select comprehensive analysis report
            analysis_option = page.locator('option:has-text("Analysis Report"), .report-option:has-text("Analysis")')
            if await analysis_option.count() > 0:
                await analysis_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected Analysis Report")
        
        # Configure report sections
        sections_to_include = ["Executive Summary", "Model Details", "Analysis Results", "Design Verification"]
        
        for section in sections_to_include:
            section_checkbox = page.locator(f'input[value="{section}"], .report-section:has-text("{section}") input')
            if await section_checkbox.count() > 0:
                await section_checkbox.first.check()
                await page.wait_for_timeout(500)
                print(f"✅ Included {section}")
        
        await page.screenshot(path=self.recordings_dir / f"part5_02_report_config_{self.timestamp}.png")
        
        # Generate report
        generate_button = page.locator('button:has-text("Generate Report"), [data-testid="generate-report"]')
        if await generate_button.count() > 0:
            await generate_button.first.click()
            await page.wait_for_timeout(5000)
            print("✅ Analysis report generated")
        
        await page.screenshot(path=self.recordings_dir / f"part5_03_report_generated_{self.timestamp}.png")

    async def step_3_customize_report_format(self, page: Page):
        """Customize report format and branding"""
        print("\n🎨 Step 3: Customizing Report Format...")
        
        # Navigate to report customization
        customize_nav = page.locator('a:has-text("Customize"), button:has-text("Format"), [data-testid="customize-report"]')
        if await customize_nav.count() > 0:
            await customize_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Select template
        template_select = page.locator('select[name="template"], .template-selector')
        if await template_select.count() > 0:
            await template_select.first.click()
            await page.wait_for_timeout(1000)
            
            # Select professional template
            professional_option = page.locator('option:has-text("Professional"), .template-option:has-text("Professional")')
            if await professional_option.count() > 0:
                await professional_option.first.click()
                await page.wait_for_timeout(1000)
                print("✅ Selected Professional template")
        
        # Add company branding
        company_name = page.locator('input[name="companyName"], input[placeholder*="company" i]')
        if await company_name.count() > 0:
            await company_name.first.fill("Demo Engineering Corp")
            await page.wait_for_timeout(1000)
            print("✅ Added company branding")
        
        # Set report title
        report_title = page.locator('input[name="reportTitle"], input[placeholder*="title" i]')
        if await report_title.count() > 0:
            await report_title.first.fill("Structural Analysis Report - Demo Bridge Project")
            await page.wait_for_timeout(1000)
            print("✅ Set report title")
        
        await page.screenshot(path=self.recordings_dir / f"part5_04_report_customization_{self.timestamp}.png")

    async def step_4_export_formats(self, page: Page):
        """Export in multiple formats"""
        print("\n💾 Step 4: Exporting in Multiple Formats...")
        
        # Export as PDF
        pdf_export = page.locator('button:has-text("Export PDF"), [data-testid="export-pdf"]')
        if await pdf_export.count() > 0:
            await pdf_export.first.click()
            await page.wait_for_timeout(3000)
            print("✅ Exported as PDF")
        
        await page.screenshot(path=self.recordings_dir / f"part5_05_pdf_export_{self.timestamp}.png")
        
        # Export as Excel
        excel_export = page.locator('button:has-text("Export Excel"), [data-testid="export-excel"]')
        if await excel_export.count() > 0:
            await excel_export.first.click()
            await page.wait_for_timeout(3000)
            print("✅ Exported as Excel")
        
        # Export CAD files
        cad_export = page.locator('button:has-text("Export CAD"), button:has-text("DXF"), [data-testid="export-cad"]')
        if await cad_export.count() > 0:
            await cad_export.first.click()
            await page.wait_for_timeout(3000)
            print("✅ Exported CAD files")
        
        await page.screenshot(path=self.recordings_dir / f"part5_06_multiple_exports_{self.timestamp}.png")

    async def step_5_project_archive(self, page: Page):
        """Create project archive and backup"""
        print("\n📦 Step 5: Creating Project Archive...")
        
        # Navigate to project settings
        settings_nav = page.locator('a:has-text("Settings"), button:has-text("Project Settings"), [data-testid="project-settings"]')
        if await settings_nav.count() > 0:
            await settings_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Create project archive
        archive_button = page.locator('button:has-text("Create Archive"), button:has-text("Backup Project"), [data-testid="create-archive"]')
        if await archive_button.count() > 0:
            await archive_button.first.click()
            await page.wait_for_timeout(2000)
            
            # Configure archive options
            include_results = page.locator('input[name="includeResults"], .archive-option:has-text("Results") input')
            if await include_results.count() > 0:
                await include_results.first.check()
                await page.wait_for_timeout(500)
            
            include_reports = page.locator('input[name="includeReports"], .archive-option:has-text("Reports") input')
            if await include_reports.count() > 0:
                await include_reports.first.check()
                await page.wait_for_timeout(500)
            
            # Create archive
            create_archive = page.locator('button:has-text("Create"), .archive-create-button')
            if await create_archive.count() > 0:
                await create_archive.first.click()
                await page.wait_for_timeout(5000)
                print("✅ Project archive created")
        
        await page.screenshot(path=self.recordings_dir / f"part5_07_project_archive_{self.timestamp}.png")

    async def step_6_collaboration_sharing(self, page: Page):
        """Set up collaboration and sharing"""
        print("\n🤝 Step 6: Setting Up Collaboration...")
        
        # Navigate to sharing section
        sharing_nav = page.locator('a:has-text("Share"), button:has-text("Collaboration"), [data-testid="sharing"]')
        if await sharing_nav.count() > 0:
            await sharing_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Add team member
        add_member_button = page.locator('button:has-text("Add Member"), [data-testid="add-member"]')
        if await add_member_button.count() > 0:
            await add_member_button.first.click()
            await page.wait_for_timeout(2000)
            
            # Fill member details
            member_email = page.locator('input[name="memberEmail"], input[placeholder*="email" i]')
            if await member_email.count() > 0:
                await member_email.first.fill("colleague@engineering.com")
                await page.wait_for_timeout(1000)
            
            # Set permissions
            permission_select = page.locator('select[name="permissions"], .permission-selector')
            if await permission_select.count() > 0:
                await permission_select.first.select_option("View")
                await page.wait_for_timeout(1000)
            
            # Send invitation
            send_invite = page.locator('button:has-text("Send Invite"), .invite-button')
            if await send_invite.count() > 0:
                await send_invite.first.click()
                await page.wait_for_timeout(2000)
                print("✅ Team member invited")
        
        await page.screenshot(path=self.recordings_dir / f"part5_08_collaboration_{self.timestamp}.png")

    async def step_7_project_completion(self, page: Page):
        """Mark project as complete and review summary"""
        print("\n🎯 Step 7: Project Completion Summary...")
        
        # Navigate back to dashboard
        dashboard_nav = page.locator('a:has-text("Dashboard"), [data-testid="dashboard"]')
        if await dashboard_nav.count() > 0:
            await dashboard_nav.first.click()
            await page.wait_for_timeout(3000)
        
        # Show project summary
        project_card = page.locator('.project-card, .project-item').first
        if await project_card.count() > 0:
            await project_card.scroll_into_view_if_needed()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part5_09_project_summary_{self.timestamp}.png")
        
        # Show completion metrics
        metrics_section = page.locator('.completion-metrics, .project-stats, .summary-stats')
        if await metrics_section.count() > 0:
            await metrics_section.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(2000)
        
        await page.screenshot(path=self.recordings_dir / f"part5_10_completion_metrics_{self.timestamp}.png")
        print("✅ Project completion summary reviewed")

    async def run_demo(self):
        """Run the complete Part 5 demo"""
        print("🎬 Starting Part 5: Export & Reporting Demo")
        print(f"📁 Recordings will be saved to: {self.recordings_dir}")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_navigate_to_reports(page)
                await self.step_2_generate_analysis_report(page)
                await self.step_3_customize_report_format(page)
                await self.step_4_export_formats(page)
                await self.step_5_project_archive(page)
                await self.step_6_collaboration_sharing(page)
                await self.step_7_project_completion(page)
                
                print("\n✅ Part 5 Demo completed successfully!")
                print("🎉 Complete StruMind workflow demonstration finished!")
                
            except Exception as e:
                print(f"\n❌ Error during demo: {e}")
                await page.screenshot(path=self.recordings_dir / f"part5_error_{self.timestamp}.png")
                
            finally:
                # Save video
                await context.close()
                await browser.close()
                
                # Rename video file
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
                    new_video_name = self.recordings_dir / f"part5_export_reporting_{self.timestamp}.webm"
                    latest_video.rename(new_video_name)
                    print(f"📹 Video saved as: {new_video_name}")

if __name__ == "__main__":
    demo = Part5ExportReporting()
    asyncio.run(demo.run_demo())