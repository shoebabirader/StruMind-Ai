#!/usr/bin/env python3
"""
StruMind Platform - Part 1: User Onboarding Demo
Records user signup, verification, and login process
"""

import asyncio
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

class StruMindPart1Demo:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:12001"
        self.recordings_dir = Path("./recordings")
        self.videos_dir = Path("./videos")
        self.recordings_dir.mkdir(exist_ok=True)
        self.videos_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # New user for demo
        self.demo_user = {
            "email": "demo@strumind.com",
            "username": "demo",
            "first_name": "Demo",
            "last_name": "User",
            "password": "DemoPassword123!",
            "company": "Demo Engineering"
        }

    async def setup_browser(self, playwright):
        """Setup browser with video recording"""
        print("🎬 Setting up browser for Part 1: User Onboarding...")
        
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

    async def step_2_login_process(self, page: Page):
        """Login with demo user"""
        print("\n🔐 Step 2: User Login Process...")
        
        # Look for login button
        login_buttons = page.locator(
            'button:has-text("Sign In"), a:has-text("Sign In"), button:has-text("Login"), '
            'a:has-text("Login"), [data-testid="login"]'
        )
        
        if await login_buttons.count() > 0:
            print("✅ Found Sign Up button")
            await signup_buttons.first.click()
            await page.wait_for_timeout(3000)
            
            # Fill signup form
            await self.fill_signup_form(page)
        else:
            print("ℹ️ No signup button found - looking for registration form")
            # Check if already on signup page
            signup_forms = page.locator('form:has(input[type="email"]):has(input[type="password"])')
            if await signup_forms.count() > 0:
                await self.fill_signup_form(page)
        
        await page.screenshot(path=self.recordings_dir / f"part1_02_signup_{self.timestamp}.png")

    async def fill_signup_form(self, page: Page):
        """Fill out the signup form"""
        print("✅ Filling signup form...")
        
        # Email field
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
        if await email_input.count() > 0:
            await email_input.first.fill(self.demo_user["email"])
            await page.wait_for_timeout(1000)
            print(f"✅ Entered email: {self.demo_user['email']}")
        
        # Username field
        username_input = page.locator('input[name="username"], input[placeholder*="username" i]')
        if await username_input.count() > 0:
            await username_input.first.fill(self.demo_user["username"])
            await page.wait_for_timeout(1000)
            print(f"✅ Entered username: {self.demo_user['username']}")
        
        # First name
        fname_input = page.locator('input[name="first_name"], input[name="firstName"], input[placeholder*="first" i]')
        if await fname_input.count() > 0:
            await fname_input.first.fill(self.demo_user["first_name"])
            await page.wait_for_timeout(1000)
        
        # Last name
        lname_input = page.locator('input[name="last_name"], input[name="lastName"], input[placeholder*="last" i]')
        if await lname_input.count() > 0:
            await lname_input.first.fill(self.demo_user["last_name"])
            await page.wait_for_timeout(1000)
        
        # Password
        password_input = page.locator('input[type="password"], input[name="password"]')
        if await password_input.count() > 0:
            await password_input.first.fill(self.demo_user["password"])
            await page.wait_for_timeout(1000)
            print("✅ Entered password")
        
        # Confirm password
        confirm_password = page.locator('input[name="confirm_password"], input[name="confirmPassword"]')
        if await confirm_password.count() > 0:
            await confirm_password.first.fill(self.demo_user["password"])
            await page.wait_for_timeout(1000)
        
        # Submit form
        submit_button = page.locator(
            'button[type="submit"], button:has-text("Sign Up"), button:has-text("Register"), button:has-text("Create Account")'
        )
        if await submit_button.count() > 0:
            await submit_button.first.click()
            await page.wait_for_timeout(4000)
            print("✅ Signup form submitted")

    async def step_3_email_verification(self, page: Page):
        """Handle email/OTP verification if applicable"""
        print("\n📧 Step 3: Email/OTP Verification...")
        
        # Look for verification elements
        verification_elements = page.locator(
            'input[placeholder*="code" i], input[placeholder*="otp" i], input[placeholder*="verification" i], '
            'text="verification", text="verify", text="code"'
        )
        
        if await verification_elements.count() > 0:
            print("✅ Found verification step")
            
            # If there's a verification code input
            code_input = page.locator('input[placeholder*="code" i], input[placeholder*="otp" i]')
            if await code_input.count() > 0:
                # Simulate entering verification code
                await code_input.first.fill("123456")
                await page.wait_for_timeout(1000)
                
                # Submit verification
                verify_button = page.locator('button:has-text("Verify"), button:has-text("Confirm")')
                if await verify_button.count() > 0:
                    await verify_button.first.click()
                    await page.wait_for_timeout(3000)
                    print("✅ Verification code submitted")
        else:
            print("ℹ️ No verification step found - proceeding to login")
        
        await page.screenshot(path=self.recordings_dir / f"part1_03_verification_{self.timestamp}.png")

    async def step_4_login_process(self, page: Page):
        """Login with new credentials"""
        print("\n🔐 Step 4: Login Process...")
        
        # Check if already logged in
        dashboard_elements = page.locator('text="dashboard", text="welcome", text="projects"')
        if await dashboard_elements.count() > 0:
            print("✅ Already logged in - skipping login step")
            return
        
        # Look for login form or button
        login_buttons = page.locator('button:has-text("Sign In"), a:has-text("Sign In"), button:has-text("Login")')
        
        if await login_buttons.count() > 0:
            await login_buttons.first.click()
            await page.wait_for_timeout(3000)
        
        # Fill login form
        email_input = page.locator('input[type="email"], input[name="email"]')
        password_input = page.locator('input[type="password"], input[name="password"]')
        
        if await email_input.count() > 0 and await password_input.count() > 0:
            print("✅ Filling login credentials")
            await email_input.first.fill(self.demo_user["email"])
            await page.wait_for_timeout(1000)
            await password_input.first.fill(self.demo_user["password"])
            await page.wait_for_timeout(1000)
            
            # Submit login
            login_submit = page.locator('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
            if await login_submit.count() > 0:
                await login_submit.first.click()
                await page.wait_for_timeout(4000)
                print("✅ Login submitted")
        
        await page.screenshot(path=self.recordings_dir / f"part1_04_login_{self.timestamp}.png")

    async def step_5_dashboard_view(self, page: Page):
        """View dashboard or project home"""
        print("\n🏠 Step 5: Dashboard/Project Home...")
        
        # Wait for dashboard to load
        await page.wait_for_timeout(3000)
        
        # Look for dashboard elements
        dashboard_elements = page.locator(
            '[class*="dashboard"], [class*="home"], [class*="welcome"], '
            'h1:has-text("Dashboard"), h1:has-text("Welcome"), h1:has-text("Projects")'
        )
        
        if await dashboard_elements.count() > 0:
            print("✅ Dashboard loaded successfully")
        else:
            print("ℹ️ Dashboard elements not found - showing current page")
        
        # Explore dashboard features
        await page.evaluate("window.scrollTo(0, 300)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 600)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)
        
        # Look for project-related elements
        project_elements = page.locator(
            'button:has-text("New Project"), button:has-text("Create"), a:has-text("Projects")'
        )
        
        if await project_elements.count() > 0:
            print(f"✅ Found {await project_elements.count()} project-related elements")
            # Hover over project elements to show they're interactive
            for i in range(min(2, await project_elements.count())):
                try:
                    await project_elements.nth(i).hover()
                    await page.wait_for_timeout(1000)
                except:
                    pass
        
        await page.screenshot(path=self.recordings_dir / f"part1_05_dashboard_{self.timestamp}.png")
        
        # Final pause to show completed onboarding
        await page.wait_for_timeout(3000)
        print("✅ User onboarding completed successfully!")

    async def run_part_1_demo(self):
        """Run Part 1: User Onboarding demo"""
        print("🎬 Starting Part 1: User Onboarding Demo")
        
        async with async_playwright() as playwright:
            browser, context, page = await self.setup_browser(playwright)
            
            try:
                await self.step_1_launch_app(page)
                await self.step_2_login_process(page)
                await self.step_3_email_verification(page)
                await self.step_4_login_process(page)
                await self.step_5_dashboard_view(page)
                
                print("✅ Part 1 demo completed successfully!")
                
            except Exception as e:
                print(f"❌ Part 1 demo failed: {e}")
                await page.screenshot(path=self.recordings_dir / f"part1_error_{self.timestamp}.png")
                
            finally:
                await page.wait_for_timeout(2000)
                await context.close()
                await browser.close()
                
                # Find and rename video
                await asyncio.sleep(2)
                video_files = list(self.recordings_dir.glob("*.webm"))
                if video_files:
                    latest_video = max(video_files, key=os.path.getctime)
                    final_video_path = self.videos_dir / f"part-1-signup-login-{self.timestamp}.webm"
                    latest_video.rename(final_video_path)
                    
                    video_size = final_video_path.stat().st_size
                    print(f"🎬 Part 1 video saved: {final_video_path}")
                    print(f"📏 Video size: {video_size / 1024:.1f} KB")
                    
                    return final_video_path
                
                return None

async def main():
    demo = StruMindPart1Demo()
    video_path = await demo.run_part_1_demo()
    
    if video_path:
        print(f"\n✅ Part 1 Demo Complete!")
        print(f"📹 Video: {video_path}")
        return True
    else:
        print(f"\n❌ Part 1 Demo Failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)