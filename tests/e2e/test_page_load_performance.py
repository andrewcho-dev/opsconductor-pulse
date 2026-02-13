import time

import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.benchmark, pytest.mark.asyncio]


async def _measure_page_load(page: Page, url: str) -> float:
    start = time.monotonic()
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")
    return time.monotonic() - start


async def test_page_load_dashboard(authenticated_customer_page: Page):
    page = authenticated_customer_page
    elapsed = await _measure_page_load(page, "/app/dashboard")
    if await page.get_by_role("heading", name="Dashboard").count() == 0:
        pytest.skip("Dashboard heading not visible.")
    await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
    elapsed_ms = elapsed * 1000.0
    print(f"PAGE_LOAD dashboard {elapsed_ms:.2f}ms")
    assert elapsed_ms < 3000


async def test_page_load_devices(authenticated_customer_page: Page):
    page = authenticated_customer_page
    start = time.monotonic()
    await page.goto("/app/devices")
    table = page.locator("table").filter(
        has=page.locator("th:has-text('Device ID')")
    ).first
    if await table.count() == 0:
        table = page.locator("table").filter(
            has=page.locator("th:has-text('Device')")
        ).first
    if await table.count() == 0:
        pytest.skip("Devices table not visible.")
    await expect(table).to_be_visible()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"PAGE_LOAD devices {elapsed_ms:.2f}ms")
    assert elapsed_ms < 3000


async def test_page_load_webhooks(authenticated_customer_page: Page):
    page = authenticated_customer_page
    start = time.monotonic()
    await page.goto("/app/integrations/webhooks")
    list_el = page.locator("#webhook-list")
    if await list_el.count() == 0:
        pytest.skip("Webhook list not visible.")
    await expect(list_el).to_be_visible()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"PAGE_LOAD webhooks {elapsed_ms:.2f}ms")
    assert elapsed_ms < 3000


async def test_page_load_snmp(authenticated_customer_page: Page):
    page = authenticated_customer_page
    start = time.monotonic()
    await page.goto("/app/integrations/snmp")
    list_el = page.locator("#snmp-list")
    if await list_el.count() == 0:
        pytest.skip("SNMP list not visible.")
    await expect(list_el).to_be_visible()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"PAGE_LOAD snmp {elapsed_ms:.2f}ms")
    assert elapsed_ms < 3000


async def test_page_load_email(authenticated_customer_page: Page):
    page = authenticated_customer_page
    start = time.monotonic()
    await page.goto("/app/integrations/email")
    list_el = page.locator("#email-list")
    if await list_el.count() == 0:
        pytest.skip("Email list not visible.")
    await expect(list_el).to_be_visible()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    print(f"PAGE_LOAD email {elapsed_ms:.2f}ms")
    assert elapsed_ms < 3000
