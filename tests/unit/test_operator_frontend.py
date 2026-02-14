from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from routes import operator as operator_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    async def fetch(self, query, *args, **kwargs):
        if "FROM tenants" in query:
            return [
                {
                    "tenant_id": "tenant-a",
                    "name": "Tenant A",
                    "status": "ACTIVE",
                    "contact_email": None,
                    "contact_name": None,
                    "metadata": {},
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        if "FROM subscriptions" in query:
            return [
                {
                    "subscription_id": "sub-1",
                    "tenant_id": "tenant-a",
                    "tenant_name": "Tenant A",
                    "subscription_type": "MAIN",
                    "parent_subscription_id": None,
                    "device_limit": 100,
                    "active_device_count": 0,
                    "term_start": datetime.now(timezone.utc),
                    "term_end": datetime.now(timezone.utc),
                    "status": "ACTIVE",
                    "plan_id": None,
                    "description": None,
                    "created_at": None,
                }
            ]
        if "FROM audit_log" in query:
            return [{"id": 1, "tenant_id": "tenant-a", "action": "x", "created_at": None}]
        return []

    async def fetchrow(self, query, *args, **kwargs):
        if "SELECT tenant_id, name, status FROM tenants WHERE tenant_id = $1" in query:
            return {"tenant_id": "tenant-a", "name": "Tenant A", "status": "ACTIVE"}
        if "INSERT INTO subscriptions" in query and "RETURNING" in query:
            return {
                "subscription_id": "sub-1",
                "tenant_id": "tenant-a",
                "subscription_type": "TRIAL",
                "parent_subscription_id": None,
                "device_limit": 10,
                "active_device_count": 0,
                "term_start": datetime.now(timezone.utc),
                "term_end": datetime.now(timezone.utc),
                "status": "ACTIVE",
                "plan_id": None,
                "description": None,
                "created_by": "operator-1",
                "created_at": datetime.now(timezone.utc),
            }
        if "SELECT" in query and "AS total_devices" in query:
            return {
                "total_devices": 1,
                "active_devices": 1,
                "online_devices": 1,
                "stale_devices": 0,
                "open_alerts": 0,
                "closed_alerts": 0,
                "alerts_24h": 0,
                "total_integrations": 0,
                "active_integrations": 0,
                "total_rules": 0,
                "active_rules": 0,
                "last_device_activity": None,
                "last_alert_created": None,
                "site_count": 1,
            }
        if "FROM tenants t" in query:
            return {
                "tenant_id": "tenant-a",
                "name": "Tenant A",
                "status": "ACTIVE",
                "device_total": 1,
                "device_active": 1,
                "device_online": 1,
                "device_stale": 0,
                "alerts_open": 0,
                "alerts_closed": 0,
                "alerts_last_24h": 0,
                "integrations_total": 0,
                "integrations_active": 0,
                "rules_total": 0,
                "rules_active": 0,
                "site_count": 1,
                "last_device_activity": None,
                "last_alert": None,
            }
        return None

    async def fetchval(self, query, *args, **kwargs):
        if "COUNT(*) FROM tenants" in query:
            return 1
        if "COUNT(*) FROM subscriptions" in query:
            return 1
        if "COUNT(*) FROM audit_log" in query:
            return 1
        if "SELECT 1 FROM tenants WHERE tenant_id = $1" in query:
            return 1 if args and args[0] == "tenant-a" else None
        if "SELECT generate_subscription_id()" in query:
            return "sub-1"
        return 1

    async def execute(self, query, *args, **kwargs):
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
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_operator_deps(monkeypatch, conn, admin=False):
    roles = ["operator-admin"] if admin else ["operator"]
    user_payload = {
        "sub": "operator-1",
        "tenant_id": "tenant-a",
        "organization": {"tenant-a": {}},
        "realm_access": {"roles": roles},
    }
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))
    monkeypatch.setattr(operator_routes, "get_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(operator_routes, "operator_connection", _operator_connection(conn))
    monkeypatch.setattr(operator_routes, "log_operator_access", AsyncMock())


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c


async def test_operator_tenants_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn())
    resp = await client.get("/operator/tenants", headers=_auth_header())
    assert resp.status_code == 200
    assert "tenants" in resp.json()


async def test_operator_tenant_stats_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn())
    resp = await client.get("/operator/tenants/tenant-a/stats", headers=_auth_header())
    assert resp.status_code == 200
    assert "stats" in resp.json()


async def test_operator_subscriptions_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn())
    resp = await client.get("/operator/subscriptions", headers=_auth_header())
    assert resp.status_code == 200
    assert "subscriptions" in resp.json()


async def test_operator_audit_log_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn())
    resp = await client.get("/operator/audit-log", headers=_auth_header())
    assert resp.status_code == 200
    assert "events" in resp.json()


async def test_create_tenant_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn(), admin=True)
    resp = await client.post(
        "/operator/tenants",
        headers=_auth_header(),
        json={"tenant_id": "tenant-new", "name": "Tenant New"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "created"


async def test_create_subscription_endpoint_exists(client, monkeypatch):
    _mock_operator_deps(monkeypatch, FakeConn())
    resp = await client.post(
        "/operator/subscriptions",
        headers=_auth_header(),
        json={
            "tenant_id": "tenant-a",
            "subscription_type": "TRIAL",
            "device_limit": 10,
        },
    )
    assert resp.status_code == 201
