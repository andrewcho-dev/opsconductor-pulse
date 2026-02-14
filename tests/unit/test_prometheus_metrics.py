from contextlib import asynccontextmanager

import httpx
import pytest

import app as app_module
from shared.metrics import (
    ingest_messages_total,
    fleet_active_alerts,
    fleet_devices_by_status,
    evaluator_rules_evaluated_total,
)

pytestmark = [pytest.mark.unit]


class FakeConn:
    async def fetch(self, query, *_args):
        if "FROM fleet_alert" in query:
            return [{"tenant_id": "tenant-a", "cnt": 2}]
        if "FROM device_state" in query:
            return [{"tenant_id": "tenant-a", "status": "ONLINE", "cnt": 3}]
        return []


class FakePool:
    @asynccontextmanager
    async def acquire(self):
        yield FakeConn()


def _counter_value(metric, **labels):
    return metric.labels(**labels)._value.get()


def test_shared_metrics_importable():
    assert ingest_messages_total is not None


def test_ingest_counter_increment():
    before = _counter_value(ingest_messages_total, tenant_id="tenant-a", result="accepted")
    ingest_messages_total.labels(tenant_id="tenant-a", result="accepted").inc()
    assert _counter_value(ingest_messages_total, tenant_id="tenant-a", result="accepted") == before + 1


def test_fleet_alerts_gauge_set():
    fleet_active_alerts.labels(tenant_id="tenant-a").set(5)
    assert fleet_active_alerts.labels(tenant_id="tenant-a")._value.get() == 5


def test_fleet_devices_gauge_set():
    fleet_devices_by_status.labels(tenant_id="tenant-a", status="ONLINE").set(4)
    assert fleet_devices_by_status.labels(tenant_id="tenant-a", status="ONLINE")._value.get() == 4


def test_evaluator_counter_increment():
    before = _counter_value(evaluator_rules_evaluated_total, tenant_id="tenant-a")
    evaluator_rules_evaluated_total.labels(tenant_id="tenant-a").inc()
    assert _counter_value(evaluator_rules_evaluated_total, tenant_id="tenant-a") == before + 1


@pytest.mark.asyncio
async def test_ui_iot_metrics_endpoint(monkeypatch):
    async def _fake_get_pool():
        return FakePool()

    monkeypatch.setattr(app_module, "get_pool", _fake_get_pool)
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "pulse_fleet_active_alerts" in resp.text
