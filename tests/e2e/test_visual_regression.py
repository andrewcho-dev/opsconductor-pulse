"""Visual regression baselines using Playwright screenshots.

Baseline workflow:
1) First run to generate baselines:
   RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v --update-snapshots
2) Subsequent runs compare against baselines:
   RUN_E2E=1 pytest tests/e2e/test_visual_regression.py -v
3) After intentional UI changes, re-run with --update-snapshots and commit.
"""

import pytest
from playwright.async_api import Page, expect

from tests.e2e.conftest import SCREENSHOT_THRESHOLD, record_screenshot_bytes

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

SCREENSHOT_DIR = "tests/e2e/screenshots"
async def _capture_and_compare(page: Page, filename: str) -> None:
    current = await page.screenshot(
        path=f"{SCREENSHOT_DIR}/{filename}", full_page=True
    )
    record_screenshot_bytes(current)
    await expect(page).to_have_screenshot(
        filename, threshold=SCREENSHOT_THRESHOLD, full_page=True
    )


async def _wait_for_device_table(page: Page) -> None:
    table = page.locator("table").filter(
        has=page.locator("th:has-text('Device ID')")
    ).first
    if await table.count() == 0:
        table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
    await expect(table).to_be_visible()


class TestVisualRegressionCustomer:
    async def test_screenshot_customer_dashboard(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/dashboard")
        await _wait_for_device_table(page)
        await _capture_and_compare(page, "customer_dashboard.png")

    async def test_screenshot_customer_devices(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/devices")
        await _wait_for_device_table(page)
        await _capture_and_compare(page, "customer_devices.png")

    async def test_screenshot_customer_alerts(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/alerts")
        await expect(page.locator("table")).to_be_visible()
        await _capture_and_compare(page, "customer_alerts.png")

    async def test_screenshot_webhook_integrations(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/integrations/webhooks")
        await expect(page.locator("#webhook-list")).to_be_visible()
        await _capture_and_compare(page, "customer_webhooks.png")

    async def test_screenshot_snmp_integrations(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/integrations/snmp")
        await expect(page.locator("#snmp-list")).to_be_visible()
        await _capture_and_compare(page, "customer_snmp.png")

    async def test_screenshot_email_integrations(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/integrations/email")
        await expect(page.locator("#email-list")).to_be_visible()
        await _capture_and_compare(page, "customer_email.png")

    async def test_screenshot_device_detail(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/dashboard")
        await _wait_for_device_table(page)
        device_link = page.locator("table tbody tr td a").first
        await expect(device_link).to_be_visible()
        await device_link.click()
        await page.wait_for_url("**/app/devices/**")
        await expect(page.get_by_text("Back to Devices")).to_be_visible()
        await _capture_and_compare(page, "customer_device_detail.png")


class TestVisualRegressionOperator:
    async def test_screenshot_operator_dashboard(
        self, authenticated_operator_page: Page
    ):
        page = authenticated_operator_page
        await page.goto("/app/operator")
        table = page.locator("table").filter(
            has=page.locator("th:has-text('Tenant')")
        ).first
        await expect(table).to_be_visible()
        await _capture_and_compare(page, "operator_dashboard.png")


class TestIntegrationPageConsistency:
    async def test_integration_pages_same_background(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        colors = []
        for path in [
            "/app/integrations/webhooks",
            "/app/integrations/snmp",
            "/app/integrations/email",
        ]:
            await page.goto(path)
            card = page.locator("[data-slot='card'], .card").first
            await expect(card).to_be_visible()
            color = await card.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            colors.append(color)
        assert colors[0] == colors[1] == colors[2]

    async def test_integration_pages_same_font(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        fonts = []
        for path in [
            "/app/integrations/webhooks",
            "/app/integrations/snmp",
            "/app/integrations/email",
        ]:
            await page.goto(path)
            font = await page.evaluate(
                "getComputedStyle(document.body).fontFamily"
            )
            fonts.append(font)
        assert fonts[0] == fonts[1] == fonts[2]

    async def test_integration_pages_same_button_style(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        button_colors = []
        for path, selector in [
            ("/app/integrations/webhooks", "#btn-add-webhook"),
            ("/app/integrations/snmp", "#btn-add-snmp"),
            ("/app/integrations/email", "#btn-add-email"),
        ]:
            await page.goto(path)
            button = page.locator(selector)
            await expect(button).to_be_visible()
            color = await button.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            button_colors.append(color)
        assert button_colors[0] == button_colors[1] == button_colors[2]
