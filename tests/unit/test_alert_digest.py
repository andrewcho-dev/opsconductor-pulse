from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
from middleware import permissions as permissions_module
from routes import customer as customer_routes
from services.subscription_worker import worker as subscription_worker

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
subscription_worker.SMTP_HOST = "smtp.example.com"


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_rows = []
        self.execute_calls = []

    async def fetchrow(self, query, *_args):
        if "FROM fleet_alert" in query:
            return {
                "critical_count": 1,
                "high_count": 1,
                "medium_count": 0,
                "low_count": 0,
                "total_count": 2,
            }
        return self.fetchrow_result

    async def fetch(self, _query, *_args):
        return self.fetch_rows

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
    ) as c:
        c.cookies.set("csrf_token", "csrf")
        from middleware import permissions as perm_mod
        async def _grant(req): perm_mod.permissions_context.set({"*"})
        app_module.app.dependency_overrides[perm_mod.inject_permissions] = _grant
        yield c
    app_module.app.dependency_overrides.clear()


async def test_get_digest_settings_returns_default(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/alert-digest-settings", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["frequency"] == "daily"
    assert resp.json()["email"] == ""


async def test_put_digest_settings_upserts(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put(
        "/customer/alert-digest-settings",
        headers=_auth_header(),
        json={"frequency": "weekly", "email": "ops@example.com"},
    )
    assert resp.status_code == 200
    assert any("INSERT INTO alert_digest_settings" in q for q in conn.execute_calls)


async def test_digest_job_skips_disabled(monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "tenant_id": "tenant-a",
            "frequency": "disabled",
            "email": "ops@example.com",
            "last_sent_at": None,
        }
    ]
    send_mock = AsyncMock()
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", send_mock)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    await subscription_worker.send_alert_digest(FakePool(conn))
    assert send_mock.await_count == 0


async def test_digest_job_sends_when_due(monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "tenant_id": "tenant-a",
            "frequency": "daily",
            "email": "ops@example.com",
            "last_sent_at": datetime.now(timezone.utc) - timedelta(days=2),
        }
    ]
    send_mock = AsyncMock()
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", send_mock)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    await subscription_worker.send_alert_digest(FakePool(conn))
    assert send_mock.await_count == 1


async def test_digest_job_skips_if_not_due(monkeypatch):
    conn = FakeConn()
    conn.fetch_rows = [
        {
            "tenant_id": "tenant-a",
            "frequency": "daily",
            "email": "ops@example.com",
            "last_sent_at": datetime.now(timezone.utc) - timedelta(hours=12),
        }
    ]
    send_mock = AsyncMock()
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", send_mock)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    await subscription_worker.send_alert_digest(FakePool(conn))
    assert send_mock.await_count == 0
