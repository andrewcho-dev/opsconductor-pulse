from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from routes import customer as customer_routes
from routes import devices as devices_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetchval_result = None

    async def fetchrow(self, _query, *_args):
        return self.fetchrow_result

    async def fetchval(self, _query, *_args):
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


async def test_provision_device_returns_credentials(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", AsyncMock(return_value=None))
    conn.fetchrow_result = {"subscription_id": "sub-1"}
    resp = await client.post(
        "/customer/devices",
        headers=_auth_header(),
        json={"device_id": "DEV-1", "site_id": "default-site"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_id"] == "DEV-1"


async def test_provision_device_missing_name(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post("/customer/devices", headers=_auth_header(), json={"site_id": "default-site"})
    assert resp.status_code == 422


async def test_apply_template_after_provision(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = {"id": 1, "name": "Rule"}
    resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["temp_high"]},
    )
    assert resp.status_code == 200
    assert "created" in resp.json()


async def test_wizard_backend_flow(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", AsyncMock(return_value=None))
    conn.fetchrow_result = {"subscription_id": "sub-1"}
    provision_resp = await client.post(
        "/customer/devices",
        headers=_auth_header(),
        json={"device_id": "DEV-2", "site_id": "default-site"},
    )
    assert provision_resp.status_code == 201

    conn.fetchrow_result = {"id": 2, "name": "Rule 2"}
    apply_resp = await client.post(
        "/customer/alert-rule-templates/apply",
        headers=_auth_header(),
        json={"template_ids": ["temp_high"]},
    )
    assert apply_resp.status_code == 200
