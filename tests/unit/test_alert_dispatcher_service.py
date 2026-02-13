from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.ui_iot.services import alert_dispatcher as dispatcher

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _alert():
    return dispatcher.AlertPayload(
        alert_id="a1",
        device_id="d1",
        tenant_id="tenant-a",
        severity="critical",
        message="temperature high",
        timestamp=datetime.now(timezone.utc),
        metadata={"k": "v"},
    )


async def test_dispatch_alert_to_webhook_and_snmp(monkeypatch):
    monkeypatch.setattr(
        dispatcher,
        "_deliver_webhook",
        AsyncMock(
            return_value=dispatcher.DeliveryResult(
                integration_id="i1",
                integration_name="Webhook",
                delivery_type=dispatcher.DeliveryType.WEBHOOK,
                success=True,
            )
        ),
    )
    monkeypatch.setattr(
        dispatcher,
        "_deliver_snmp",
        AsyncMock(
            return_value=dispatcher.DeliveryResult(
                integration_id="i2",
                integration_name="SNMP",
                delivery_type=dispatcher.DeliveryType.SNMP,
                success=True,
            )
        ),
    )
    result = await dispatcher.dispatch_alert(
        _alert(),
        [
            {"integration_id": "i1", "type": "webhook", "enabled": True},
            {"integration_id": "i2", "type": "snmp", "enabled": True},
        ],
    )
    assert result.total_integrations == 2
    assert result.successful == 2
    assert result.failed == 0


async def test_dispatch_alert_skips_disabled_integrations(monkeypatch):
    webhook = AsyncMock()
    monkeypatch.setattr(dispatcher, "_deliver_webhook", webhook)
    result = await dispatcher.dispatch_alert(
        _alert(),
        [{"integration_id": "i1", "type": "webhook", "enabled": False}],
    )
    assert result.successful == 0
    webhook.assert_not_awaited()


async def test_dispatch_alert_handles_delivery_exception(monkeypatch):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(dispatcher, "_deliver_webhook", _boom)
    result = await dispatcher.dispatch_alert(
        _alert(),
        [{"integration_id": "i1", "type": "webhook", "enabled": True}],
    )
    assert result.failed == 1
    assert "network error" in result.results[0].error


async def test_deliver_webhook_success(monkeypatch):
    class _Resp:
        status_code = 200

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *_args, **_kwargs):
            return _Resp()

    monkeypatch.setattr(dispatcher.httpx, "AsyncClient", lambda **_kwargs: _Client())
    result = await dispatcher._deliver_webhook(
        _alert(),
        {"integration_id": "i1", "name": "Webhook A", "webhook_url": "http://example.com/hook"},
    )
    assert result.success is True
    assert result.error is None


async def test_deliver_webhook_missing_url():
    result = await dispatcher._deliver_webhook(_alert(), {"integration_id": "i1", "name": "Webhook A"})
    assert result.success is False
    assert "Missing webhook_url" in result.error


async def test_deliver_snmp_success(monkeypatch):
    monkeypatch.setattr(
        dispatcher,
        "send_alert_trap",
        AsyncMock(return_value=MagicMock(success=True, error=None, duration_ms=7.5)),
    )
    result = await dispatcher._deliver_snmp(
        _alert(),
        {
            "integration_id": "i2",
            "name": "SNMP A",
            "snmp_host": "127.0.0.1",
            "snmp_config": {"version": "2c", "community": "public"},
        },
    )
    assert result.success is True
    assert result.delivery_type == dispatcher.DeliveryType.SNMP


async def test_deliver_snmp_missing_config():
    result = await dispatcher._deliver_snmp(_alert(), {"integration_id": "i2", "name": "SNMP A"})
    assert result.success is False
    assert "Missing snmp_host or snmp_config" in result.error


async def test_dispatch_to_integration_unknown_type():
    result = await dispatcher.dispatch_to_integration(_alert(), {"integration_id": "i9", "type": "email"})
    assert result.success is False
    assert "Unknown integration type" in result.error
