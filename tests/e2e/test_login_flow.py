import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

KEYCLOAK_URL = "http://localhost:8180"


class TestLoginFlow:
    """Test OAuth login flow."""

    async def test_unauthenticated_redirects_to_login(self, page: Page):
        """Unauthenticated user redirected to Keycloak."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**", timeout=10000)
        assert "realms/pulse" in page.url

    async def test_customer_login_flow(self, page: Page):
        """Customer can login and reach dashboard."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")
        await page.fill("#username", "customer1")
        await page.fill("#password", "test123")
        await page.click("#kc-login")
        await page.wait_for_url("**/customer/dashboard", timeout=10000)
        assert "/customer/dashboard" in page.url
        tenant_badge = page.locator(".tenant-badge")
        await expect(tenant_badge).to_be_visible()
        await expect(tenant_badge).to_contain_text("tenant-a")

    async def test_operator_login_flow(self, page: Page):
        """Operator can login and reach operator dashboard."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")
        await page.fill("#username", "operator1")
        await page.fill("#password", "test123")
        await page.click("#kc-login")
        await page.wait_for_url("**/operator/dashboard", timeout=10000)
        assert "/operator/dashboard" in page.url
        operator_badge = page.locator(".operator-badge")
        await expect(operator_badge).to_be_visible()

    async def test_invalid_login_shows_error(self, page: Page):
        """Invalid credentials show error."""
        await page.goto("/")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**")
        await page.fill("#username", "customer1")
        await page.fill("#password", "wrongpassword")
        await page.click("#kc-login")
        error = page.locator("#input-error")
        await expect(error).to_be_visible()

    async def test_logout_flow(self, authenticated_customer_page: Page):
        """User can logout."""
        page = authenticated_customer_page
        await page.click("text=Logout")
        await page.wait_for_url("**/", timeout=10000)
        await page.goto("/customer/dashboard")
        await page.wait_for_url(f"{KEYCLOAK_URL}/**", timeout=10000)
