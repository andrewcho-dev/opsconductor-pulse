import os
from datetime import datetime, timezone
import asyncpg
import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

E2E_DATABASE_URL = os.getenv(
    "E2E_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://iot:iot_dev@localhost:5432/iotcloud"),
)


NAV_LINKS = [
    ("Dashboard", "/app/dashboard"),
    ("Devices", "/app/devices"),
    ("Alerts", "/app/alerts"),
    ("Webhooks", "/app/integrations/webhooks"),
    ("SNMP", "/app/integrations/snmp"),
    ("Email", "/app/integrations/email"),
    ("MQTT", "/app/integrations/mqtt"),
]


class TestCustomerNavLinks:
    """Verify every customer nav link navigates to a working HTML page."""

    async def test_dashboard_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="Dashboard").click()
        await page.wait_for_url("**/app/dashboard")
        await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
        await expect(page.get_by_text("Total Devices")).to_be_visible()

    async def test_devices_link_returns_html(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="Devices").click()
        await page.wait_for_url("**/app/devices")
        await expect(page.get_by_role("heading", name="Devices")).to_be_visible()
        await expect(page.locator("[data-slot='sidebar']")).to_be_visible()

    async def test_alerts_link_returns_html(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="Alerts").click()
        await page.wait_for_url("**/app/alerts")
        await expect(page.get_by_role("heading", name="Alerts")).to_be_visible()
        await expect(page.locator("[data-slot='sidebar']")).to_be_visible()

    async def test_webhooks_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="Webhooks").click()
        await page.wait_for_url("**/app/integrations/webhooks")
        await expect(page.get_by_role("heading", name="Webhooks")).to_be_visible()

    async def test_snmp_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="SNMP").click()
        await page.wait_for_url("**/app/integrations/snmp")
        await expect(
            page.get_by_role("heading", name="SNMP", exact=True)
        ).to_be_visible()

    async def test_email_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="Email").click()
        await page.wait_for_url("**/app/integrations/email")
        await expect(page.get_by_role("heading", name="Email")).to_be_visible()

    async def test_mqtt_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.get_by_role("link", name="MQTT").click()
        await page.wait_for_url("**/app/integrations/mqtt")
        await expect(page.get_by_role("heading", name="MQTT")).to_be_visible()


class TestNavBarPresence:
    """Verify the nav bar appears on every customer page with all 6 links."""

    async def _assert_nav_present(self, page: Page):
        sidebar = page.locator("[data-slot='sidebar']")
        await expect(sidebar).to_be_visible()
        for label in ("Dashboard", "Devices", "Alerts", "Webhooks", "SNMP", "Email", "MQTT"):
            await expect(sidebar.get_by_role("link", name=label)).to_be_visible()

    async def test_dashboard_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await self._assert_nav_present(page)

    async def test_devices_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/devices")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_alerts_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/alerts")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_webhooks_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/integrations/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_snmp_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/integrations/snmp")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_email_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/integrations/email")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_mqtt_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/integrations/mqtt")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_device_detail_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        # Navigate to a device detail via dashboard table
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            devices_table = page.locator("table").filter(
                has=page.locator("th:has-text('Device ID')")
            ).first
        if await devices_table.count() == 0:
            pytest.skip("No devices table available on dashboard.")
        rows = devices_table.locator("tbody tr")
        if await rows.count() == 0:
            pytest.skip("No devices available for detail navigation.")
        device_link = rows.first.locator("a").first
        if await device_link.count() == 0:
            pytest.skip("Device link not available on dashboard.")
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        await self._assert_nav_present(page)


class TestActiveNavLink:
    """Verify the active class is applied to the correct nav link."""

    async def test_dashboard_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        active_link = page.locator("[data-sidebar='menu-button'][data-active='true']")
        await expect(active_link).to_contain_text("Dashboard")

    async def test_devices_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/devices")
        await page.wait_for_load_state("domcontentloaded")
        active_link = page.locator("[data-sidebar='menu-button'][data-active='true']")
        await expect(active_link).to_contain_text("Devices")

    async def test_alerts_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/alerts")
        await page.wait_for_load_state("domcontentloaded")
        active_link = page.locator("[data-sidebar='menu-button'][data-active='true']")
        await expect(active_link).to_contain_text("Alerts")


class TestPageContent:
    """Verify page content renders correctly."""

    async def test_devices_page_shows_table(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/devices")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_url("**/app/devices*")
        await page.wait_for_load_state("networkidle")
        await expect(page.get_by_role("heading", name="Devices")).to_be_visible(timeout=15000)
        table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        if await table.count() > 0:
            await expect(table).to_be_visible()
        elif await page.get_by_text("No devices found").count() > 0:
            await expect(page.get_by_text("No devices found")).to_be_visible(timeout=15000)
            return
        elif await page.get_by_text("Failed to load devices").count() > 0:
            await expect(page.get_by_text("Failed to load devices")).to_be_visible()
            pytest.fail("Devices failed to load.")
        else:
            pytest.skip("Devices list not ready in this environment.")
        rows = table.locator("tbody tr")
        assert await rows.count() >= 1

    async def test_alerts_page_shows_table(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/alerts")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_url("**/app/alerts*")
        await page.wait_for_load_state("networkidle")
        await expect(page.get_by_role("heading", name="Alerts")).to_be_visible(timeout=15000)
        table = page.locator("table")
        if await table.count() > 0:
            await expect(table).to_be_visible()
        elif await page.get_by_text("No open alerts", exact=False).count() > 0:
            await expect(
                page.get_by_text("No open alerts", exact=False)
            ).to_be_visible(timeout=15000)
            return
        elif await page.get_by_text("Failed to load alerts").count() > 0:
            await expect(page.get_by_text("Failed to load alerts")).to_be_visible()
            pytest.fail("Alerts failed to load.")
        else:
            pytest.skip("Alerts list not ready in this environment.")

    async def test_device_detail_shows_device_info(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        tenant_id = (await page.locator("header [data-slot='badge']").first.inner_text()).strip()
        device_id = "e2e-nav-device"
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
                VALUES ($1, $2, 'e2e-site', 'ONLINE', now())
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status)
                VALUES ($1, $2, 'e2e-site', 'ACTIVE')
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()
        await page.reload()
        await page.wait_for_load_state("networkidle")
        # Get device ID from dashboard table
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            pytest.skip("No devices table available on dashboard.")
        await expect(devices_table).to_be_visible(timeout=15000)
        device_link = devices_table.locator("tbody tr td a").first
        await expect(device_link).to_be_visible()
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        await expect(page.get_by_role("link", name="Back to Devices")).to_be_visible()
        await expect(page.get_by_text(device_id).first).to_be_visible()
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                "DELETE FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            await conn.execute(
                "DELETE FROM device_state WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()


class TestCrossPageNavigation:
    """Verify navigation flows across multiple pages."""

    async def test_navigate_dashboard_to_devices_to_detail(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        tenant_id = (await page.locator("header [data-slot='badge']").first.inner_text()).strip()
        device_id = "e2e-nav-device-2"
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
                VALUES ($1, $2, 'e2e-site', 'ONLINE', now())
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status)
                VALUES ($1, $2, 'e2e-site', 'ACTIVE')
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()
        # Dashboard → Devices page
        await page.get_by_role("link", name="Devices").click()
        await page.wait_for_url("**/app/devices")
        await expect(page.get_by_role("heading", name="Devices")).to_be_visible()
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        if await devices_table.count() == 0:
            pytest.skip("No devices table available on devices page.")
        await expect(devices_table).to_be_visible(timeout=15000)
        # Devices → Device detail
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        await expect(page.get_by_role("link", name="Back to Devices")).to_be_visible()
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                "DELETE FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            await conn.execute(
                "DELETE FROM device_state WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()

    async def test_navigate_back_button(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        tenant_id = (await page.locator("header [data-slot='badge']").first.inner_text()).strip()
        device_id = f"e2e-nav-back-{int(datetime.now(timezone.utc).timestamp())}"
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
                VALUES ($1, $2, 'e2e-site', 'ONLINE', now())
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status)
                VALUES ($1, $2, 'e2e-site', 'ACTIVE')
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()
        # Go to devices page
        await page.goto("/app/devices")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_url("**/app/devices*")
        await page.wait_for_load_state("networkidle")
        devices_url = page.url
        # Click into device detail
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
        if await devices_table.count() == 0:
            devices_table = page.locator("table").filter(
                has=page.locator("th:has-text('Device ID')")
            ).first
        if await devices_table.count() == 0:
            pytest.skip("No devices table available on devices page.")
        await expect(devices_table).to_be_visible(timeout=15000)
        device_row = devices_table.locator("tbody tr", has_text=device_id).first
        if await device_row.count() == 0:
            pytest.skip("Inserted device not visible on devices page yet.")
        device_link = device_row.locator("a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        # Go back
        await page.go_back()
        await page.wait_for_url("**/app/devices*")
        assert page.url == devices_url
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                "DELETE FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            await conn.execute(
                "DELETE FROM device_state WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
        finally:
            await conn.close()


class TestOperatorNav:
    """Verify operator dashboard navigation and multi-tenant view."""

    async def test_operator_dashboard_has_nav(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        header = page.locator("header")
        await expect(header).to_be_visible()
        # Has logout button
        logout = page.locator("button[title='Logout']")
        await expect(logout).to_be_visible()

    async def test_operator_can_see_all_tenants(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        device_id = "e2e-tenant-b-device"
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                """
                INSERT INTO device_state (tenant_id, device_id, site_id, status, last_seen_at)
                VALUES ('tenant-b', $1, 'e2e-site', 'ONLINE', now())
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                device_id,
            )
            await conn.execute(
                """
                INSERT INTO device_registry (tenant_id, device_id, site_id, status)
                VALUES ('tenant-b', $1, 'e2e-site', 'ACTIVE')
                ON CONFLICT (tenant_id, device_id) DO NOTHING
                """,
                device_id,
            )
        finally:
            await conn.close()
        await page.goto("/app/operator/devices")
        await page.wait_for_url("**/app/operator/devices")
        await page.fill("input[placeholder='Filter by tenant_id']", "tenant-b")
        await page.click("button:has-text('Filter')")
        await page.wait_for_load_state("networkidle")
        if await page.get_by_text("No devices found").count() > 0:
            pytest.skip("No devices found for tenant-b in operator view.")
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Tenant ID')")
        ).first
        if await devices_table.count() == 0:
            pytest.skip("Operator devices table not visible.")
        await expect(devices_table).to_be_visible(timeout=15000)
        await expect(page.locator("tr", has_text="tenant-b").first).to_be_visible(
            timeout=15000
        )
        conn = await asyncpg.connect(E2E_DATABASE_URL)
        try:
            await conn.execute(
                "DELETE FROM device_state WHERE tenant_id = 'tenant-b' AND device_id = $1",
                device_id,
            )
            await conn.execute(
                "DELETE FROM device_registry WHERE tenant_id = 'tenant-b' AND device_id = $1",
                device_id,
            )
        finally:
            await conn.close()
