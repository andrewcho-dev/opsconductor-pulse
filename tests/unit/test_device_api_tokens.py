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
        self.fetch_rows = []
        self.fetchval_result = 1
        self.fetchrow_result = None
        self.execute_calls = []

    async def fetch(self, _query, *_args):
        return self.fetch_rows

    async def fetchval(self, _query, *_args):
        return self.fetchval_result

    async def fetchrow(self, _query, *_args):
        return self.fetchrow_result

    async def execute(self, query, *_args):
        self.execute_calls.append(query)
        return "OK"


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


async def test_list_tokens_returns_active_only(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [
        {"id": "t1", "client_id": "c1", "label": "default", "created_at": "x", "revoked_at": None},
        {"id": "t2", "client_id": "c2", "label": "old", "created_at": "x", "revoked_at": "2026-01-01"},
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices/dev-1/tokens", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["tokens"][0]["client_id"] == "c1"


async def test_revoke_token_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"id": "tok-1"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete(
        "/customer/devices/dev-1/tokens/8b77b355-6416-4f6b-b653-4fb85dc94a6c",
        headers=_auth_header(),
    )
    assert resp.status_code == 204


async def test_revoke_token_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete(
        "/customer/devices/dev-1/tokens/8b77b355-6416-4f6b-b653-4fb85dc94a6c",
        headers=_auth_header(),
    )
    assert resp.status_code == 404


async def test_rotate_generates_new_credentials(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/devices/dev-1/tokens/rotate",
        headers=_auth_header(),
        json={"label": "rotated"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["client_id"]
    assert body["password"]
    assert body["broker_url"]


async def test_rotate_revokes_existing_first(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/devices/dev-1/tokens/rotate",
        headers=_auth_header(),
        json={"label": "rotated"},
    )
    assert resp.status_code == 201
    assert any("UPDATE device_api_tokens" in query for query in conn.execute_calls)
