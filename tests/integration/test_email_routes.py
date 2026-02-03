"""Integration tests for email integration routes."""

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestEmailIntegrationRoutes:
    """Test email integration CRUD routes."""

    async def test_list_email_integrations_empty(self, client, auth_headers):
        """Test listing email integrations when none exist."""
        response = await client.get(
            "/customer/integrations/email",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_email_integration(self, client, auth_headers):
        """Test creating an email integration."""
        payload = {
            "name": "Test Email",
            "smtp_config": {
                "smtp_host": "8.8.8.8",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
                "from_name": "Test Alerts",
            },
            "recipients": {
                "to": ["admin@example.com"],
                "cc": [],
                "bcc": [],
            },
            "enabled": True,
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Email"
        assert data["smtp_host"] == "8.8.8.8"
        assert data["recipient_count"] == 1

    async def test_create_email_integration_invalid_smtp_host(self, client, auth_headers):
        """Test that private SMTP hosts are rejected."""
        payload = {
            "name": "Bad SMTP",
            "smtp_config": {
                "smtp_host": "192.168.1.1",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
            },
            "recipients": {
                "to": ["admin@example.com"],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower() or "blocked" in response.json()["detail"].lower()

    async def test_create_email_integration_no_recipients(self, client, auth_headers):
        """Test that at least one recipient is required."""
        payload = {
            "name": "No Recipients",
            "smtp_config": {
                "smtp_host": "8.8.8.8",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "alerts@example.com",
            },
            "recipients": {
                "to": [],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]

    async def test_create_email_integration_invalid_email(self, client, auth_headers):
        """Test that invalid email addresses are rejected."""
        payload = {
            "name": "Invalid Email",
            "smtp_config": {
                "smtp_host": "8.8.8.8",
                "smtp_port": 587,
                "smtp_tls": True,
                "from_address": "not-an-email",
            },
            "recipients": {
                "to": ["admin@example.com"],
            },
        }
        response = await client.post(
            "/customer/integrations/email",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]

    async def test_get_email_integration(self, client, auth_headers, created_email_integration):
        """Test getting a specific email integration."""
        integration_id = created_email_integration["id"]
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == integration_id

    async def test_get_email_integration_not_found(self, client, auth_headers):
        """Test getting non-existent integration returns 404."""
        response = await client.get(
            "/customer/integrations/email/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_email_integration(self, client, auth_headers, created_email_integration):
        """Test updating an email integration."""
        integration_id = created_email_integration["id"]
        response = await client.patch(
            f"/customer/integrations/email/{integration_id}",
            json={"name": "Updated Email", "enabled": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Email"
        assert data["enabled"] is False

    async def test_delete_email_integration(self, client, auth_headers, created_email_integration):
        """Test deleting an email integration."""
        integration_id = created_email_integration["id"]
        response = await client.delete(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_test_email_integration(self, client, auth_headers, created_email_integration):
        """Test sending a test email."""
        integration_id = created_email_integration["id"]

        with patch("services.ui_iot.services.email_sender.aiosmtplib") as mock_smtp:
            mock_smtp.SMTP.return_value.__aenter__ = AsyncMock()
            mock_smtp.SMTP.return_value.__aexit__ = AsyncMock()
            mock_smtp.SMTP.return_value.send_message = AsyncMock()

            response = await client.post(
                f"/customer/integrations/email/{integration_id}/test",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    async def test_tenant_isolation(self, client, auth_headers, other_tenant_headers, created_email_integration):
        """Test that one tenant cannot access another tenant's integrations."""
        integration_id = created_email_integration["id"]

        # Try to access with different tenant
        response = await client.get(
            f"/customer/integrations/email/{integration_id}",
            headers=other_tenant_headers,
        )
        assert response.status_code == 404


@pytest.fixture
async def created_email_integration(client, auth_headers):
    """Create an email integration for testing."""
    payload = {
        "name": "Test Email Fixture",
        "smtp_config": {
            "smtp_host": "8.8.8.8",
            "smtp_port": 587,
            "smtp_tls": True,
            "from_address": "alerts@example.com",
        },
        "recipients": {
            "to": ["admin@example.com"],
        },
    }
    response = await client.post(
        "/customer/integrations/email",
        json=payload,
        headers=auth_headers,
    )
    return response.json()
