import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestCustomerDevices:
    """Test /customer/devices endpoints."""

    async def test_list_devices_requires_auth(self, client: AsyncClient):
        """Unauthenticated request returns 401."""
        response = await client.get("/customer/devices")
        assert response.status_code == 401

    async def test_list_devices_with_token(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Authenticated request returns tenant's devices only."""
        response = await client.get(
            "/customer/devices?format=json",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "tenant_id" in data
        for device in data["devices"]:
            assert device["tenant_id"] == test_tenants["tenant_a"]

    async def test_list_devices_with_cookie(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Cookie authentication works."""
        response = await client.get(
            "/customer/devices?format=json",
            cookies={"pulse_session": customer_a_token},
        )
        assert response.status_code == 200

    async def test_get_device_detail(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Get single device by ID."""
        response = await client.get(
            "/customer/devices/test-device-a1?format=json",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device"]["device_id"] == "test-device-a1"

    async def test_get_device_wrong_tenant_returns_404(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """Cannot access device from another tenant."""
        response = await client.get(
            "/customer/devices/test-device-b1",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 404

    async def test_operator_cannot_access_customer_routes(
        self, client: AsyncClient, operator_token: str
    ):
        """Operator role cannot access customer routes."""
        response = await client.get(
            "/customer/devices",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert response.status_code == 403


class TestCustomerAlerts:
    """Test /customer/alerts endpoints."""

    async def test_list_alerts(
        self, client: AsyncClient, customer_a_token: str, test_tenants
    ):
        """List alerts for tenant."""
        response = await client.get(
            "/customer/alerts?format=json",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        for alert in data["alerts"]:
            assert alert["tenant_id"] == test_tenants["tenant_a"]


class TestCustomerIntegrations:
    """Test /customer/integrations CRUD endpoints."""

    async def test_list_integrations(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """List integrations for tenant."""
        response = await client.get(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "integrations" in data

    async def test_create_integration(
        self, client: AsyncClient, customer_a_token: str, clean_db
    ):
        """Create new integration."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Test Integration",
                "webhook_url": "https://webhook.site/test-uuid",
                "enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Integration"
        assert "integration_id" in data

    async def test_create_integration_ssrf_blocked(
        self, client: AsyncClient, customer_a_token: str
    ):
        """SSRF blocked for private IPs."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Evil Integration",
                "webhook_url": "https://10.0.0.1/internal",
                "enabled": True,
            },
        )
        assert response.status_code == 400
        detail = response.json().get("detail", "")
        assert "Private IP" in detail or "blocked" in detail.lower()

    async def test_create_integration_localhost_blocked(
        self, client: AsyncClient, customer_a_token: str
    ):
        """SSRF blocked for localhost."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={
                "name": "Localhost Integration",
                "webhook_url": "https://localhost/hook",
                "enabled": True,
            },
        )
        assert response.status_code == 400

    async def test_update_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Update existing integration."""
        response = await client.patch(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={"enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    async def test_update_integration_empty_patch_rejected(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Empty PATCH returns 400."""
        response = await client.patch(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={},
        )
        assert response.status_code == 400

    async def test_delete_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Delete integration."""
        response = await client.delete(
            f"/customer/integrations/{test_integrations['integration_a']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 204

    async def test_cannot_access_other_tenant_integration(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Cannot access integration from another tenant."""
        response = await client.get(
            f"/customer/integrations/{test_integrations['integration_b']}",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code == 404

    async def test_viewer_cannot_create(
        self, client: AsyncClient, customer_viewer_token: str
    ):
        """Customer viewer cannot create integrations."""
        response = await client.post(
            "/customer/integrations",
            headers={"Authorization": f"Bearer {customer_viewer_token}"},
            json={
                "name": "Viewer Integration",
                "webhook_url": "https://example.com/hook",
                "enabled": True,
            },
        )
        assert response.status_code == 403


class TestTestDelivery:
    """Test /customer/integrations/{id}/test endpoint."""

    async def test_test_delivery(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Test delivery returns result."""
        response = await client.post(
            f"/customer/integrations/{test_integrations['integration_a']}/test",
            headers={"Authorization": f"Bearer {customer_a_token}"},
        )
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "latency_ms" in data

    async def test_rate_limiting(
        self, client: AsyncClient, customer_a_token: str, test_integrations
    ):
        """Rate limiting kicks in after 5 requests."""
        integration_id = test_integrations["integration_a"]
        for i in range(6):
            response = await client.post(
                f"/customer/integrations/{integration_id}/test",
                headers={"Authorization": f"Bearer {customer_a_token}"},
            )
            if i < 5:
                assert response.status_code != 429
            else:
                assert response.status_code == 429
