from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.requests import Request

import app as app_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from routes import operator as operator_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    async def fetch(self, *args, **kwargs):
        return []

    async def fetchrow(self, *args, **kwargs):
        return None

    async def fetchval(self, *args, **kwargs):
        return None

    async def execute(self, *args, **kwargs):
        return "OK"


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _operator_connection(conn):
    @asynccontextmanager
    async def _ctx(_pool):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token"}


def _mock_user_payload(role: str) -> dict:
    role_map = {
        "operator": ["operator"],
        "operator_admin": ["operator-admin"],
        "customer_admin": ["customer", "tenant-admin"],
    }
    return {
        "sub": "operator-1",
        "tenant_id": "tenant-a",
        "organization": {"tenant-a": {}},
        "realm_access": {"roles": role_map.get(role, [role])},
    }


def _mock_operator_deps(monkeypatch, conn, role="operator"):
    user_payload = _mock_user_payload(role)
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(return_value=user_payload),
    )
    monkeypatch.setattr(operator_routes, "get_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(operator_routes, "operator_connection", _operator_connection(conn))
    monkeypatch.setattr(operator_routes, "list_subscriptions", AsyncMock(return_value={"subscriptions": []}), raising=False)
    monkeypatch.setattr(operator_routes, "create_subscription", AsyncMock(return_value={"subscription_id": "sub-1", "status": "created"}), raising=False)
    async def _grant_all(_request):
        permissions_module.permissions_context.set({"*"})
    monkeypatch.setattr(permissions_module, "inject_permissions", _grant_all)
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
    ) as client:
        yield client


async def test_operator_list_all_devices(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_all_devices", AsyncMock(return_value=[{"device_id": "d1", "tenant_id": "tenant-a"}]))

    resp = await client.get("/operator/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["devices"][0]["device_id"] == "d1"


async def test_operator_filter_by_tenant(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    fetch_devices = AsyncMock(return_value=[{"device_id": "d2", "tenant_id": "tenant-a"}])
    fetch_all_devices = AsyncMock(return_value=[{"device_id": "d1", "tenant_id": "tenant-a"}])
    monkeypatch.setattr(operator_routes, "fetch_devices", fetch_devices)
    monkeypatch.setattr(operator_routes, "fetch_all_devices", fetch_all_devices)

    resp = await client.get("/operator/devices?tenant_filter=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["devices"][0]["device_id"] == "d2"
    fetch_devices.assert_awaited()
    fetch_all_devices.assert_not_awaited()


async def test_operator_audit_logged(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    log_access = AsyncMock()
    monkeypatch.setattr(operator_routes, "log_operator_access", log_access)
    monkeypatch.setattr(operator_routes, "fetch_all_devices", AsyncMock(return_value=[]))

    resp = await client.get("/operator/devices", headers=_auth_header())
    assert resp.status_code == 200
    log_access.assert_awaited()


async def test_operator_audit_log_requires_admin(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")

    resp = await client.get("/operator/audit-log", headers=_auth_header())
    assert resp.status_code == 200


async def test_customer_cannot_access_operator(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="customer_admin")

    resp = await client.get("/operator/devices", headers=_auth_header())
    assert resp.status_code == 403


async def test_operator_list_alerts_all(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_all_alerts", AsyncMock(return_value=[{"alert_id": "a1"}]))

    resp = await client.get("/operator/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["alert_id"] == "a1"


async def test_operator_list_alerts_filtered(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_alerts", AsyncMock(return_value=[{"alert_id": "a2"}]))

    resp = await client.get("/operator/alerts?tenant_filter=tenant-a", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alerts"][0]["alert_id"] == "a2"


async def test_operator_list_quarantine(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_quarantine_events", AsyncMock(return_value=[{"reason": "RATE_LIMITED"}]))

    resp = await client.get("/operator/quarantine", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["events"][0]["reason"] == "RATE_LIMITED"






async def test_operator_view_device_json(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn, role="operator")
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())
    monkeypatch.setattr(operator_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(operator_routes, "fetch_device_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(operator_routes, "fetch_device_telemetry", AsyncMock(return_value=[]))

    resp = await client.get("/operator/tenants/tenant-a/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


async def test_operator_helpers():
    req = Request({"type": "http", "headers": []})
    ip, user_agent = operator_routes.get_request_metadata(req)
    assert ip is None
    assert user_agent is None
