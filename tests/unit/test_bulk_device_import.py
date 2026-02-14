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
        self.fetchval_result = "sub-1"
        self.execute_calls = []
        self.executemany_calls = []

    async def fetchval(self, _query, *_args):
        return self.fetchval_result

    async def execute(self, query, *_args):
        self.execute_calls.append(query)
        return "OK"

    async def executemany(self, query, args):
        self.executemany_calls.append((query, args))
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


async def test_import_valid_csv(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(return_value={"device_id": "dev"})
    monkeypatch.setattr(customer_routes, "create_device_on_subscription", create_mock)
    csv_data = "name,device_type,site_id,tags\nsensor-a,temperature,site-1,\"a,b\"\nsensor-b,pressure,,\n"
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["failed"] == 0


async def test_import_invalid_row_missing_name(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "create_device_on_subscription", AsyncMock())
    csv_data = "name,device_type\n,temperature\n"
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["failed"] == 1
    assert body["results"][0]["status"] == "error"


async def test_import_exceeds_row_limit(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    rows = "\n".join(["sensor,temperature"] * 501)
    csv_data = f"name,device_type\n{rows}\n"
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 400


async def test_import_file_too_large(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    large = b"a" * int(1.1 * 1024 * 1024)
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", large, "text/csv")},
    )
    assert resp.status_code == 413


async def test_import_partial_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    create_mock = AsyncMock(return_value={"device_id": "dev"})
    monkeypatch.setattr(customer_routes, "create_device_on_subscription", create_mock)
    csv_data = (
        "name,device_type\n"
        "sensor-a,temperature\n"
        "sensor-b,invalid_type\n"
        "sensor-c,humidity\n"
    )
    resp = await client.post(
        "/customer/devices/import",
        headers=_auth_header(),
        files={"file": ("devices.csv", csv_data, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["failed"] == 1
