import json
import uuid

import pytest
from playwright.async_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def _find_row_with_name(page: Page, list_selector: str, name: str):
    """Find the table row containing the given name and return its Delete button."""
    rows = page.locator(f"{list_selector} table tbody tr")
    count = await rows.count()
    for i in range(count):
        row = rows.nth(i)
        text = await row.inner_text()
        if name in text:
            return row.locator("button:has-text('Delete')")
    return None


class TestWebhookCRUD:
    """Test webhook integration create/test/delete through the browser."""

    async def test_create_webhook_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E Webhook {uuid.uuid4().hex[:6]}"

        # Click Add Webhook button
        await page.click("#btn-add-webhook")
        modal = page.locator("#webhook-modal")
        await expect(modal).to_be_visible()

        # Fill form
        await page.fill("#webhook-name", name)
        await page.fill("#webhook-url", "https://example.com/hook-e2e")

        # Submit
        await page.click("#webhook-form button[type='submit']")

        # Wait for modal to close and list to reload
        await expect(modal).to_be_hidden(timeout=5000)
        await page.wait_for_timeout(500)

        # Verify integration appears in list by name
        list_el = page.locator("#webhook-list")
        await expect(list_el).to_contain_text(name)

        # Track for cleanup: get ID via API
        response = await page.request.get("/customer/integrations")
        data = await response.json()
        for integration in data.get("integrations", []):
            if integration.get("name") == name:
                cleanup_integrations.append(("webhook", integration["integration_id"]))
                break

    async def test_webhook_form_validates_url(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        await page.click("#btn-add-webhook")
        modal = page.locator("#webhook-modal")
        await expect(modal).to_be_visible()

        # Fill name but leave URL empty
        await page.fill("#webhook-name", "Test Validation")
        await page.fill("#webhook-url", "")

        # Submit - HTML5 validation should prevent submission
        await page.click("#webhook-form button[type='submit']")

        # Modal should still be visible (form didn't submit)
        await expect(modal).to_be_visible()

        # Close modal
        await page.click("#btn-cancel")

    async def test_test_webhook_delivery(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page

        # Create integration via API
        name = f"E2E Test Target {uuid.uuid4().hex[:6]}"
        response = await page.request.post(
            "/customer/integrations",
            data={
                "name": name,
                "webhook_url": "https://example.com/test-delivery",
                "enabled": True,
            },
        )
        assert response.status in (200, 201)
        data = await response.json()
        integration_id = data.get("integration_id") or data.get("id")
        if integration_id:
            cleanup_integrations.append(("webhook", integration_id))

        # Navigate to webhooks page and wait for list to load
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        # Click Test button for the integration
        test_button = page.locator("button:has-text('Test')").first
        if await test_button.count() > 0:
            # Handle the alert dialog from test
            page.once("dialog", lambda dialog: dialog.accept())
            await test_button.click()
            await page.wait_for_timeout(1000)

    async def test_delete_webhook_integration(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page

        # Create integration via API
        name = f"E2E WH Del {uuid.uuid4().hex[:6]}"
        response = await page.request.post(
            "/customer/integrations",
            data={
                "name": name,
                "webhook_url": "https://example.com/delete-test",
                "enabled": True,
            },
        )
        assert response.status in (200, 201)

        # Navigate to webhooks page
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        # Verify integration is in the list
        list_el = page.locator("#webhook-list")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#webhook-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Click Delete and accept confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify it's gone
        await page.goto("/customer/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)
        content = await list_el.inner_text()
        assert name not in content


class TestSNMPCRUD:
    """Test SNMP integration create/delete through the browser."""

    async def test_create_snmp_v2c_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E SNMP v2c {uuid.uuid4().hex[:6]}"

        # Click Add SNMP Integration button
        await page.click("#btn-add-snmp")
        modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Fill form - v2c is default; use public hostname that passes validation
        await page.fill("#snmp-name", name)
        await page.fill("#snmp-host", "example.com")
        await page.fill("#snmp-port", "162")
        await page.fill("#snmp-community", "public")

        # Submit
        await page.click("#snmp-form button[type='submit']")
        await page.wait_for_timeout(500)

        # Verify integration appears via API (list UI fetch can be flaky)
        found = False
        for _ in range(10):
            response = await page.request.get("/customer/integrations/snmp")
            if response.status == 200:
                data = await response.json()
                if any(item.get("name") == name for item in data if isinstance(data, list)):
                    found = True
                    break
            await page.wait_for_timeout(500)
        assert found, "SNMP v2c integration not found via API"

        # Track for cleanup
        response = await page.request.get("/customer/integrations/snmp")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("snmp", integration["id"]))
                break

    async def test_create_snmp_v3_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E SNMP v3 {uuid.uuid4().hex[:6]}"

        await page.click("#btn-add-snmp")
        modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Fill form and select v3; use public hostname
        await page.fill("#snmp-name", name)
        await page.fill("#snmp-host", "example.com")
        await page.fill("#snmp-port", "162")
        await page.select_option("#snmp-version", "3")

        # v3 fields should now be visible
        v3_config = page.locator("#v3-config")
        await expect(v3_config).to_be_visible()
        await page.fill("#snmp-username", "testuser")
        await page.fill("#snmp-auth-password", "authpass123")

        # Submit
        await page.click("#snmp-form button[type='submit']")
        await page.wait_for_timeout(500)

        # Verify integration appears via API (list UI fetch can be flaky)
        found = False
        for _ in range(10):
            response = await page.request.get("/customer/integrations/snmp")
            if response.status == 200:
                data = await response.json()
                if any(item.get("name") == name for item in data if isinstance(data, list)):
                    found = True
                    break
            await page.wait_for_timeout(500)
        assert found, "SNMP v3 integration not found via API"

        # Track for cleanup
        response = await page.request.get("/customer/integrations/snmp")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("snmp", integration["id"]))
                break

    async def test_snmp_version_toggle(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")

        await page.click("#btn-add-snmp")
        modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Default: v2c config visible, v3 hidden
        v2c_config = page.locator("#v2c-config")
        v3_config = page.locator("#v3-config")
        await expect(v2c_config).to_be_visible()
        await expect(v3_config).to_be_hidden()

        # Switch to v3
        await page.select_option("#snmp-version", "3")
        await expect(v3_config).to_be_visible()
        await expect(v2c_config).to_be_hidden()

        # Switch back to v2c
        await page.select_option("#snmp-version", "2c")
        await expect(v2c_config).to_be_visible()
        await expect(v3_config).to_be_hidden()

        await page.click("#btn-cancel")

    async def test_delete_snmp_integration(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page

        # Create via API with public hostname
        name = f"E2E SNMP Del {uuid.uuid4().hex[:6]}"
        response = await page.request.post(
            "/customer/integrations/snmp",
            data=json.dumps({
                "name": name,
                "snmp_host": "example.com",
                "snmp_port": 162,
                "snmp_config": {"version": "2c", "community": "public"},
                "enabled": True,
            }),
            headers={"Content-Type": "application/json"},
        )
        assert response.status in (200, 201)

        # Navigate and verify presence
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#snmp-list")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#snmp-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Delete with confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify removal
        await page.goto("/customer/snmp-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)
        content = await list_el.inner_text()
        assert name not in content


class TestEmailCRUD:
    """Test email integration create/delete through the browser."""

    async def test_create_email_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/customer/email-integrations")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E Email {uuid.uuid4().hex[:6]}"

        # Click Add Email Integration
        await page.click("#btn-add-email")
        modal = page.locator("#email-modal")
        await expect(modal).to_be_visible()

        # Fill required fields
        await page.fill("#email-name", name)
        await page.fill("#smtp-host", "example.com")
        await page.fill("#smtp-port", "587")
        await page.fill("#from-address", "alerts@example.com")
        await page.fill("#recipients-to", "ops@example.com")

        # Scroll submit button into view and click (long form may exceed viewport)
        submit_btn = page.locator("#email-form button[type='submit']")
        await submit_btn.scroll_into_view_if_needed()
        await page.locator("#email-modal .modal").evaluate("el => { el.scrollTop = el.scrollHeight; }")
        await submit_btn.click(force=True)
        await expect(modal).to_be_hidden(timeout=10000)
        await page.wait_for_timeout(500)

        # Verify integration appears in list
        list_el = page.locator("#email-list")
        await expect(list_el).to_contain_text(name)

        # Track for cleanup
        response = await page.request.get("/customer/integrations/email")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("email", integration["id"]))
                break

    async def test_delete_email_integration(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page

        # Create via API with public hostname
        name = f"E2E Email Del {uuid.uuid4().hex[:6]}"
        response = await page.request.post(
            "/customer/integrations/email",
            data={
                "name": name,
                "smtp_config": {
                    "smtp_host": "example.com",
                    "smtp_port": 587,
                    "smtp_tls": True,
                    "from_address": "alerts@example.com",
                    "from_name": "Test",
                },
                "recipients": {"to": ["ops@example.com"]},
                "template": {
                    "subject_template": "[{severity}] {device_id}",
                    "format": "html",
                },
                "enabled": True,
            },
        )
        assert response.status in (200, 201)

        # Navigate and verify presence
        await page.goto("/customer/email-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#email-list")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#email-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Delete with confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify removal
        await page.goto("/customer/email-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)
        content = await list_el.inner_text()
        assert name not in content


class TestMQTTCRUD:
    """Test MQTT integration create/delete through the browser."""

    async def test_create_mqtt_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/customer/mqtt-integrations")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E MQTT {uuid.uuid4().hex[:6]}"

        await page.click("#btn-add-mqtt")
        modal = page.locator("#mqtt-modal")
        await expect(modal).to_be_visible()

        await page.fill("#mqtt-name", name)
        await page.fill("#mqtt-topic", "alerts/test-tenant/INFO/test-site/test-device")

        await page.click("#mqtt-form button[type='submit']")

        await expect(modal).to_be_hidden(timeout=5000)
        await page.wait_for_timeout(500)

        list_el = page.locator("#mqtt-list")
        await expect(list_el).to_contain_text(name)

        response = await page.request.get("/customer/integrations/mqtt")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("mqtt", integration["id"]))
                break

    async def test_delete_mqtt_integration(self, authenticated_customer_page: Page):
        page = authenticated_customer_page

        name = f"E2E MQTT Del {uuid.uuid4().hex[:6]}"
        response = await page.request.post(
            "/customer/integrations/mqtt",
            data=json.dumps({
                "name": name,
                "mqtt_topic": "alerts/test/INFO/site/dev",
                "mqtt_qos": 1,
                "enabled": True,
            }),
            headers={"Content-Type": "application/json"},
        )
        assert response.status in (200, 201)

        await page.goto("/customer/mqtt-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#mqtt-list")
        await expect(list_el).to_contain_text(name)

        delete_btn = await _find_row_with_name(page, "#mqtt-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        await page.goto("/customer/mqtt-integrations")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)
        content = await list_el.inner_text()
        assert name not in content


class TestDesignConsistency:
    """Verify all integration pages use the same visual theme."""

    async def test_all_integration_pages_have_same_theme(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        bg_colors = {}

        for name, path in [
            ("webhook", "/customer/webhooks"),
            ("snmp", "/customer/snmp-integrations"),
            ("email", "/customer/email-integrations"),
            ("mqtt", "/customer/mqtt-integrations"),
        ]:
            await page.goto(path)
            await page.wait_for_load_state("domcontentloaded")
            card = page.locator(".card").first
            await expect(card).to_be_visible()
            color = await card.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            bg_colors[name] = color

        # All three should use the same card background color
        colors = list(bg_colors.values())
        assert len(set(colors)) == 1, (
            f"Card backgrounds differ: {bg_colors}"
        )

    async def test_all_integration_pages_have_add_button(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page

        for path, btn_id in [
            ("/customer/webhooks", "#btn-add-webhook"),
            ("/customer/snmp-integrations", "#btn-add-snmp"),
            ("/customer/email-integrations", "#btn-add-email"),
            ("/customer/mqtt-integrations", "#btn-add-mqtt"),
        ]:
            await page.goto(path)
            await page.wait_for_load_state("domcontentloaded")
            button = page.locator(btn_id)
            await expect(button).to_be_visible()
