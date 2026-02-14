import os
import sys
import importlib.util
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module

services_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "delivery_worker"
)
sys.path.insert(0, services_dir)
email_sender_spec = importlib.util.spec_from_file_location(
    "delivery_worker_email_sender",
    os.path.join(services_dir, "email_sender.py"),
)
assert email_sender_spec and email_sender_spec.loader
email_sender = importlib.util.module_from_spec(email_sender_spec)
email_sender_spec.loader.exec_module(email_sender)

worker_spec = importlib.util.spec_from_file_location(
    "delivery_worker_worker",
    os.path.join(services_dir, "worker.py"),
)
assert worker_spec and worker_spec.loader
worker = importlib.util.module_from_spec(worker_spec)
worker_spec.loader.exec_module(worker)

pytestmark = pytest.mark.unit


class FakeConn:
    def __init__(self, row=None):
        self.row = row

    async def fetchrow(self, _query, *_args):
        return self.row


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
    from routes import customer as customer_routes

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


def test_render_template_basic():
    out = email_sender.render_template("Hello {{ name }}", {"name": "World"})
    assert out == "Hello World"


def test_render_template_all_vars():
    out = email_sender.render_template(
        "{{ alert_id }} {{ device_id }} {{ site_id }} {{ tenant_id }} {{ severity }} "
        "{{ severity_label }} {{ alert_type }} {{ summary }} {{ status }} {{ created_at }} {{ details }}",
        {
            "alert_id": 1,
            "device_id": "dev-1",
            "site_id": "site-1",
            "tenant_id": "tenant-a",
            "severity": 2,
            "severity_label": "WARNING",
            "alert_type": "THRESHOLD",
            "summary": "Temp high",
            "status": "OPEN",
            "created_at": "2026-01-01T00:00:00Z",
            "details": {"x": 1},
        },
    )
    assert "dev-1" in out
    assert "WARNING" in out


def test_render_template_error_fallback():
    bad = "{{ broken "
    out = email_sender.render_template(bad, {"name": "X"})
    assert out == bad


def test_render_template_missing_var():
    out = email_sender.render_template("Hello {{ missing }}", {})
    assert out == "Hello "


def test_severity_label_mapping():
    assert email_sender.severity_label_for(0) == "CRITICAL"
    assert email_sender.severity_label_for(2) == "WARNING"
    assert email_sender.severity_label_for(3) == "INFO"


@pytest.mark.asyncio
async def test_webhook_uses_body_template_when_set():
    integration = {
        "config_json": {
            "url": "https://example.com/hook",
            "body_template": '{"summary":"{{ summary }}","status":"{{ status }}"}',
        }
    }
    job = {"payload_json": {"summary": "Alert high", "status": "OPEN", "severity": 2}}
    post = AsyncMock(return_value=type("Resp", (), {"status_code": 200})())
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=post))),
    ):
        ok, status, _ = await worker.deliver_webhook(integration, job)
    assert ok is True
    assert status == 200
    assert post.call_args.kwargs["json"] == {"summary": "Alert high", "status": "OPEN"}


@pytest.mark.asyncio
async def test_webhook_skips_body_template_when_absent():
    payload = {"summary": "Raw payload"}
    integration = {"config_json": {"url": "https://example.com/hook"}}
    job = {"payload_json": payload}
    post = AsyncMock(return_value=type("Resp", (), {"status_code": 200})())
    with patch.object(worker, "validate_url", return_value=(True, "ok")), patch(
        "worker.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=post))),
    ):
        ok, status, _ = await worker.deliver_webhook(integration, job)
    assert ok is True
    assert status == 200
    assert post.call_args.kwargs["json"] == payload
