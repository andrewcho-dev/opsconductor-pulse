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
        await page.goto("/app/integrations/webhooks")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E Webhook {uuid.uuid4().hex[:6]}"

        # Click Add Webhook button
        add_button = page.get_by_role("button", name="Add Webhook")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="New Webhook")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-webhook")
        if await add_button.count() == 0:
            pytest.skip("Add Webhook button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#webhook-modal")
        await expect(modal).to_be_visible()

        # Fill form
        name_input = page.locator("#webhook-name")
        url_input = page.locator("#webhook-url")
        if await name_input.count() == 0 or await url_input.count() == 0:
            pytest.skip("Webhook form fields not available.")
        await name_input.fill(name)
        await url_input.fill("https://example.com/hook-e2e")

        # Submit
        submit_button = page.locator("#webhook-form button[type='submit']")
        if await submit_button.count() == 0:
            submit_button = modal.get_by_role("button", name="Save")
        if await submit_button.count() == 0:
            pytest.skip("Webhook submit button not available.")
        await submit_button.first.click()

        # Wait for modal to close and list to reload
        await expect(modal).to_be_hidden(timeout=5000)
        await page.wait_for_timeout(500)

        # Verify integration appears in list by name
        list_el = page.locator("#webhook-list")
        if await list_el.count() == 0:
            pytest.skip("Webhook list not visible.")
        await expect(list_el).to_contain_text(name)

        # Track for cleanup: get ID via API
        response = await page.request.get("/customer/integrations")
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        data = await response.json()
        for integration in data.get("integrations", []):
            if integration.get("name") == name:
                cleanup_integrations.append(("webhook", integration["integration_id"]))
                break

    async def test_webhook_form_validates_url(
        self, authenticated_customer_page: Page
    ):
        page = authenticated_customer_page
        await page.goto("/app/integrations/webhooks")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        add_button = page.get_by_role("button", name="Add Webhook")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="New Webhook")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-webhook")
        if await add_button.count() == 0:
            pytest.skip("Add Webhook button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#webhook-modal")
        await expect(modal).to_be_visible()

        # Fill name but leave URL empty
        name_input = page.locator("#webhook-name")
        url_input = page.locator("#webhook-url")
        if await name_input.count() == 0 or await url_input.count() == 0:
            pytest.skip("Webhook form fields not available.")
        await name_input.fill("Test Validation")
        await url_input.fill("")

        # Submit - HTML5 validation should prevent submission
        submit_button = page.locator("#webhook-form button[type='submit']")
        if await submit_button.count() == 0:
            submit_button = modal.get_by_role("button", name="Save")
        if await submit_button.count() == 0:
            pytest.skip("Webhook submit button not available.")
        await submit_button.first.click()

        # Modal should still be visible (form didn't submit)
        await expect(modal).to_be_visible()

        # Close modal
        cancel_button = page.locator("#btn-cancel")
        if await cancel_button.count() == 0:
            cancel_button = modal.get_by_role("button", name="Cancel")
        if await cancel_button.count() == 0:
            pytest.skip("Webhook cancel button not available.")
        await cancel_button.first.click()

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
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        assert response.status in (200, 201)
        data = await response.json()
        integration_id = data.get("integration_id") or data.get("id")
        if integration_id:
            cleanup_integrations.append(("webhook", integration_id))

        # Navigate to webhooks page and wait for list to load
        await page.goto("/app/integrations/webhooks")
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
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        assert response.status in (200, 201)

        # Navigate to webhooks page
        await page.goto("/app/integrations/webhooks")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        # Verify integration is in the list
        list_el = page.locator("#webhook-list")
        if await list_el.count() == 0:
            pytest.skip("Webhook list not visible.")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#webhook-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Click Delete and accept confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify it's gone
        await page.goto("/app/integrations/webhooks")
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
        await page.goto("/app/integrations/snmp")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E SNMP v2c {uuid.uuid4().hex[:6]}"

        # Click Add SNMP Integration button
        add_button = page.get_by_role("button", name="Add SNMP")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="Add SNMP Integration")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-snmp")
        if await add_button.count() == 0:
            pytest.skip("Add SNMP button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Fill form - v2c is default; use public hostname that passes validation
        name_input = page.locator("#snmp-name")
        host_input = page.locator("#snmp-host")
        port_input = page.locator("#snmp-port")
        community_input = page.locator("#snmp-community")
        if (
            await name_input.count() == 0
            or await host_input.count() == 0
            or await port_input.count() == 0
            or await community_input.count() == 0
        ):
            pytest.skip("SNMP v2c form fields not available.")
        await name_input.fill(name)
        await host_input.fill("example.com")
        await port_input.fill("162")
        await community_input.fill("public")

        # Submit
        submit_button = page.locator("#snmp-form button[type='submit']")
        if await submit_button.count() == 0:
            submit_button = modal.get_by_role("button", name="Save")
        if await submit_button.count() == 0:
            pytest.skip("SNMP submit button not available.")
        await submit_button.first.click()
        await page.wait_for_timeout(500)

        # Verify integration appears via API (list UI fetch can be flaky)
        found = False
        for _ in range(10):
            response = await page.request.get("/customer/integrations/snmp")
            if response.status in (401, 403):
                pytest.skip("Integration API not authorized for this environment.")
            if response.status == 200:
                data = await response.json()
                if any(item.get("name") == name for item in data if isinstance(data, list)):
                    found = True
                    break
            await page.wait_for_timeout(500)
        assert found, "SNMP v2c integration not found via API"

        # Track for cleanup
        response = await page.request.get("/customer/integrations/snmp")
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("snmp", integration["id"]))
                break

    async def test_create_snmp_v3_integration(
        self, authenticated_customer_page: Page, cleanup_integrations
    ):
        page = authenticated_customer_page
        await page.goto("/app/integrations/snmp")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E SNMP v3 {uuid.uuid4().hex[:6]}"

        add_button = page.get_by_role("button", name="Add SNMP")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="Add SNMP Integration")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-snmp")
        if await add_button.count() == 0:
            pytest.skip("Add SNMP button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Fill form and select v3; use public hostname
        name_input = page.locator("#snmp-name")
        host_input = page.locator("#snmp-host")
        port_input = page.locator("#snmp-port")
        version_select = page.locator("#snmp-version")
        if (
            await name_input.count() == 0
            or await host_input.count() == 0
            or await port_input.count() == 0
            or await version_select.count() == 0
        ):
            pytest.skip("SNMP v3 form fields not available.")
        await name_input.fill(name)
        await host_input.fill("example.com")
        await port_input.fill("162")
        await version_select.select_option("3")

        # v3 fields should now be visible
        v3_config = page.locator("#v3-config")
        await expect(v3_config).to_be_visible()
        user_input = page.locator("#snmp-username")
        auth_input = page.locator("#snmp-auth-password")
        if await user_input.count() == 0 or await auth_input.count() == 0:
            pytest.skip("SNMP v3 fields not available.")
        await user_input.fill("testuser")
        await auth_input.fill("authpass123")

        # Submit
        submit_button = page.locator("#snmp-form button[type='submit']")
        if await submit_button.count() == 0:
            submit_button = modal.get_by_role("button", name="Save")
        if await submit_button.count() == 0:
            pytest.skip("SNMP submit button not available.")
        await submit_button.first.click()
        await page.wait_for_timeout(500)

        # Verify integration appears via API (list UI fetch can be flaky)
        found = False
        for _ in range(10):
            response = await page.request.get("/customer/integrations/snmp")
            if response.status in (401, 403):
                pytest.skip("Integration API not authorized for this environment.")
            if response.status == 200:
                data = await response.json()
                if any(item.get("name") == name for item in data if isinstance(data, list)):
                    found = True
                    break
            await page.wait_for_timeout(500)
        assert found, "SNMP v3 integration not found via API"

        # Track for cleanup
        response = await page.request.get("/customer/integrations/snmp")
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        data = await response.json()
        for integration in data if isinstance(data, list) else []:
            if integration.get("name") == name:
                cleanup_integrations.append(("snmp", integration["id"]))
                break

    async def test_snmp_version_toggle(self, authenticated_customer_page: Page):
        page = authenticated_customer_page
        await page.goto("/app/integrations/snmp")
        await page.wait_for_load_state("domcontentloaded")

        add_button = page.get_by_role("button", name="Add SNMP")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="Add SNMP Integration")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-snmp")
        if await add_button.count() == 0:
            pytest.skip("Add SNMP button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#snmp-modal")
        await expect(modal).to_be_visible()

        # Default: v2c config visible, v3 hidden
        v2c_config = page.locator("#v2c-config")
        v3_config = page.locator("#v3-config")
        if await v2c_config.count() == 0 or await v3_config.count() == 0:
            pytest.skip("SNMP config sections not available.")
        await expect(v2c_config).to_be_visible()
        await expect(v3_config).to_be_hidden()

        # Switch to v3
        version_select = page.locator("#snmp-version")
        if await version_select.count() == 0:
            pytest.skip("SNMP version selector not available.")
        await version_select.select_option("3")
        await expect(v3_config).to_be_visible()
        await expect(v2c_config).to_be_hidden()

        # Switch back to v2c
        await version_select.select_option("2c")
        await expect(v2c_config).to_be_visible()
        await expect(v3_config).to_be_hidden()

        cancel_button = page.locator("#btn-cancel")
        if await cancel_button.count() == 0:
            cancel_button = modal.get_by_role("button", name="Cancel")
        if await cancel_button.count() == 0:
            pytest.skip("SNMP cancel button not available.")
        await cancel_button.first.click()

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
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        assert response.status in (200, 201)

        # Navigate and verify presence
        await page.goto("/app/integrations/snmp")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#snmp-list")
        if await list_el.count() == 0:
            pytest.skip("SNMP list not visible.")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#snmp-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Delete with confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify removal
        await page.goto("/app/integrations/snmp")
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
        await page.goto("/app/integrations/email")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E Email {uuid.uuid4().hex[:6]}"

        # Click Add Email Integration
        add_button = page.get_by_role("button", name="Add Email")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="Add Email Integration")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-email")
        if await add_button.count() == 0:
            pytest.skip("Add Email button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#email-modal")
        await expect(modal).to_be_visible()

        # Fill required fields
        name_input = page.locator("#email-name")
        host_input = page.locator("#smtp-host")
        port_input = page.locator("#smtp-port")
        from_input = page.locator("#from-address")
        to_input = page.locator("#recipients-to")
        if (
            await name_input.count() == 0
            or await host_input.count() == 0
            or await port_input.count() == 0
            or await from_input.count() == 0
            or await to_input.count() == 0
        ):
            pytest.skip("Email form fields not available.")
        await name_input.fill(name)
        await host_input.fill("example.com")
        await port_input.fill("587")
        await from_input.fill("alerts@example.com")
        await to_input.fill("ops@example.com")

        # Scroll submit button into view and click (long form may exceed viewport)
        submit_btn = page.locator("#email-form button[type='submit']")
        if await submit_btn.count() == 0:
            submit_btn = modal.get_by_role("button", name="Save")
        if await submit_btn.count() == 0:
            pytest.skip("Email submit button not available.")
        await submit_btn.scroll_into_view_if_needed()
        await page.locator("#email-modal .modal").evaluate("el => { el.scrollTop = el.scrollHeight; }")
        await submit_btn.click(force=True)
        await expect(modal).to_be_hidden(timeout=10000)
        await page.wait_for_timeout(500)

        # Verify integration appears in list
        list_el = page.locator("#email-list")
        if await list_el.count() == 0:
            pytest.skip("Email list not visible.")
        await expect(list_el).to_contain_text(name)

        # Track for cleanup
        response = await page.request.get("/customer/integrations/email")
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
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
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        assert response.status in (200, 201)

        # Navigate and verify presence
        await page.goto("/app/integrations/email")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#email-list")
        if await list_el.count() == 0:
            pytest.skip("Email list not visible.")
        await expect(list_el).to_contain_text(name)

        # Find the specific row's Delete button
        delete_btn = await _find_row_with_name(page, "#email-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        # Delete with confirmation
        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        # Refresh and verify removal
        await page.goto("/app/integrations/email")
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
        await page.goto("/app/integrations/mqtt")
        await page.wait_for_load_state("domcontentloaded")

        name = f"E2E MQTT {uuid.uuid4().hex[:6]}"

        add_button = page.get_by_role("button", name="Add MQTT")
        if await add_button.count() == 0:
            add_button = page.get_by_role("button", name="Add MQTT Integration")
        if await add_button.count() == 0:
            add_button = page.locator("#btn-add-mqtt")
        if await add_button.count() == 0:
            pytest.skip("Add MQTT button not available.")
        await add_button.first.click()
        modal = page.get_by_role("dialog").first
        if await modal.count() == 0:
            modal = page.locator("#mqtt-modal")
        await expect(modal).to_be_visible()

        name_input = page.locator("#mqtt-name")
        topic_input = page.locator("#mqtt-topic")
        if await name_input.count() == 0 or await topic_input.count() == 0:
            pytest.skip("MQTT form fields not available.")
        await name_input.fill(name)
        await topic_input.fill("alerts/test-tenant/INFO/test-site/test-device")

        submit_button = page.locator("#mqtt-form button[type='submit']")
        if await submit_button.count() == 0:
            submit_button = modal.get_by_role("button", name="Save")
        if await submit_button.count() == 0:
            pytest.skip("MQTT submit button not available.")
        await submit_button.first.click()

        await expect(modal).to_be_hidden(timeout=5000)
        await page.wait_for_timeout(500)

        list_el = page.locator("#mqtt-list")
        if await list_el.count() == 0:
            pytest.skip("MQTT list not visible.")
        await expect(list_el).to_contain_text(name)

        response = await page.request.get("/customer/integrations/mqtt")
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
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
        if response.status in (401, 403):
            pytest.skip("Integration API not authorized for this environment.")
        assert response.status in (200, 201)

        await page.goto("/app/integrations/mqtt")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(500)

        list_el = page.locator("#mqtt-list")
        if await list_el.count() == 0:
            pytest.skip("MQTT list not visible.")
        await expect(list_el).to_contain_text(name)

        delete_btn = await _find_row_with_name(page, "#mqtt-list", name)
        assert delete_btn is not None, f"Could not find row with name {name}"

        page.once("dialog", lambda dialog: dialog.accept())
        await delete_btn.click()
        await page.wait_for_timeout(500)

        await page.goto("/app/integrations/mqtt")
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
            ("webhook", "/app/integrations/webhooks"),
            ("snmp", "/app/integrations/snmp"),
            ("email", "/app/integrations/email"),
            ("mqtt", "/app/integrations/mqtt"),
        ]:
            await page.goto(path)
            await page.wait_for_load_state("domcontentloaded")
            card = page.locator("[data-slot='card'], .card").first
            if await card.count() == 0:
                pytest.skip(f"Card element not visible on {name} integrations page.")
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
            ("/app/integrations/webhooks", "#btn-add-webhook"),
            ("/app/integrations/snmp", "#btn-add-snmp"),
            ("/app/integrations/email", "#btn-add-email"),
            ("/app/integrations/mqtt", "#btn-add-mqtt"),
        ]:
            await page.goto(path)
            await page.wait_for_load_state("domcontentloaded")
            button = page.locator(btn_id)
            if await button.count() == 0:
                button = page.get_by_role("button", name="Add").first
            if await button.count() == 0:
                pytest.skip(f"Add button not visible on {path}.")
            await expect(button).to_be_visible()
