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
from services.evaluator_iot import evaluator

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.fetch_rows = []
        self.fetchrow_result = None

    async def fetch(self, _query, *_args):
        return self.fetch_rows

    async def fetchrow(self, _query, *_args):
        return self.fetchrow_result

    async def execute(self, _query, *_args):
        return "UPDATE 1"


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
    async def _grant_all(_request):
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


async def test_list_windows_returns_list(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [{"window_id": "mw-1", "name": "Nightly"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/maintenance-windows", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_create_window_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"window_id": "mw-1", "name": "Nightly"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/customer/maintenance-windows",
        headers=_auth_header(),
        json={"name": "Nightly", "starts_at": "2026-01-01T00:00:00Z"},
    )
    assert resp.status_code == 201
    assert resp.json()["window_id"] == "mw-1"


async def test_update_window_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.patch(
        "/customer/maintenance-windows/mw-missing",
        headers=_auth_header(),
        json={"name": "Updated"},
    )
    assert resp.status_code == 404


async def test_delete_window_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {"window_id": "mw-1"}
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/customer/maintenance-windows/mw-1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


async def test_is_in_maintenance_active_window():
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "window_id": "mw-1",
            "recurring": None,
            "site_ids": None,
            "device_types": None,
            "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ends_at": None,
        }
    ]
    assert await evaluator.is_in_maintenance(conn, "tenant-a", site_id="site-1", device_type="temp")


async def test_is_in_maintenance_no_windows():
    conn = FakeConn()
    conn.fetch_rows = []
    assert not await evaluator.is_in_maintenance(conn, "tenant-a")


async def test_is_in_maintenance_site_filter_miss():
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "window_id": "mw-1",
            "recurring": None,
            "site_ids": ["site-x"],
            "device_types": None,
            "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ends_at": None,
        }
    ]
    assert not await evaluator.is_in_maintenance(conn, "tenant-a", site_id="site-y")


async def test_is_in_maintenance_recurring_outside_hours(monkeypatch):
    class _FixedDatetime:
        @classmethod
        def now(cls, _tz=None):
            return datetime(2026, 1, 4, 6, 0, 0, tzinfo=timezone.utc)  # Sunday, 06:00

    monkeypatch.setattr(evaluator, "datetime", _FixedDatetime)
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "window_id": "mw-1",
            "recurring": {"dow": [0], "start_hour": 2, "end_hour": 4},
            "site_ids": None,
            "device_types": None,
            "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ends_at": None,
        }
    ]
    assert not await evaluator.is_in_maintenance(conn, "tenant-a")


async def test_is_in_maintenance_recurring_inside_hours(monkeypatch):
    class _FixedDatetime:
        @classmethod
        def now(cls, _tz=None):
            return datetime(2026, 1, 4, 3, 0, 0, tzinfo=timezone.utc)  # Sunday, 03:00

    monkeypatch.setattr(evaluator, "datetime", _FixedDatetime)
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "window_id": "mw-1",
            "recurring": {"dow": [0], "start_hour": 2, "end_hour": 4},
            "site_ids": None,
            "device_types": None,
            "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ends_at": None,
        }
    ]
    assert await evaluator.is_in_maintenance(conn, "tenant-a")
