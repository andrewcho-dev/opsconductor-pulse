"""Unit tests for alert dispatcher."""

import pytest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from services.ui_iot.services.alert_dispatcher import (
    dispatch_alert,
    dispatch_to_integration,
    AlertPayload,
    DeliveryType,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def sample_alert():
    return AlertPayload(
        alert_id="alert-123",
        device_id="device-456",
        tenant_id="tenant-a",
        severity="critical",
        message="Test alert",
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def snmp_integration():
    return {
        "integration_id": "int-1",
        "name": "Test SNMP",
        "type": "snmp",
        "snmp_host": "192.0.2.100",
        "snmp_port": 162,
        "snmp_config": {"version": "2c", "community": "public"},
        "enabled": True,
    }


class TestDispatcher:
    """Test dispatcher functionality."""

    @patch("services.ui_iot.services.alert_dispatcher.send_alert_trap")
    async def test_dispatch_snmp(self, mock_send, sample_alert, snmp_integration):
        """Test SNMP dispatch."""
        mock_send.return_value = SimpleNamespace(success=True, error=None, duration_ms=30.0)
        result = await dispatch_alert(sample_alert, [snmp_integration])
        assert result.successful == 1

    async def test_skip_disabled(self, sample_alert, snmp_integration):
        """Test disabled integrations skipped."""
        snmp_integration["enabled"] = False
        result = await dispatch_alert(sample_alert, [snmp_integration])
        assert len(result.results) == 0

    async def test_unknown_type(self, sample_alert):
        """Test unknown type returns error."""
        integration = {"id": "1", "name": "Bad", "type": "email"}
        result = await dispatch_to_integration(sample_alert, integration)
        assert not result.success
        assert "Unknown" in result.error
