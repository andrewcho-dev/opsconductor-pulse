from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import notifications as notifications_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Keep this file pure unit tests (override integration DB bootstrap fixture).
    yield


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeConn:
    def __init__(self):
        self.fetchrow_results: list[object] | None = None
        self.fetch_results: list[list[object]] | None = None
        self.fetchrow_result = None
        self.fetch_result = []
        self.execute_result = "DELETE 1"

    async def fetchrow(self, query, *args):
        if self.fetchrow_results is not None:
            if not self.fetchrow_results:
                return None
            return self.fetchrow_results.pop(0)
        return self.fetchrow_result

    async def fetch(self, query, *args):
        if self.fetch_results is not None:
            if not self.fetch_results:
                return []
            return self.fetch_results.pop(0)
        return self.fetch_result

    async def execute(self, query, *args):
        return self.execute_result

    def transaction(self):
        return _Tx()


class FakePool:
    def __init__(self, conn: FakeConn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _tenant_connection(conn: FakeConn):
    @asynccontextmanager
    async def _ctx(_pool, _tenant_id):
        yield conn

    return _ctx


def _auth_header():
    return {"Authorization": "Bearer test-token", "X-CSRF-Token": "csrf"}


def _mock_customer_deps(monkeypatch, conn: FakeConn, *, tenant_id: str = "tenant-a", perms: set[str] | None = None):
    user_payload = {
        "sub": "user-1",
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
        "email": "u@example.com",
        "preferred_username": "me",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(notifications_routes, "tenant_connection", _tenant_connection(conn))

    if perms is None:
        perms = {"*"}

    async def _inject(_request):
        permissions_module.permissions_context.set(set(perms))
        return None

    monkeypatch.setattr(permissions_module, "inject_permissions", AsyncMock(side_effect=_inject))


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_list_channels_masks_config(client, monkeypatch):
    now = datetime.now(timezone.utc)
    conn = FakeConn()
    conn.fetch_result = [
        {
            "channel_id": 1,
            "tenant_id": "tenant-a",
            "name": "Slack",
            "channel_type": "slack",
            "config": {"webhook_url": "https://hooks.slack/test"},
            "is_enabled": True,
            "created_at": now,
            "updated_at": now,
        }
    ]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/notification-channels", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["channels"][0]["config"]["webhook_url"] == "***"


async def test_create_channel_missing_required_config_returns_422(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/notification-channels",
        headers=_auth_header(),
        json={"name": "Slack", "channel_type": "slack", "config": {}},
    )
    assert resp.status_code == 422


async def test_create_channel_success(client, monkeypatch):
    now = datetime.now(timezone.utc)
    conn = FakeConn()
    conn.fetchrow_result = {
        "channel_id": 1,
        "tenant_id": "tenant-a",
        "name": "Test Channel",
        "channel_type": "webhook",
        "config": {"url": "https://hooks.example.com/test", "secret": "shh"},
        "is_enabled": True,
        "created_at": now,
        "updated_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/notification-channels",
        headers=_auth_header(),
        json={
            "name": "Test Channel",
            "channel_type": "webhook",
            "config": {"url": "https://hooks.example.com/test", "secret": "shh"},
            "is_enabled": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["config"]["secret"] == "***"


async def test_get_channel_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/notification-channels/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_update_channel_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put(
        "/api/v1/customer/notification-channels/1",
        headers=_auth_header(),
        json={"name": "n", "channel_type": "webhook", "config": {"url": "https://x"}, "is_enabled": True},
    )
    assert resp.status_code == 404


async def test_delete_channel_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.execute_result = "DELETE 0"
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/notification-channels/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_delete_channel_success_returns_204(client, monkeypatch):
    conn = FakeConn()
    conn.execute_result = "DELETE 1"
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/notification-channels/1", headers=_auth_header())
    assert resp.status_code == 204


async def test_test_channel_webhook_returns_delivery_payload(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {
        "channel_id": 1,
        "tenant_id": "tenant-a",
        "name": "W",
        "channel_type": "webhook",
        "config": {"url": "https://example.com/hook"},
        "is_enabled": True,
    }
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(notifications_routes, "send_webhook", AsyncMock(return_value={"ok": True}))

    resp = await client.post("/api/v1/customer/notification-channels/1/test", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["delivery"]["ok"] is True


async def test_test_channel_slack_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {
        "channel_id": 2,
        "tenant_id": "tenant-a",
        "name": "S",
        "channel_type": "slack",
        "config": {"webhook_url": "https://hooks.slack/test"},
        "is_enabled": True,
    }
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(notifications_routes, "send_slack", AsyncMock())

    resp = await client.post("/api/v1/customer/notification-channels/2/test", headers=_auth_header())
    assert resp.status_code == 200


async def test_test_channel_sender_error_returns_502(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = {
        "channel_id": 2,
        "tenant_id": "tenant-a",
        "name": "S",
        "channel_type": "slack",
        "config": {"webhook_url": "https://hooks.slack/test"},
        "is_enabled": True,
    }
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(notifications_routes, "send_slack", AsyncMock(side_effect=Exception("boom")))

    resp = await client.post("/api/v1/customer/notification-channels/2/test", headers=_auth_header())
    assert resp.status_code == 502


async def test_list_routing_rules(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"rule_id": 1, "tenant_id": "tenant-a", "channel_id": 1, "deliver_on": ["OPEN"], "created_at": datetime.now(timezone.utc)}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/notification-routing-rules", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["rules"]) == 1


async def test_create_routing_rule_success(client, monkeypatch):
    now = datetime.now(timezone.utc)
    conn = FakeConn()
    conn.fetchrow_result = {
        "rule_id": 1,
        "tenant_id": "tenant-a",
        "channel_id": 1,
        "min_severity": 2,
        "alert_type": None,
        "device_tag_key": None,
        "device_tag_val": None,
        "site_ids": None,
        "device_prefixes": None,
        "deliver_on": ["OPEN"],
        "throttle_minutes": 0,
        "priority": 100,
        "is_enabled": True,
        "created_at": now,
    }
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.post(
        "/api/v1/customer/notification-routing-rules",
        headers=_auth_header(),
        json={"channel_id": 1, "min_severity": 2, "deliver_on": ["OPEN"]},
    )
    assert resp.status_code == 201
    assert resp.json()["rule_id"] == 1


async def test_update_routing_rule_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.put(
        "/api/v1/customer/notification-routing-rules/1",
        headers=_auth_header(),
        json={"channel_id": 1, "min_severity": 2, "deliver_on": ["OPEN"]},
    )
    assert resp.status_code == 404


async def test_delete_routing_rule_not_found_returns_404(client, monkeypatch):
    conn = FakeConn()
    conn.execute_result = "DELETE 0"
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.delete("/api/v1/customer/notification-routing-rules/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_list_notification_jobs_filters(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_result = [{"job_id": 1, "tenant_id": "tenant-a"}]
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/api/v1/customer/notification-jobs?channel_id=1&status=QUEUED&limit=5",
        headers=_auth_header(),
    )
    assert resp.status_code == 200
    assert len(resp.json()["jobs"]) == 1

