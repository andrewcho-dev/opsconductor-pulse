import os

import httpx
import pytest
from playwright.async_api import expect

UI_BASE_URL = os.environ.get("UI_BASE_URL", "http://localhost:8000")
HEALTHZ_URLS = {
    "ui_iot": f"{UI_BASE_URL}/healthz",
}

pytestmark = [pytest.mark.e2e, pytest.mark.smoke, pytest.mark.asyncio]


async def test_ui_iot_healthz():
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(HEALTHZ_URLS["ui_iot"])
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "degraded")


async def test_unauthenticated_api_returns_401():
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{UI_BASE_URL}/customer/devices")
    assert resp.status_code == 401


async def test_dashboard_loads(customer_page):
    await customer_page.goto("/app/dashboard")
    await customer_page.wait_for_load_state("networkidle")
    await expect(customer_page.get_by_role("heading", name="Dashboard")).to_be_visible()


async def test_devices_page_loads(customer_page):
    await customer_page.goto("/app/devices")
    await customer_page.wait_for_load_state("networkidle")
    await expect(customer_page.get_by_role("heading", name="Devices")).to_be_visible()


async def test_alerts_page_loads(customer_page):
    await customer_page.goto("/app/alerts")
    await customer_page.wait_for_load_state("networkidle")
    await expect(customer_page.get_by_role("heading", name="Alerts")).to_be_visible()


async def test_sites_page_loads(customer_page):
    await customer_page.goto("/app/sites")
    await customer_page.wait_for_load_state("networkidle")
    await expect(customer_page.get_by_role("heading", name="Sites")).to_be_visible()


async def test_integrations_page_loads(customer_page):
    await customer_page.goto("/app/integrations/webhooks")
    await customer_page.wait_for_load_state("networkidle")
    assert await customer_page.locator("h1, h2, main").first.is_visible()


async def test_delivery_log_page_loads(customer_page):
    await customer_page.goto("/app/delivery-log")
    await customer_page.wait_for_load_state("networkidle")
    await expect(customer_page.get_by_role("heading", name="Delivery Log")).to_be_visible()


async def test_operator_dashboard_loads(operator_page):
    await operator_page.goto("/app/operator")
    await operator_page.wait_for_load_state("networkidle")
    assert await operator_page.locator("h1, h2").first.is_visible()


@pytest.mark.xfail(reason="alert rule create route not implemented; form opens via modal on /app/alert-rules")
async def test_alert_rule_create_form_loads(customer_page):
    await customer_page.goto("/app/alert-rules/new")
    await customer_page.wait_for_load_state("networkidle")
    assert await customer_page.locator("input, select, form").first.is_visible()
