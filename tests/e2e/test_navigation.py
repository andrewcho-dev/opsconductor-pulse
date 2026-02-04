import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


NAV_LINKS = [
    ("Dashboard", "/customer/dashboard"),
    ("Devices", "/customer/devices"),
    ("Alerts", "/customer/alerts"),
    ("Webhooks", "/customer/webhooks"),
    ("SNMP", "/customer/snmp-integrations"),
    ("Email", "/customer/email-integrations"),
]


class TestCustomerNavLinks:
    """Verify every customer nav link navigates to a working HTML page."""

    async def test_dashboard_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('Dashboard')")
        await page.wait_for_url("**/customer/dashboard")
        # Dashboard has a stats section, not a "Dashboard" heading
        stats = page.locator(".stats")
        await expect(stats).to_be_visible()

    async def test_devices_link_returns_html(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('Devices')")
        await page.wait_for_url("**/customer/devices")
        heading = page.locator("h2:has-text('Devices')")
        await expect(heading).to_be_visible()
        # Must be HTML, not raw JSON
        nav = page.locator(".nav")
        await expect(nav).to_be_visible()

    async def test_alerts_link_returns_html(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('Alerts')")
        await page.wait_for_url("**/customer/alerts")
        heading = page.locator("h2:has-text('Alerts')")
        await expect(heading).to_be_visible()
        nav = page.locator(".nav")
        await expect(nav).to_be_visible()

    async def test_webhooks_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('Webhooks')")
        await page.wait_for_url("**/customer/webhooks")
        heading = page.locator("h2:has-text('Webhook')")
        await expect(heading).to_be_visible()

    async def test_snmp_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('SNMP')")
        await page.wait_for_url("**/customer/snmp-integrations")
        heading = page.locator("h2:has-text('SNMP')")
        await expect(heading).to_be_visible()

    async def test_email_link_works(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.click("a.nav-link:has-text('Email')")
        await page.wait_for_url("**/customer/email-integrations")
        heading = page.locator("h2:has-text('Email')")
        await expect(heading).to_be_visible()


class TestNavBarPresence:
    """Verify the nav bar appears on every customer page with all 6 links."""

    async def _assert_nav_present(self, page: Page):
        nav = page.locator(".nav")
        await expect(nav).to_be_visible()
        links = nav.locator("a.nav-link")
        assert await links.count() == 6

    async def test_dashboard_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await self._assert_nav_present(page)

    async def test_devices_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/devices")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_alerts_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/alerts")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_webhooks_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_snmp_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_email_page_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/email-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await self._assert_nav_present(page)

    async def test_device_detail_has_nav(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        # Navigate to a device detail via dashboard table
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        await self._assert_nav_present(page)


class TestActiveNavLink:
    """Verify the active class is applied to the correct nav link."""

    async def test_dashboard_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        active_link = page.locator("a.nav-link.active")
        await expect(active_link).to_have_text("Dashboard")

    async def test_devices_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/devices")
        await page.wait_for_load_state("domcontentloaded")
        active_link = page.locator("a.nav-link.active")
        await expect(active_link).to_have_text("Devices")

    async def test_alerts_nav_active(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/alerts")
        await page.wait_for_load_state("domcontentloaded")
        active_link = page.locator("a.nav-link.active")
        await expect(active_link).to_have_text("Alerts")


class TestPageContent:
    """Verify page content renders correctly."""

    async def test_devices_page_shows_table(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/devices")
        await page.wait_for_load_state("domcontentloaded")
        table = page.locator("table").filter(
            has=page.locator("th:has-text('Device ID')")
        ).first
        await expect(table).to_be_visible()
        # Seeded data should produce at least one row
        rows = table.locator("tbody tr")
        assert await rows.count() >= 1

    async def test_alerts_page_shows_table(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/alerts")
        await page.wait_for_load_state("domcontentloaded")
        table = page.locator("table")
        await expect(table).to_be_visible()

    async def test_device_detail_shows_device_info(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        # Get device ID from dashboard table
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        device_id = await device_link.inner_text()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        content = await page.content()
        assert device_id in content


class TestCrossPageNavigation:
    """Verify navigation flows across multiple pages."""

    async def test_navigate_dashboard_to_devices_to_detail(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        # Dashboard → Devices page
        await page.click("a.nav-link:has-text('Devices')")
        await page.wait_for_url("**/customer/devices")
        heading = page.locator("h2:has-text('Devices')")
        await expect(heading).to_be_visible()
        # Devices → Device detail
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        breadcrumb = page.locator(".breadcrumb")
        await expect(breadcrumb).to_be_visible()

    async def test_navigate_back_button(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        # Go to devices page
        await page.goto("/customer/devices")
        await page.wait_for_load_state("domcontentloaded")
        devices_url = page.url
        # Click into device detail
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/customer/devices/**")
        # Go back
        await page.go_back()
        await page.wait_for_url("**/customer/devices")
        assert page.url == devices_url


class TestOperatorNav:
    """Verify operator dashboard navigation and multi-tenant view."""

    async def test_operator_dashboard_has_nav(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        # Operator dashboard has a header with operator badge
        header = page.locator(".header")
        await expect(header).to_be_visible()
        badge = page.locator(".operator-badge")
        await expect(badge).to_be_visible()
        await expect(badge).to_contain_text("OPERATOR")
        # Has logout button
        logout = page.locator("a.logout-btn")
        await expect(logout).to_be_visible()

    async def test_operator_can_see_all_tenants(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        # Operator dashboard has a Devices table with Tenant column
        devices_table = page.locator("table").filter(
            has=page.locator("th:has-text('Tenant')")
        ).first
        await expect(devices_table).to_be_visible()
        # Should show devices from multiple tenants (seeded: tenant-a, tenant-b)
        table_text = await devices_table.inner_text()
        assert "tenant-a" in table_text
        assert "tenant-b" in table_text
