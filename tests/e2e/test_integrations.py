import pytest
import uuid
from playwright.async_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class TestIntegrationManagement:
    """Test integration CRUD via UI (if UI exists) or API."""

    async def test_create_integration_via_api(
        self, authenticated_customer_page: Page
    ):
        """Create integration via API call."""
        page = authenticated_customer_page
        cookies = await page.context.cookies()
        session_cookie = next(
            (c for c in cookies if c["name"] == "pulse_session"),
            None,
        )

        if session_cookie:
            response = await page.request.post(
                "/customer/integrations",
                data={
                    "name": f"E2E Test Integration {uuid.uuid4().hex[:8]}",
                    "webhook_url": "https://webhook.site/test",
                    "enabled": True,
                },
            )
            assert response.status in (200, 201)

    async def test_list_integrations(
        self, authenticated_customer_page: Page
    ):
        """List integrations via API."""
        page = authenticated_customer_page
        response = await page.request.get("/customer/integrations")
        assert response.status == 200
        data = await response.json()
        assert "integrations" in data
