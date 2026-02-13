from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.ui_iot.services import snmp_sender

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_get_snmp_sender_returns_singleton():
    snmp_sender._snmp_sender = None
    first = snmp_sender.get_snmp_sender()
    second = snmp_sender.get_snmp_sender()
    assert first is second


async def test_send_alert_trap_uses_default_port_and_prefix(monkeypatch):
    sender = MagicMock()
    sender.send_trap = AsyncMock(return_value=snmp_sender.SNMPTrapResult(success=True))
    monkeypatch.setattr(snmp_sender, "get_snmp_sender", lambda: sender)
    now = datetime.now(timezone.utc)
    result = await snmp_sender.send_alert_trap(
        host="127.0.0.1",
        port=162,
        config={"version": "2c", "community": "public"},
        alert_id="a1",
        device_id="d1",
        tenant_id="tenant-a",
        severity="warning",
        message="msg",
        timestamp=now,
    )
    assert result.success is True
    sender.send_trap.assert_awaited()


async def test_build_v3_auth_defaults_protocols(monkeypatch):
    sender = snmp_sender.SNMPSender()
    captured = {}

    def _usm_user_data(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "auth"

    monkeypatch.setattr(snmp_sender, "UsmUserData", _usm_user_data)
    result = sender._build_v3_auth(
        {
            "username": "u1",
            "auth_password": "pass",
        }
    )
    assert result == "auth"
    assert captured["args"][0] == "u1"
    assert "authProtocol" in captured["kwargs"]


async def test_send_trap_returns_error_for_unsupported_version():
    sender = snmp_sender.SNMPSender()
    alert = snmp_sender.AlertTrapData(
        alert_id="a1",
        device_id="d1",
        tenant_id="tenant-a",
        severity="critical",
        message="x",
        timestamp=datetime.now(timezone.utc),
    )
    result = await sender.send_trap(
        host="127.0.0.1",
        port=162,
        config={"version": "1"},
        alert=alert,
    )
    assert result.success is False
    assert "Unsupported SNMP version" in result.error


async def test_build_alert_varbinds_maps_unknown_severity_to_info():
    sender = snmp_sender.SNMPSender()
    alert = snmp_sender.AlertTrapData(
        alert_id="a1",
        device_id="d1",
        tenant_id="tenant-a",
        severity="not-known",
        message="m",
        timestamp=datetime.now(timezone.utc),
    )
    varbinds = sender._build_alert_varbinds(alert, "1.3.6.1.4.1.99999")
    assert len(varbinds) == 6
