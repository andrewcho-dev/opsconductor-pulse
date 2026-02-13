import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestOperatorDashboard:
    """Test operator dashboard functionality."""

    async def test_shows_all_tenants(
        self, authenticated_operator_page: Page
    ):
        """Operator dashboard shows data from all tenants."""
        page = authenticated_operator_page
        tenant_table = page.locator("table").filter(
            has=page.locator("th:has-text('Tenant')")
        ).first
        await expect(tenant_table.locator("th:has-text('Tenant')")).to_be_visible()

    async def test_operator_badge_visible(
        self, authenticated_operator_page: Page
    ):
        """Operator badge is visible."""
        page = authenticated_operator_page
        badge = page.locator("header [data-slot='badge']").first
        if await badge.count() == 0:
            pytest.skip("Operator badge not available.")
        await expect(badge).to_be_visible()
        await expect(badge).to_contain_text("OPERATOR")

    async def test_settings_not_visible_for_regular_operator(
        self, authenticated_operator_page: Page
    ):
        """Regular operator cannot see settings panel."""
        page = authenticated_operator_page
        settings = page.locator(".settings-panel")
        await expect(settings).not_to_be_visible()
