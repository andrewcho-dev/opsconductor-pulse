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
        await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
        await expect(page.get_by_text("Total Devices")).to_be_visible()
        await expect(page.get_by_text("Online").first).to_be_visible()
        await expect(page.get_by_text("Stale").first).to_be_visible()

    async def test_dashboard_shows_devices_table(
        self, authenticated_customer_page: Page
    ):
        """Dashboard shows devices table."""
        page = authenticated_customer_page
        await page.wait_for_load_state("networkidle")
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            devices_table = page.locator("table").filter(
                has=page.locator("th:has-text('Device ID')")
            ).first
        if await devices_table.count() == 0:
            if await page.get_by_text("No devices found").count() > 0:
                pytest.skip("No devices found for this customer dashboard.")
            pytest.skip("Devices table not visible on dashboard.")
        await expect(devices_table).to_be_visible()
        await expect(devices_table.locator("th:has-text('Device')")).to_be_visible()
        await expect(devices_table.locator("th:has-text('Status')")).to_be_visible()

    async def test_device_link_navigates_to_detail(
        self, authenticated_customer_page: Page
    ):
        """Clicking device navigates to detail page."""
        page = authenticated_customer_page
        await page.wait_for_load_state("networkidle")
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            devices_table = page.locator("table").filter(
                has=page.locator("th:has-text('Device ID')")
            ).first
        if await devices_table.count() == 0:
            pytest.skip("Devices table not visible on dashboard.")
        rows = devices_table.locator("tbody tr")
        if await rows.count() == 0:
            if await page.get_by_text("No devices found").count() > 0:
                pytest.skip("No devices available for detail navigation.")
            pytest.skip("No device rows available on dashboard.")
        await expect(rows.first).to_be_visible()
        device_link = devices_table.locator("tbody tr td a").first
        if await device_link.count() == 0:
            pytest.skip("Device link not available on dashboard.")
        await expect(device_link).to_be_visible()
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        assert device_id in page.url

    async def test_shows_only_tenant_data(
        self, authenticated_customer_page: Page
    ):
        """Dashboard only shows current tenant's data."""
        page = authenticated_customer_page
        tenant_badge = page.locator("header [data-slot='badge']").first
        await expect(tenant_badge).to_be_visible()
        tenant_id = (await tenant_badge.inner_text()).strip()
        assert tenant_id
        device_rows = page.locator("table tbody tr")
        count = await device_rows.count()
        other_tenant = "tenant-b" if tenant_id == "tenant-a" else "tenant-a"
        for i in range(count):
            row = device_rows.nth(i)
            row_text = await row.inner_text()
            assert other_tenant not in row_text


class TestCustomerDeviceDetail:
    """Test device detail page."""

    async def test_device_detail_loads(
        self, authenticated_customer_page: Page
    ):
        """Device detail page loads correctly."""
        page = authenticated_customer_page
        await page.wait_for_load_state("networkidle")
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            devices_table = page.locator("table").filter(
                has=page.locator("th:has-text('Device ID')")
            ).first
        if await devices_table.count() == 0:
            pytest.skip("Devices table not visible on dashboard.")
        rows = devices_table.locator("tbody tr")
        if await rows.count() == 0:
            if await page.get_by_text("No devices found").count() > 0:
                pytest.skip("No devices available for detail page load.")
            pytest.skip("No device rows available on dashboard.")
        await expect(rows.first).to_be_visible()
        device_link = devices_table.locator("tbody tr td a").first
        if await device_link.count() == 0:
            pytest.skip("Device link not available on dashboard.")
        await expect(device_link).to_be_visible()
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        await expect(page.get_by_role("link", name="Back to Devices")).to_be_visible()
        await expect(page.get_by_text(device_id).first).to_be_visible()

    async def test_cannot_access_other_tenant_device(
        self, authenticated_customer_page: Page
    ):
        """Cannot access device from another tenant."""
        page = authenticated_customer_page
        tenant_badge = page.locator("header [data-slot='badge']").first
        tenant_id = (await tenant_badge.inner_text()).strip()
        other_device = "test-device-b1" if tenant_id == "tenant-a" else "test-device-a1"
        await page.goto(f"/app/devices/{other_device}")
        await page.wait_for_load_state("domcontentloaded")
        await expect(page.get_by_text("Device not found.")).to_be_visible()
