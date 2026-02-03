"""Unit tests for email sender."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestEmailSender:
    """Test email sender functionality."""

    async def test_render_template(self):
        """Test template rendering."""
        from services.ui_iot.services.email_sender import render_template

        result = render_template(
            "Alert: {alert_type} on {device_id}",
            alert_type="NO_HEARTBEAT",
            device_id="sensor-001",
        )
        assert result == "Alert: NO_HEARTBEAT on sensor-001"

    async def test_render_template_missing_var(self):
        """Test template with missing variable doesn't crash."""
        from services.ui_iot.services.email_sender import render_template

        # Should return template as-is when variable missing
        result = render_template(
            "Alert: {alert_type} on {missing_var}",
            alert_type="NO_HEARTBEAT",
        )
        # Returns original template due to KeyError handling
        assert "{missing_var}" in result or "NO_HEARTBEAT" in result

    @patch("services.ui_iot.services.email_sender.aiosmtplib")
    async def test_send_email_success(self, mock_aiosmtplib):
        """Test successful email send."""
        from services.ui_iot.services.email_sender import send_alert_email

        # Mock SMTP
        mock_smtp = AsyncMock()
        mock_aiosmtplib.SMTP.return_value = mock_smtp
        mock_smtp.__aenter__.return_value = mock_smtp

        result = await send_alert_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            smtp_tls=True,
            from_address="alerts@example.com",
            from_name="Alerts",
            recipients={"to": ["admin@example.com"]},
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            alert_type="NO_HEARTBEAT",
            timestamp=datetime.utcnow(),
        )

        assert result.success
        assert result.recipients_count == 1

    async def test_send_email_no_recipients(self):
        """Test email with no recipients fails."""
        from services.ui_iot.services.email_sender import send_alert_email

        result = await send_alert_email(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user=None,
            smtp_password=None,
            smtp_tls=True,
            from_address="alerts@example.com",
            from_name="Alerts",
            recipients={"to": [], "cc": [], "bcc": []},
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            alert_type="NO_HEARTBEAT",
            timestamp=datetime.utcnow(),
        )

        assert not result.success
        assert "No recipients" in result.error
