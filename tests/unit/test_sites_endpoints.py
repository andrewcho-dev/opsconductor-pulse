from contextlib import asynccontextmanager
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
        self.site_row = {"site_id": "s1", "name": "Site 1", "location": "Loc"}
        self.site_rows = []
        self.devices_rows = []
        self.alert_rows = []
        self.fetch_calls = []

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        if "FROM sites s" in query:
            return self.site_rows
        if "FROM device_registry dr" in query:
            return self.devices_rows
        if "FROM fleet_alert" in query:
            return self.alert_rows
        return []

    async def fetchrow(self, query, *args):
        if "FROM sites WHERE" in query:
            return self.site_row
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


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("csrf_token", "csrf")
        yield client
    app_module.app.dependency_overrides.clear()


async def test_list_sites_returns_all(client, monkeypatch):
    conn = FakeConn()
    conn.site_rows = [
        {
            "site_id": "s1",
            "name": "Site 1",
            "location": "A",
            "latitude": None,
            "longitude": None,
            "device_count": 2,
            "online_count": 1,
            "stale_count": 0,
            "offline_count": 1,
            "active_alert_count": 1,
        }
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert "device_count" in resp.json()["sites"][0]


async def test_list_sites_empty(client, monkeypatch):
    conn = FakeConn()
    conn.site_rows = []
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json() == {"sites": [], "total": 0}


async def test_get_site_summary_success(client, monkeypatch):
    conn = FakeConn()
    conn.devices_rows = [{"device_id": "d1", "name": "D1", "status": "ONLINE", "device_type": "temp"}]
    conn.alert_rows = [{"id": 1, "alert_type": "THRESHOLD", "severity": 1, "summary": "x", "status": "OPEN"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites/s1/summary", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["device_count"] == 1
    assert body["active_alert_count"] == 1


async def test_get_site_summary_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.site_row = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites/missing/summary", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_site_summary_alerts_capped(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites/s1/summary", headers=_auth_header())
    assert resp.status_code == 200
    alert_query = [q for q, _ in conn.fetch_calls if "FROM fleet_alert" in q][0]
    assert "LIMIT 20" in alert_query


async def test_list_sites_only_tenant_sites(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/sites", headers=_auth_header())
    assert resp.status_code == 200
    query, _ = conn.fetch_calls[0]
    assert "WHERE s.tenant_id = $1" in query
