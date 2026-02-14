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
        self.fetchrow_result = None
        self.fetchval_result = 1

    async def fetch(self, _query, *_args):
        return self.fetch_rows

    async def fetchrow(self, _query, *_args):
        return self.fetchrow_result

    async def fetchval(self, _query, *_args):
        return self.fetchval_result

    async def execute(self, _query, *_args):
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


async def test_list_groups_returns_groups(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [{"group_id": "g1", "name": "Group 1", "description": None, "member_count": 2}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/device-groups", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["groups"][0]["member_count"] == 2


async def test_list_groups_empty(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/device-groups", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["groups"] == []


async def test_create_group_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"group_id": "g1", "name": "Group 1", "description": None}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/device-groups",
        headers=_auth_header(),
        json={"name": "Group 1"},
    )
    assert resp.status_code == 201
    assert resp.json()["group_id"] == "g1"


async def test_create_group_conflict(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/device-groups",
        headers=_auth_header(),
        json={"group_id": "g1", "name": "Group 1"},
    )
    assert resp.status_code == 409


async def test_update_group_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"group_id": "g1", "name": "Updated", "description": "desc"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch(
        "/customer/device-groups/g1",
        headers=_auth_header(),
        json={"name": "Updated"},
    )
    assert resp.status_code == 200


async def test_update_group_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch(
        "/customer/device-groups/g1",
        headers=_auth_header(),
        json={"name": "Updated"},
    )
    assert resp.status_code == 404


async def test_delete_group_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"group_id": "g1"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/customer/device-groups/g1", headers=_auth_header())
    assert resp.status_code == 200


async def test_delete_group_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/customer/device-groups/g1", headers=_auth_header())
    assert resp.status_code == 404


async def test_add_group_member_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"group_id": "g1"}
    conn.fetchval_result = 1
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put("/customer/device-groups/g1/devices/d1", headers=_auth_header())
    assert resp.status_code == 200


async def test_remove_group_member_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/customer/device-groups/g1/devices/d1", headers=_auth_header())
    assert resp.status_code == 200


async def test_remove_group_member_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/customer/device-groups/g1/devices/d1", headers=_auth_header())
    assert resp.status_code == 404
