#!/usr/bin/env python3
"""
Debug login script to test authentication and inspect console/network errors.
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
        
        # Track network requests
        def on_response(response):
            if response.status >= 400:
                failed_requests.append({
                    "url": response.url,
                    "status": response.status,
                    "method": response.request.method,
                    "headers": dict(response.headers)
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
            await asyncio.sleep(3)
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
        
        # Try to inspect token/claims from localStorage or cookies
        print("\n" + "="*60)
        print("CHECKING FOR TOKEN/CLAIMS DATA")
        print("="*60)
        
        # Check localStorage
        local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
        print(f"localStorage: {local_storage}")
        
        # Check sessionStorage
        session_storage = await page.evaluate("() => JSON.stringify(sessionStorage)")
        print(f"sessionStorage: {session_storage}")
        
        # Check cookies
        cookies = await context.cookies()
        print(f"\nCookies ({len(cookies)}):")
        for cookie in cookies:
            print(f"  - {cookie['name']}: {cookie['value'][:50]}..." if len(cookie['value']) > 50 else f"  - {cookie['name']}: {cookie['value']}")
            # Look for JWT tokens
            if 'tenant_id' in cookie['value'].lower():
                print(f"    [!] Found 'tenant_id' in cookie: {cookie['name']}")
        
        # Try to decode any JWT-like tokens
        token_check = await page.evaluate("""() => {
            const tokens = [];
            // Check localStorage
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                const value = localStorage.getItem(key);
                if (value && value.includes('.')) {
                    const parts = value.split('.');
                    if (parts.length === 3) {
                        try {
                            const payload = atob(parts[1]);
                            tokens.push({source: 'localStorage', key, payload: JSON.parse(payload)});
                        } catch (e) {}
                    }
                }
            }
            // Check sessionStorage
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                const value = sessionStorage.getItem(key);
                if (value && value.includes('.')) {
                    const parts = value.split('.');
                    if (parts.length === 3) {
                        try {
                            const payload = atob(parts[1]);
                            tokens.push({source: 'sessionStorage', key, payload: JSON.parse(payload)});
                        } catch (e) {}
                    }
                }
            }
            return tokens;
        }""")
        
        if token_check:
            print(f"\n[!] Found {len(token_check)} JWT token(s):")
            for token in token_check:
                print(f"\n  Source: {token['source']}, Key: {token['key']}")
                payload = token['payload']
                print(f"  Payload: {json.dumps(payload, indent=4)}")
                if 'tenant_id' in payload:
                    print(f"  [✓] tenant_id found: {payload['tenant_id']}")
        
        print("\n" + "="*60)
        print("CONSOLE ERRORS")
        print("="*60)
        error_messages = [msg for msg in console_messages if msg['type'] == 'error']
        if error_messages:
            for i, msg in enumerate(error_messages, 1):
                print(f"{i}. [{msg['type'].upper()}] {msg['text']}")
                if msg['location']:
                    print(f"   Location: {msg['location']}")
        else:
            print("No console errors detected.")
        
        print("\n" + "="*60)
        print("FAILED NETWORK REQUESTS (status >= 400)")
        print("="*60)
        if failed_requests:
            for i, req in enumerate(failed_requests[:10], 1):  # Top 10
                print(f"\n{i}. {req['method']} {req['url']}")
                print(f"   Status: {req['status']}")
                
                # Try to get response body
                try:
                    # Find matching response
                    for resp in page.context.pages[0].responses:
                        if resp.url == req['url']:
                            try:
                                body = await resp.text()
                                print(f"   Response: {body[:200]}...")
                                if 'tenant_id' in body.lower():
                                    print(f"   [!] 'tenant_id' found in response")
                            except:
                                pass
                            break
                except:
                    pass
        else:
            print("No failed requests detected.")
        
        # Final summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"1. Login successful: {'YES' if '/app' in page.url and f'realms/{REALM}' not in page.url else 'NO'}")
        print(f"2. Console errors: {len(error_messages)}")
        print(f"3. Failed requests: {len(failed_requests)}")
        print(f"4. tenant_id in token: {'YES' if any('tenant_id' in str(t.get('payload', {})) for t in token_check) else 'NO' if token_check else 'N/A - No tokens found'}")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
