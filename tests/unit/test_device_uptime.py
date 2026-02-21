from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from middleware import permissions as permissions_module
from routes import customer as customer_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_results = []
        self.fetchval_results = []

    async def fetchrow(self, _query, *_args):
        if self.fetchrow_results:
            return self.fetchrow_results.pop(0)
        return None

    async def fetchval(self, _query, *_args):
        if self.fetchval_results:
            return self.fetchval_results.pop(0)
        return None


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
    async def _grant_all(_request=None):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_uptime_no_offline_alerts(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [1, None]  # device exists, no open NO_TELEMETRY
    conn.fetchrow_results = [{"offline_seconds": 0}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices/dev-1/uptime?range=24h", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["uptime_pct"] == 100.0


async def test_uptime_with_offline_period(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [1, None]
    conn.fetchrow_results = [{"offline_seconds": 1800}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices/dev-1/uptime?range=24h", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["uptime_pct"] == 97.9


async def test_uptime_device_currently_offline(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [1, 1]  # second fetchval is open NO_TELEMETRY
    conn.fetchrow_results = [{"offline_seconds": 600}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices/dev-1/uptime?range=24h", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "offline"


async def test_uptime_range_7d(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_results = [1, None]
    conn.fetchrow_results = [{"offline_seconds": 0}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices/dev-1/uptime?range=7d", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["range_seconds"] == 604800


async def test_fleet_uptime_summary_counts(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"total_devices": 3, "online": 2, "offline": 1},
        {"avg_uptime_pct": 98.7},
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/fleet/uptime-summary", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["online"] == 2
    assert body["offline"] == 1


async def test_fleet_uptime_avg_calculation(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_results = [
        {"total_devices": 4, "online": 3, "offline": 1},
        {"avg_uptime_pct": 97.234},
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/fleet/uptime-summary", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["avg_uptime_pct"] == 97.2
