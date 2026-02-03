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
        await expect(stats.locator("text=Total Devices")).to_be_visible()
        await expect(stats.locator("text=Online").first).to_be_visible()
        await expect(stats.locator("text=Stale").first).to_be_visible()

    async def test_dashboard_shows_devices_table(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows devices table."""
        page = authenticated_customer_page
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        await expect(devices_table).to_be_visible()
        await expect(devices_table.locator("th:has-text('Device ID')")).to_be_visible()
        await expect(devices_table.locator("th:has-text('Status')")).to_be_visible()

    async def test_device_link_navigates_to_detail(
        self, authenticated_customer_page: Page
    ):
        """Clicking device navigates to detail page."""
        page = authenticated_customer_page
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        await expect(devices_table.locator("tbody tr").first).to_be_visible()
        device_link = devices_table.locator("tbody tr td a").first
        await expect(device_link).to_be_visible()
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
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        await expect(devices_table.locator("tbody tr").first).to_be_visible()
        device_link = devices_table.locator("tbody tr td a").first
        await expect(device_link).to_be_visible()
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        breadcrumb = page.locator(".breadcrumb")
        await expect(breadcrumb).to_be_visible()
        await expect(breadcrumb).to_contain_text(device_id)

    async def test_cannot_access_other_tenant_device(
        self, authenticated_customer_page: Page
    ):
        """Cannot access device from another tenant."""
        page = authenticated_customer_page
        await page.goto("/customer/devices/test-device-b1")
        content = await page.content()
        assert "404" in content or "not found" in content.lower()
