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
from services.ui_iot.db import queries as db_queries

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_result = []
        self.fetchval_result = 0
        self.fetch_calls = []
        self.fetchval_calls = []

    async def fetchrow(self, query, *args):
        return self.fetchrow_result

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        return self.fetchval_result

    async def execute(self, *_args, **_kwargs):
        return "OK"

    async def executemany(self, *_args, **_kwargs):
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


async def test_update_device_name_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"tenant_id": "tenant-a", "device_id": "d1"}
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1", "model": "name"}))

    resp = await client.patch("/customer/devices/d1", headers=_auth_header(), json={"name": "name"})
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


async def test_update_device_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/devices/missing", headers=_auth_header(), json={"name": "x"})
    assert resp.status_code == 404


async def test_update_device_no_fields(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/devices/d1", headers=_auth_header(), json={})
    assert resp.status_code == 400


async def test_decommission_device_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"device_id": "d1", "decommissioned_at": datetime.now(timezone.utc)}
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/devices/d1/decommission", headers=_auth_header())
    assert resp.status_code == 200
    assert "decommissioned_at" in resp.json()


async def test_decommission_already_done(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)

    resp = await client.patch("/customer/devices/d1/decommission", headers=_auth_header())
    assert resp.status_code == 404


async def test_list_devices_excludes_decommissioned():
    conn = FakeConn()
    await db_queries.fetch_devices_v2(conn, tenant_id="tenant-a", include_decommissioned=False)
    assert "decommissioned_at IS NULL" in conn.fetchval_calls[0][0]


async def test_list_devices_include_decommissioned():
    conn = FakeConn()
    await db_queries.fetch_devices_v2(conn, tenant_id="tenant-a", include_decommissioned=True)
    assert "decommissioned_at IS NULL" not in conn.fetchval_calls[0][0]
