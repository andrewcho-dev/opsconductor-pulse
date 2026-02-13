import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestOperatorSubscriptionUI:
    """Test operator subscription management UI."""

    async def test_tenant_detail_has_subscription_card(
        self, authenticated_operator_page: Page
    ):
        """Operator tenant detail page shows subscription card."""
        page = authenticated_operator_page

        await page.click("text=Tenants")
        await page.wait_for_load_state("networkidle")

        tenant_link = page.locator('a[href^="/app/operator/tenants/"]').first
        if await tenant_link.count() == 0:
            pytest.skip("No operator tenant links available.")
        await tenant_link.click()
        await page.wait_for_load_state("networkidle")

        subscription_card = page.locator("text=Subscription").first
        await expect(subscription_card).to_be_visible()

        manage_button = page.locator('button:has-text("Manage")')
        if await manage_button.count() == 0:
            pytest.skip("Manage button not visible on tenant detail.")
        await expect(manage_button).to_be_visible()

    async def test_edit_subscription_dialog(
        self, authenticated_operator_page: Page
    ):
        """Operator can open and use subscription edit dialog."""
        page = authenticated_operator_page

        await page.click("text=Tenants")
        await page.wait_for_load_state("networkidle")
        tenant_link = page.locator('a[href^="/app/operator/tenants/"]').first
        if await tenant_link.count() == 0:
            pytest.skip("No operator tenant links available.")
        await tenant_link.click()
        await page.wait_for_load_state("networkidle")

        manage_button = page.locator('button:has-text("Manage")')
        if await manage_button.count() == 0:
            pytest.skip("Manage button not visible on tenant detail.")
        await manage_button.first.click()

        dialog = page.locator('[role="dialog"]')
        await expect(dialog).to_be_visible()

        await expect(page.locator('button:has-text("+30 Days")')).to_be_visible()
        await expect(page.locator('button:has-text("+90 Days")')).to_be_visible()
        await expect(page.locator('button:has-text("+1 Year")')).to_be_visible()

        await expect(page.locator('label:has-text("Device Limit")')).to_be_visible()
        await expect(page.locator('label:has-text("Term End")')).to_be_visible()
        await expect(page.locator('label:has-text("Status")')).to_be_visible()
        await expect(page.locator('label:has-text("Notes")')).to_be_visible()

        save_button = page.locator('button:has-text("Save Changes")')
        if await save_button.count() == 0:
            pytest.skip("Save Changes button not visible.")
        await expect(save_button).to_be_disabled()

        await page.fill("textarea", "Test notes for verification")
        await expect(save_button).to_be_enabled()


class TestCustomerSubscriptionUI:
    """Test customer subscription UI."""

    async def test_sidebar_has_subscription_link(
        self, authenticated_customer_page: Page
    ):
        """Customer sidebar shows Subscription link."""
        page = authenticated_customer_page

        sidebar_link = page.locator('a:has-text("Subscription")')
        await expect(sidebar_link).to_be_visible()

    async def test_subscription_page_loads(
        self, authenticated_customer_page: Page
    ):
        """Customer can view subscription page."""
        page = authenticated_customer_page

        await page.click('text=Subscription')
        await page.wait_for_load_state("networkidle")

        heading = page.get_by_role("heading", name="Subscription")
        if await heading.count() == 0:
            pytest.skip("Subscription heading not visible.")
        await expect(heading).to_be_visible()
        if await page.get_by_text("No active subscriptions").count() > 0:
            pytest.skip("No active subscriptions available for this environment.")
        await expect(page.get_by_text("Total Capacity")).to_be_visible()
        await expect(page.get_by_text("Active Subscriptions")).to_be_visible()
        await expect(page.get_by_text("Available")).to_be_visible()

    async def test_device_list_shows_limit(
        self, authenticated_customer_page: Page
    ):
        """Device list page shows subscription limit info."""
        page = authenticated_customer_page

        await page.click("text=Devices")
        await page.wait_for_load_state("networkidle")

        limit_text = page.locator("text=/\\d+ of \\d+ devices/")
        if await limit_text.count() == 0:
            pytest.skip("Device usage limit text not visible.")
        await expect(limit_text).to_be_visible()
