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


def _row(ts: str, metrics: dict, seq: int = 1):
    return {
        "time": datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc),
        "device_id": "dev-1",
        "site_id": "site-1",
        "seq": seq,
        "metrics": metrics,
    }


async def test_export_csv_returns_streaming_response(client, monkeypatch):
    conn = FakeConn()
    conn.rows = [_row("2026-01-01T00:00:00Z", {"temperature": 70.0})]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")


async def test_export_csv_has_content_disposition(client, monkeypatch):
    conn = FakeConn()
    conn.rows = [_row("2026-01-01T00:00:00Z", {"temperature": 70.0})]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h",
        headers=_auth_header(),
    )
    assert "attachment; filename=dev-1_telemetry_24h.csv" in resp.headers.get(
        "content-disposition", ""
    )


async def test_export_csv_metric_keys_as_columns(client, monkeypatch):
    conn = FakeConn()
    conn.rows = [
        _row("2026-01-01T00:00:00Z", {"temperature": 70.0, "humidity": 40}),
        _row("2026-01-01T00:01:00Z", {"temperature": 71.0}),
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    header = resp.text.splitlines()[0]
    assert "temperature" in header
    assert "humidity" in header


async def test_export_csv_empty_returns_headers(client, monkeypatch):
    conn = FakeConn()
    conn.rows = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert resp.text.splitlines()[0] == "time,device_id,site_id,seq"


async def test_export_csv_invalid_range(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=99y",
        headers=_auth_header(),
    )
    assert resp.status_code == 400


async def test_export_csv_limit_param(client, monkeypatch):
    conn = FakeConn()
    conn.rows = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h&limit=100",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert conn.last_args[3] == 100


async def test_export_csv_tenant_isolation(client, monkeypatch):
    conn = FakeConn()
    conn.rows = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/customer/devices/dev-1/telemetry/export?range=24h",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert "WHERE tenant_id = $1" in conn.last_query
