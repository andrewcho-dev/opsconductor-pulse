import os

import pytest
from playwright.async_api import async_playwright, Browser, BrowserContext

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8080")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser: Browser):
    """Create browser context with fresh state."""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=BASE_URL,
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context: BrowserContext):
    """Create page."""
    page = await context.new_page()
    yield page
    await page.close()


@pytest.fixture
async def authenticated_customer_page(context: BrowserContext):
    """Create page with customer1 logged in."""
    page = await context.new_page()
    await page.goto("/")
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")
    await page.fill("#username", "customer1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")
    await page.wait_for_url(f"{BASE_URL}/customer/dashboard")
    yield page
    await page.close()


@pytest.fixture
async def authenticated_operator_page(context: BrowserContext):
    """Create page with operator1 logged in."""
    page = await context.new_page()
    await page.goto("/")
    await page.wait_for_url(f"{KEYCLOAK_URL}/**")
    await page.fill("#username", "operator1")
    await page.fill("#password", "test123")
    await page.click("#kc-login")
    await page.wait_for_url(f"{BASE_URL}/operator/dashboard")
    yield page
    await page.close()
