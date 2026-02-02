"""Unit tests for SNMP sender."""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from services.ui_iot.services.snmp_sender import (
    SNMPSender,
    AlertTrapData,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestSNMPSender:
    """Test SNMP sender functionality."""

    def test_build_varbinds(self):
        """Test building varbinds for trap."""
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )
        varbinds = sender._build_alert_varbinds(alert, "1.3.6.1.4.1.99999")
        assert len(varbinds) == 6

    @patch("services.ui_iot.services.snmp_sender.sendNotification")
    async def test_send_trap_v2c_success(self, mock_send):
        """Test successful SNMPv2c trap."""
        mock_send.return_value = (None, None, None, [])
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test",
            timestamp=datetime.utcnow(),
        )
        result = await sender.send_trap(
            host="192.0.2.100",
            port=162,
            config={"version": "2c", "community": "public"},
            alert=alert,
        )
        assert result.success is True

    async def test_unsupported_version(self):
        """Test unsupported SNMP version."""
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test",
            timestamp=datetime.utcnow(),
        )
        result = await sender.send_trap(
            host="192.0.2.100",
            port=162,
            config={"version": "1"},
            alert=alert,
        )
        assert result.success is False
        assert "Unsupported" in result.error
