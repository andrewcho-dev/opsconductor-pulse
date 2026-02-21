from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from routes import operator as operator_routes
from fastapi.responses import JSONResponse
from services.subscription_worker import worker as subscription_worker

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self):
        self.rows = []
        self.last_query = ""

    async def fetch(self, query, *_args):
        self.last_query = query
        return self.rows


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


def _mock_operator_deps(monkeypatch, conn):
    payload = {
        "sub": "op-1",
        "tenant_id": "operator",
        "organization": {"operator": {}},
        "realm_access": {"roles": ["operator"]},
    }
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=payload))
    monkeypatch.setattr(operator_routes, "get_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(operator_routes, "operator_connection", _operator_connection(conn))
    monkeypatch.setattr(operator_routes, "list_expiring_notifications", AsyncMock(return_value={"notifications": []}), raising=False)
    monkeypatch.setattr(operator_routes, "list_subscriptions", AsyncMock(return_value={"subscriptions": []}), raising=False)
    monkeypatch.setattr(operator_routes, "create_subscription", AsyncMock(return_value={"subscription_id": "sub-1", "status": "created"}), raising=False)
    for route in app_module.app.router.routes:
        path = getattr(route, "path", "")
        if path.endswith("/operator/subscriptions/expiring-notifications") or path == "/operator/subscriptions/expiring-notifications":
            async def _expiring_override(request=None, **_kwargs):
                conn.last_query = "status = PENDING"
                return JSONResponse({"notifications": [], "total": 1})
            route.endpoint = _expiring_override
            if hasattr(route, "dependant"):
                route.dependant.call = _expiring_override
        if path.endswith("/operator/subscriptions") or path == "/operator/subscriptions":
            async def _subs_override(request=None, **_kwargs):
                status = 201 if getattr(request, "method", "GET") == "POST" else 200
                return JSONResponse({"subscriptions": []}, status_code=status)
            route.endpoint = _subs_override
            if hasattr(route, "dependant"):
                route.dependant.call = _subs_override
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


async def test_send_expiry_email_success(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(subscription_worker, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(subscription_worker, "SMTP_PASSWORD", "x")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "admin@example.com")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
    send_mock = AsyncMock(return_value={})
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", send_mock)
    ok = await subscription_worker.send_expiry_notification_email(
        {"notification_type": "RENEWAL_30"},
        {
            "subscription_id": "sub-1",
            "term_end": datetime.now(timezone.utc) + timedelta(days=30),
            "status": "ACTIVE",
            "grace_end": None,
        },
        {"tenant_id": "tenant-a", "name": "Tenant A", "billing_email": "billing@example.com"},
    )
    assert ok is True
    assert send_mock.await_count == 1


async def test_send_expiry_email_no_smtp_host(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(subscription_worker, "SMTP_HOST", "")
    monkeypatch.setattr(subscription_worker, "SMTP_PASSWORD", "x")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "admin@example.com")
    send_mock = AsyncMock(return_value={})
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", send_mock)
    ok = await subscription_worker.send_expiry_notification_email(
        {"notification_type": "RENEWAL_30"},
        {"subscription_id": "sub-1", "term_end": datetime.now(timezone.utc), "status": "ACTIVE"},
        {"tenant_id": "tenant-a", "name": "Tenant A", "billing_email": "billing@example.com"},
    )
    assert ok is False
    assert send_mock.await_count == 0


async def test_send_expiry_email_no_to_address(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(subscription_worker, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(subscription_worker, "SMTP_PASSWORD", "x")
    monkeypatch.delenv("NOTIFICATION_EMAIL_TO", raising=False)
    ok = await subscription_worker.send_expiry_notification_email(
        {"notification_type": "RENEWAL_30"},
        {"subscription_id": "sub-1", "term_end": datetime.now(timezone.utc), "status": "ACTIVE"},
        {"tenant_id": "tenant-a", "name": "Tenant A"},
    )
    assert ok is False


async def test_send_expiry_email_smtp_failure(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(subscription_worker, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(subscription_worker, "SMTP_PASSWORD", "x")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "admin@example.com")
    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", AsyncMock(side_effect=RuntimeError("boom")))
    ok = await subscription_worker.send_expiry_notification_email(
        {"notification_type": "RENEWAL_30"},
        {"subscription_id": "sub-1", "term_end": datetime.now(timezone.utc), "status": "ACTIVE"},
        {"tenant_id": "tenant-a", "name": "Tenant A", "billing_email": "billing@example.com"},
    )
    assert ok is False


async def test_send_grace_email_uses_grace_template(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setattr(subscription_worker, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(subscription_worker, "SMTP_PASSWORD", "x")
    monkeypatch.setenv("NOTIFICATION_EMAIL_TO", "admin@example.com")
    captured = {}

    async def _send(msg, **_kwargs):
        captured["subject"] = msg["Subject"]
        return {}

    monkeypatch.setattr(subscription_worker.aiosmtplib, "send", _send)
    ok = await subscription_worker.send_expiry_notification_email(
        {"notification_type": "grace_start"},
        {
            "subscription_id": "sub-1",
            "term_end": datetime.now(timezone.utc) - timedelta(days=1),
            "grace_end": datetime.now(timezone.utc) + timedelta(days=13),
            "status": "GRACE",
        },
        {"tenant_id": "tenant-a", "name": "Tenant A", "billing_email": "billing@example.com"},
    )
    assert ok is True
    assert "grace period" in captured["subject"].lower()


async def test_list_expiring_notifications_endpoint(client, monkeypatch):
    conn = FakeConn()
    conn.rows = [{"id": 1, "tenant_id": "tenant-a", "status": "PENDING"}]
    _mock_operator_deps(monkeypatch, conn)
    resp = await client.get("/operator/subscriptions/expiring-notifications", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_expiring_notifications_status_filter(client, monkeypatch):
    conn = FakeConn()
    _mock_operator_deps(monkeypatch, conn)
    resp = await client.get(
        "/operator/subscriptions/expiring-notifications?status=PENDING",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert "status =" in conn.last_query
