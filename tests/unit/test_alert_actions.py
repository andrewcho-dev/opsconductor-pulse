from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
        self.fetchrow_result = None
        self.fetch_result = []
        self.fetchval_result = 0
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.fetchval_calls = []

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return self.fetchrow_result

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        return self.fetchval_result


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


def _mock_user_payload(role: str, tenant_id: str) -> dict:
    role_map = {
        "customer_admin": ["customer", "tenant-admin"],
        "customer_viewer": ["customer"],
    }
    return {
        "sub": "user-1",
        "email": "user@example.com",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": role_map.get(role, [role])},
    }


def _mock_customer_deps(monkeypatch, conn, role="customer_admin", tenant_id="tenant-a"):
    user_payload = _mock_user_payload(role, tenant_id)
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(return_value=user_payload),
    )

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
    ) as client:
        client.cookies.set("csrf_token", "csrf")
        from middleware import permissions as perm_mod
        async def _grant(req): perm_mod.permissions_context.set({"*"})
        app_module.app.dependency_overrides[perm_mod.inject_permissions] = _grant
        yield client
    app_module.app.dependency_overrides.clear()


async def test_acknowledge_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "ACKNOWLEDGED"}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/alerts/1/acknowledge", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACKNOWLEDGED"


async def test_acknowledge_alert_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/alerts/1/acknowledge", headers=_auth_header())
    assert resp.status_code == 404


async def test_close_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "status": "CLOSED"}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/alerts/1/close", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"


async def test_close_already_closed(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/alerts/1/close", headers=_auth_header())
    assert resp.status_code == 404


async def test_silence_alert_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": 1, "silenced_until": datetime.now(timezone.utc)}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch(
        "/customer/alerts/1/silence",
        headers=_auth_header(),
        json={"minutes": 30},
    )
    assert resp.status_code == 200
    assert "silenced_until" in resp.json()


async def test_silence_alert_invalid_minutes(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch(
        "/customer/alerts/1/silence",
        headers=_auth_header(),
        json={"minutes": 0},
    )
    assert resp.status_code == 422


async def test_list_alerts_default_open(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    query, args = conn.fetch_calls[-1]
    assert "status = $2" in query
    assert args[1] == "OPEN"


async def test_list_alerts_acknowledged(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/customer/alerts?status=ACKNOWLEDGED", headers=_auth_header())
    assert resp.status_code == 200
    query, args = conn.fetch_calls[-1]
    assert "status = $2" in query
    assert args[1] == "ACKNOWLEDGED"


async def test_list_alerts_all(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/customer/alerts?status=ALL", headers=_auth_header())
    assert resp.status_code == 200
    query, _ = conn.fetch_calls[-1]
    assert "status = $2" not in query


async def test_list_alerts_invalid_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.get("/customer/alerts?status=BOGUS", headers=_auth_header())
    assert resp.status_code == 400
