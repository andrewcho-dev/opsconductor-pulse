from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.rows = []
        self.last_query = ""
        self.last_args = ()

    async def fetch(self, query, *args):
        self.last_query = query
        self.last_args = args
        return self.rows


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _tenant_connection(conn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(monkeypatch, conn, tenant_id="tenant-a"):
    user_payload = {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(customer_routes, "get_db_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(customer_routes, "tenant_connection", _tenant_connection(conn))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


def _row(ts: str, avg=10.0, min_v=8.0, max_v=12.0, count=3):
    return {
        "bucket": datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc),
        "avg_val": avg,
        "min_val": min_v,
        "max_val": max_v,
        "sample_count": count,
    }


async def test_telemetry_history_returns_points(client, monkeypatch):
    conn = FakeConn()
    conn.rows = [_row("2026-01-01T00:00:00Z")]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature&range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    point = resp.json()["points"][0]
    assert point["avg"] == 10.0
    assert point["min"] == 8.0
    assert point["max"] == 12.0
    assert point["count"] == 3
    assert point["time"]


async def test_telemetry_history_empty(client, monkeypatch):
    conn = FakeConn()
    conn.rows = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature&range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.json()["points"] == []


async def test_telemetry_history_invalid_range(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature&range=99y",
        headers=_auth_header(),
    )
    assert resp.status_code == 400


async def test_telemetry_history_default_range_24h(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    # args: bucket, metric, tenant, device, lookback
    assert conn.last_args[0] == "15 minutes"
    assert conn.last_args[4] == "24 hours"


async def test_telemetry_history_uses_time_bucket(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature&range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert "time_bucket" in conn.last_query


async def test_telemetry_history_tenant_isolation(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/history?metric=temperature&range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert "WHERE tenant_id = $3" in conn.last_query
