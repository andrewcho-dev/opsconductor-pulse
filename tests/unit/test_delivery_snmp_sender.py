from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import snmp_sender

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class DummyObjectIdentity:
    def __init__(self, oid):
        self.oid = oid


class DummyObjectType:
    def __init__(self, identity, value):
        self.identity = identity
        self.value = value


def _patch_snmp_base(monkeypatch):
    monkeypatch.setattr(snmp_sender, "CommunityData", lambda *a, **k: ("community", a, k), raising=False)
    monkeypatch.setattr(snmp_sender, "UdpTransportTarget", lambda *a, **k: ("transport", a, k), raising=False)
    monkeypatch.setattr(snmp_sender, "ContextData", lambda: "ctx", raising=False)
    monkeypatch.setattr(snmp_sender, "NotificationType", lambda identity: identity, raising=False)
    monkeypatch.setattr(snmp_sender, "ObjectIdentity", DummyObjectIdentity, raising=False)
    monkeypatch.setattr(snmp_sender, "ObjectType", DummyObjectType, raising=False)
    monkeypatch.setattr(snmp_sender, "SnmpEngine", lambda: "engine", raising=False)
    monkeypatch.setattr(snmp_sender, "OctetString", lambda v: v, raising=False)
    monkeypatch.setattr(snmp_sender, "usmHMACSHAAuthProtocol", "sha", raising=False)
    monkeypatch.setattr(snmp_sender, "usmAesCfb128Protocol", "aes", raising=False)
    monkeypatch.setattr(snmp_sender, "usmDESPrivProtocol", "des", raising=False)


async def test_send_v2c_trap(monkeypatch):
    community_mock = MagicMock()
    send_mock = AsyncMock(return_value=(None, None, None, None))
    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    _patch_snmp_base(monkeypatch)
    monkeypatch.setattr(snmp_sender, "CommunityData", community_mock, raising=False)
    monkeypatch.setattr(snmp_sender, "sendNotification", send_mock, raising=False)

    result = await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={"version": "2c", "community": "public"},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        timestamp=datetime.now(timezone.utc),
    )

    assert result.success is True
    community_mock.assert_called_once()


async def test_send_v3_trap(monkeypatch):
    user_mock = MagicMock()
    send_mock = AsyncMock(return_value=(None, None, None, None))
    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    monkeypatch.setattr(snmp_sender, "UsmUserData", user_mock, raising=False)
    _patch_snmp_base(monkeypatch)
    monkeypatch.setattr(snmp_sender, "sendNotification", send_mock, raising=False)

    result = await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={
            "version": "3",
            "username": "user",
            "auth_password": "auth",
            "priv_password": "priv",
            "priv_protocol": "AES",
        },
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="warning",
        message="Alert",
        timestamp=datetime.now(timezone.utc),
    )

    assert result.success is True
    user_mock.assert_called()


async def test_send_trap_timeout(monkeypatch):
    send_mock = AsyncMock(return_value=("timeout", None, None, None))
    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    _patch_snmp_base(monkeypatch)
    monkeypatch.setattr(snmp_sender, "sendNotification", send_mock, raising=False)

    result = await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={"version": "2c", "community": "public"},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="info",
        message="Alert",
        timestamp=datetime.now(timezone.utc),
    )

    assert result.success is False
    assert "timeout" in result.error


async def test_send_trap_unreachable(monkeypatch):
    send_mock = AsyncMock(side_effect=ConnectionError("unreachable"))
    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    _patch_snmp_base(monkeypatch)
    monkeypatch.setattr(snmp_sender, "sendNotification", send_mock, raising=False)

    result = await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={"version": "2c", "community": "public"},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="info",
        message="Alert",
        timestamp=datetime.now(timezone.utc),
    )

    assert result.success is False
    assert "unreachable" in result.error


async def test_varbind_construction(monkeypatch):
    captured = {}

    async def _send(*args, **kwargs):
        captured["args"] = args
        return (None, None, None, None)

    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    _patch_snmp_base(monkeypatch)
    monkeypatch.setattr(snmp_sender, "sendNotification", _send, raising=False)

    await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={"version": "2c", "community": "public"},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        oid_prefix="1.3.6.1.4.1.99999",
    )

    var_binds = captured["args"][6:]
    assert len(var_binds) == 6
    assert var_binds[0].identity.oid.endswith(".1.1.0")


async def test_unsupported_version(monkeypatch):
    monkeypatch.setattr(snmp_sender, "PYSNMP_AVAILABLE", True)
    result = await snmp_sender.send_alert_trap(
        host="198.51.100.10",
        port=162,
        config={"version": "1"},
        alert_id="a1",
        device_id="d1",
        tenant_id="t1",
        severity="critical",
        message="Alert",
        timestamp=datetime.now(timezone.utc),
    )

    assert result.success is False
    assert "Unsupported" in result.error
