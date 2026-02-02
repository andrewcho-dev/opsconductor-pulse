import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestCustomerDashboard:
    """Test customer dashboard functionality."""

    async def test_dashboard_shows_device_stats(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows device statistics."""
        page = authenticated_customer_page
        stats = page.locator(".stats")
        await expect(stats).to_be_visible()
        await expect(page.locator("text=Total Devices")).to_be_visible()
        await expect(page.locator("text=Online")).to_be_visible()
        await expect(page.locator("text=Stale")).to_be_visible()

    async def test_dashboard_shows_devices_table(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows devices table."""
        page = authenticated_customer_page
        table = page.locator("table").first
        await expect(table).to_be_visible()
        await expect(page.locator("th:has-text('Device ID')")).to_be_visible()
        await expect(page.locator("th:has-text('Status')")).to_be_visible()

    async def test_device_link_navigates_to_detail(
        self, authenticated_customer_page: Page
    ):
        """Clicking device navigates to detail page."""
        page = authenticated_customer_page
        device_link = page.locator("table tbody tr td a").first
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        assert device_id in page.url

    async def test_shows_only_tenant_data(
        self, authenticated_customer_page: Page
    ):
        """Dashboard only shows current tenant's data."""
        page = authenticated_customer_page
        tenant_badge = page.locator(".tenant-badge")
        await expect(tenant_badge).to_contain_text("tenant-a")
        device_rows = page.locator("table tbody tr")
        count = await device_rows.count()
        for i in range(count):
            row = device_rows.nth(i)
            row_text = await row.inner_text()
            assert "tenant-b" not in row_text


class TestCustomerDeviceDetail:
    """Test device detail page."""

    async def test_device_detail_loads(
        self, authenticated_customer_page: Page
    ):
        """Device detail page loads correctly."""
        page = authenticated_customer_page
        device_link = page.locator("table tbody tr td a").first
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        await expect(page.locator("h1, h2")).to_be_visible()

    async def test_cannot_access_other_tenant_device(
        self, authenticated_customer_page: Page
    ):
        """Cannot access device from another tenant."""
        page = authenticated_customer_page
        await page.goto("/customer/devices/test-device-b1")
        content = await page.content()
        assert "404" in content or "not found" in content.lower()
