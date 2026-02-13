#!/usr/bin/env python3
"""
Enhanced debug login script with response body capture
"""
import asyncio
import json
from playwright.async_api import async_playwright

TARGET_URL = "https://192.168.10.53/app/"
USERNAME = "acme-admin"
PASSWORD = "acme123"
REALM = "pulse"

console_messages = []
failed_requests = []


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # Track console messages
        def on_console(msg):
            console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            })
        
        # Track network responses
        async def on_response(response):
            if response.status >= 400:
                try:
                    body = await response.text()
                except:
                    body = "(unable to read response body)"
                
                failed_requests.append({
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "headers": dict(response.headers),
                    "body": body
                })
        
        page.on("console", on_console)
        page.on("response", on_response)
        
        print(f"[1] Navigating to {TARGET_URL}")
        await page.goto(TARGET_URL)
        await page.wait_for_load_state("domcontentloaded")
        
        # Wait for redirect to Keycloak
        await asyncio.sleep(2)
        current_url = page.url
        print(f"[2] Current URL: {current_url}")
        
        if f"realms/{REALM}" in current_url:
            print(f"[3] Detected Keycloak login page for realm '{REALM}'")
            
            # Fill in credentials
            await page.fill("#username", USERNAME)
            await page.fill("#password", PASSWORD)
            print(f"[4] Filled credentials: {USERNAME} / {'*' * len(PASSWORD)}")
            
            # Click login
            await page.click("#kc-login")
            print("[5] Clicked login button")
            
            # Wait for navigation
            await asyncio.sleep(5)
            await page.wait_for_load_state("domcontentloaded")
            
            current_url = page.url
            print(f"[6] Post-login URL: {current_url}")
            
            # Check if still on Keycloak (login failed)
            if f"realms/{REALM}" in current_url:
                print("[!] STILL ON KEYCLOAK - Login likely failed")
                # Check for error message
                error_locator = page.locator("#input-error, .alert-error, .kc-feedback-text")
                if await error_locator.count() > 0:
                    error_text = await error_locator.first.text_content()
                    print(f"[!] Error message: {error_text}")
            elif "/app" in current_url:
                print("[✓] LOGIN SUCCESS - Redirected to app")
            else:
                print(f"[?] UNEXPECTED URL: {current_url}")
        else:
            print(f"[!] Did not redirect to Keycloak. Current URL: {current_url}")
        
        # Wait a bit more for any async requests
        await asyncio.sleep(3)
        
        print("\n" + "="*80)
        print("TOP 5 FAILED REQUESTS WITH RESPONSE BODIES")
        print("="*80)
        
        # Show first 5 unique failed requests
        seen_urls = set()
        count = 0
        for req in failed_requests:
            if req['url'] not in seen_urls and count < 5:
                seen_urls.add(req['url'])
                count += 1
                
                print(f"\n{count}. {req['method']} {req['url']}")
                print(f"   Status: {req['status']}")
                print(f"   Response Body:")
                
                # Try to pretty-print JSON
                try:
                    body_json = json.loads(req['body'])
                    print(f"   {json.dumps(body_json, indent=6)}")
                except:
                    # Not JSON, print as-is
                    if len(req['body']) > 500:
                        print(f"   {req['body'][:500]}...")
                    else:
                        print(f"   {req['body']}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
