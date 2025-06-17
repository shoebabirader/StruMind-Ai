#!/usr/bin/env python3
"""
StruMind Workflow Demo - Part 1: User Login
Records the login process with the demo user account.
"""

import asyncio
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

class Part1LoginDemo:
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
        print("🎬 Setting up browser for Part 1: User Login...")
        
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

    async def step_1_launch_app(self, page: Page):
        """Launch the StruMind application"""
        print("\n🚀 Step 1: Launching StruMind Application...")
        
        await page.goto(self.frontend_url)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
        # Show landing page
        await page.screenshot(path=self.recordings_dir / f"part1_01_launch_{self.timestamp}.png")
        
        title = await page.title()
        print(f"✅ Application launched: {title}")
        
        # Scroll to show features
        await page.evaluate("window.scrollTo(0, 400)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)

    async def step_2_navigate_to_login(self, page: Page):
        """Navigate to login page"""
        print("\n🔐 Step 2: Navigating to Login...")
        
        # Look for login button
        login_buttons = page.locator(
            'button:has-text("Sign In"), a:has-text("Sign In"), button:has-text("Login"), '
            'a:has-text("Login"), [data-testid="login"]'
        )
        
        if await login_buttons.count() > 0:
            print("✅ Found Login button")
            await login_buttons.first.click()
            await page.wait_for_timeout(3000)
        else:
            # Try navigating directly to login page
            print("ℹ️ No login button found - navigating directly to /auth/login")
            await page.goto(f"{self.frontend_url}/auth/login")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)

        await page.screenshot(path=self.recordings_dir / f"part1_02_login_page_{self.timestamp}.png")

    async def step_3_login_process(self, page: Page):
        """Login with demo user"""
        print("\n📝 Step 3: Login Process...")
        
        # Fill login form
        email_input = page.locator('input[type="email"], input[name="email"]')
        password_input = page.locator('input[type="password"], input[name="password"]')

        if await email_input.count() > 0 and await password_input.count() > 0:
            print("✅ Filling login credentials")
            await email_input.first.fill(self.demo_user["email"])
            await page.wait_for_timeout(1000)
            await password_input.first.fill(self.demo_user["password"])
            await page.wait_for_timeout(1000)

            await page.screenshot(path=self.recordings_dir / f"part1_03_form_filled_{self.timestamp}.png")

            # Submit login
            login_submit = page.locator('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
            if await login_submit.count() > 0:
                print("✅ Submitting login form")
                await login_submit.first.click()
                await page.wait_for_timeout(5000)
                
                # Wait for redirect to dashboard
                await page.wait_for_url("**/dashboard", timeout=10000)
                print("✅ Successfully logged in and redirected to dashboard")
            else:
                print("❌ No submit button found")
        else:
            print("❌ Login form not found")

        await page.screenshot(path=self.recordings_dir / f"part1_04_login_result_{self.timestamp}.png")

    async def step_4_dashboard_view(self, page: Page):
        """Show the dashboard after login"""
        print("\n📊 Step 4: Dashboard Overview...")
        
        # Wait for dashboard to load
        await page.wait_for_timeout(3000)
        
        # Take screenshot of dashboard
        await page.screenshot(path=self.recordings_dir / f"part1_05_dashboard_{self.timestamp}.png")
        
        # Show different sections of dashboard
        dashboard_sections = [
            "Projects", "Analytics", "Team", "Settings"
        ]
        
        for section in dashboard_sections:
            section_element = page.locator(f'text="{section}"').first
            if await section_element.count() > 0:
                await section_element.scroll_into_view_if_needed()
                await page.wait_for_timeout(1000)
        
        print("✅ Dashboard tour completed")

    async def run_demo(self):
        """Run the complete Part 1 demo"""
        print("🎬 Starting Part 1: User Login Demo")
        print(f"📁 Recordings will be saved to: {self.recordings_dir}")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_launch_app(page)
                await self.step_2_navigate_to_login(page)
                await self.step_3_login_process(page)
                await self.step_4_dashboard_view(page)
                
                print("\n✅ Part 1 Demo completed successfully!")
                
            except Exception as e:
                print(f"\n❌ Error during demo: {e}")
                await page.screenshot(path=self.recordings_dir / f"part1_error_{self.timestamp}.png")
                
            finally:
                # Save video
                await context.close()
                await browser.close()
                
                # Rename video file
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=lambda x: x.stat().st_mtime)
                    new_video_name = self.recordings_dir / f"part1_login_demo_{self.timestamp}.webm"
                    latest_video.rename(new_video_name)
                    print(f"📹 Video saved as: {new_video_name}")

if __name__ == "__main__":
    demo = Part1LoginDemo()
    asyncio.run(demo.run_demo())