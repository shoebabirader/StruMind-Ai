#!/usr/bin/env python3
"""
Test frontend-backend login integration with browser DevTools
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

class LoginIntegrationTest:
    def __init__(self):
        self.frontend_url = "http://localhost:12001"
        self.backend_url = "http://localhost:8000"
        
    async def test_login_flow(self):
        """Test the complete login flow with network monitoring"""
        print("🔍 Testing Frontend-Backend Login Integration...")
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)  # Headless for server environment
            context = await browser.new_context()
            page = await context.new_page()
            
            # Enable console logging
            page.on("console", lambda msg: print(f"🖥️ Console: {msg.text}"))
            
            # Monitor network requests
            requests = []
            responses = []
            
            async def handle_request(request):
                requests.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data
                })
                print(f"📤 Request: {request.method} {request.url}")
            
            async def handle_response(response):
                responses.append({
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers)
                })
                print(f"📥 Response: {response.status} {response.url}")
                
                # Log response body for API calls
                if "/api/" in response.url:
                    try:
                        body = await response.text()
                        print(f"📄 Response body: {body[:200]}...")
                    except:
                        print("📄 Response body: (binary or error)")
            
            page.on("request", handle_request)
            page.on("response", handle_response)
            
            try:
                # Navigate to frontend
                print(f"🌐 Navigating to {self.frontend_url}")
                await page.goto(self.frontend_url)
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(3000)
                
                # Take screenshot of landing page
                await page.screenshot(path="test_login_1_landing.png")
                print("📸 Screenshot: Landing page")
                
                # Look for login form or button
                login_buttons = page.locator('button:has-text("Sign In"), a:has-text("Sign In"), button:has-text("Login")')
                
                if await login_buttons.count() > 0:
                    print("✅ Found login button")
                    await login_buttons.first.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path="test_login_2_form.png")
                    print("📸 Screenshot: Login form")
                else:
                    print("ℹ️ No login button found, checking for login form")
                
                # Fill login form
                email_input = page.locator('input[type="email"], input[name="email"]')
                password_input = page.locator('input[type="password"], input[name="password"]')
                
                if await email_input.count() > 0 and await password_input.count() > 0:
                    print("✅ Found login form fields")
                    
                    # Clear and fill email
                    await email_input.first.clear()
                    await email_input.first.fill("demo@strumind.com")
                    await page.wait_for_timeout(1000)
                    
                    # Clear and fill password
                    await password_input.first.clear()
                    await password_input.first.fill("DemoPassword123!")
                    await page.wait_for_timeout(1000)
                    
                    await page.screenshot(path="test_login_3_filled.png")
                    print("📸 Screenshot: Form filled")
                    
                    # Submit form
                    submit_button = page.locator('button[type="submit"], button:has-text("Sign In"), button:has-text("Login")')
                    if await submit_button.count() > 0:
                        print("🚀 Submitting login form...")
                        await submit_button.first.click()
                        
                        # Wait for response
                        await page.wait_for_timeout(5000)
                        
                        await page.screenshot(path="test_login_4_after_submit.png")
                        print("📸 Screenshot: After submit")
                        
                        # Check if we're redirected or see dashboard
                        current_url = page.url
                        print(f"🌐 Current URL after login: {current_url}")
                        
                        # Look for dashboard elements
                        dashboard_elements = page.locator(
                            'h1:has-text("Dashboard"), h1:has-text("Welcome"), div:has-text("Projects"), '
                            'button:has-text("New Project"), nav, .dashboard'
                        )
                        
                        if await dashboard_elements.count() > 0:
                            print("✅ Login successful - Dashboard elements found")
                            await page.screenshot(path="test_login_5_success.png")
                            print("📸 Screenshot: Login success")
                        else:
                            print("❌ Login may have failed - No dashboard elements found")
                            
                            # Check for error messages
                            error_elements = page.locator(
                                'div:has-text("error"), div:has-text("invalid"), div:has-text("incorrect"), '
                                '.error, .alert-error, [role="alert"]'
                            )
                            
                            if await error_elements.count() > 0:
                                error_text = await error_elements.first.text_content()
                                print(f"❌ Error message found: {error_text}")
                            else:
                                print("ℹ️ No error message found")
                    else:
                        print("❌ No submit button found")
                else:
                    print("❌ Login form fields not found")
                
                # Wait a bit more to see final state
                await page.wait_for_timeout(3000)
                await page.screenshot(path="test_login_6_final.png")
                print("📸 Screenshot: Final state")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                await page.screenshot(path="test_login_error.png")
                
            finally:
                # Save network logs
                with open("network_requests.json", "w") as f:
                    json.dump(requests, f, indent=2)
                with open("network_responses.json", "w") as f:
                    json.dump(responses, f, indent=2)
                
                print(f"📊 Captured {len(requests)} requests and {len(responses)} responses")
                
                # Print API requests
                api_requests = [r for r in requests if "/api/" in r["url"]]
                if api_requests:
                    print("🔍 API Requests made:")
                    for req in api_requests:
                        print(f"  {req['method']} {req['url']}")
                        if req['post_data']:
                            print(f"    Data: {req['post_data'][:100]}...")
                else:
                    print("⚠️ No API requests found!")
                
                await browser.close()

async def main():
    test = LoginIntegrationTest()
    await test.test_login_flow()

if __name__ == "__main__":
    asyncio.run(main())