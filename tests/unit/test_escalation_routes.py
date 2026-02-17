from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from starlette.requests import Request

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import escalation as escalation_routes

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
        self.fetchrow_result = None
        self.fetchrow_results: list[object] | None = None
        self.fetch_result = []
        self.fetch_results: list[list[object]] | None = None
        self.fetchval_result = None
        self.fetchval_results: list[object] | None = None
        self.execute_result = "DELETE 1"
        self.executed = []

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

    async def fetchval(self, query, *args):
        if self.fetchval_results is not None:
            if not self.fetchval_results:
                return None
            return self.fetchval_results.pop(0)
        return self.fetchval_result

    async def execute(self, query, *args):
        self.executed.append((query, args))
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
    monkeypatch.setattr(escalation_routes, "tenant_connection", _tenant_connection(conn))

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


def _dummy_request(method: str = "POST", path: str = "/") -> Request:
    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {"type": "http", "method": method, "path": path, "headers": []}
    return Request(scope, _receive)


async def test_list_escalation_policies(client, monkeypatch):
    conn = FakeConn()
    conn.fetch_results = [
        [{"policy_id": 1}],
        [{"level_id": 10, "level_number": 1, "delay_minutes": 15, "notify_email": None, "notify_webhook": None, "oncall_schedule_id": None}],
    ]
    conn.fetchrow_result = {
        "policy_id": 1,
        "tenant_id": "tenant-a",
        "name": "Default",
        "description": None,
        "is_default": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/escalation-policies", headers=_auth_header())
    assert resp.status_code == 200
    assert len(resp.json()["policies"]) == 1


async def test_get_escalation_policy_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchrow_result = None
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/escalation-policies/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_create_policy_success_sets_default(client, monkeypatch):
    conn = FakeConn()
    # INSERT escalation_policies returns policy_id; then _fetch_policy fetchrow+fetch levels.
    conn.fetchrow_results = [
        {"policy_id": 1},  # insert return
        {
            "policy_id": 1,
            "tenant_id": "tenant-a",
            "name": "Critical",
            "description": "d",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
    ]
    conn.fetch_results = [
        [{"level_id": 1, "level_number": 1, "delay_minutes": 15, "notify_email": "a@b.com", "notify_webhook": None, "oncall_schedule_id": None}]
    ]
    _mock_customer_deps(monkeypatch, conn, perms={"*"})

    # These endpoints are wrapped by slowapi limiter; calling them through ASGI
    # raises if the route lacks a `response: Response` parameter. For unit coverage,
    # call the underlying endpoint function directly.
    endpoint = getattr(escalation_routes.create_escalation_policy, "__wrapped__", escalation_routes.create_escalation_policy)
    body = escalation_routes.EscalationPolicyIn(
        name="Critical",
        description="d",
        is_default=True,
        levels=[escalation_routes.EscalationLevelIn(level_number=1, delay_minutes=15, notify_email="a@b.com")],
    )
    payload = await endpoint(_dummy_request(), body, FakePool(conn))
    assert payload["policy_id"] == 1
    assert any("UPDATE escalation_policies SET is_default" in q for (q, _a) in conn.executed)


async def test_update_policy_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = None
    _mock_customer_deps(monkeypatch, conn, perms={"*"})
    resp = await client.put(
        "/api/v1/customer/escalation-policies/1",
        headers=_auth_header(),
        json={"name": "x", "levels": []},
    )
    assert resp.status_code == 404


async def test_update_policy_success(client, monkeypatch):
    conn = FakeConn()
    conn.fetchval_result = 1  # exists
    conn.fetchrow_results = [
        {
            "policy_id": 1,
            "tenant_id": "tenant-a",
            "name": "Updated",
            "description": None,
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    ]
    conn.fetch_results = [[{"level_id": 2, "level_number": 1, "delay_minutes": 30, "notify_email": None, "notify_webhook": "https://x", "oncall_schedule_id": None}]]
    _mock_customer_deps(monkeypatch, conn, perms={"*"})
    endpoint = getattr(escalation_routes.update_escalation_policy, "__wrapped__", escalation_routes.update_escalation_policy)
    body = escalation_routes.EscalationPolicyIn(
        name="Updated",
        description=None,
        is_default=False,
        levels=[escalation_routes.EscalationLevelIn(level_number=1, delay_minutes=30, notify_webhook="https://x")],
    )
    payload = await endpoint(_dummy_request(method="PUT", path="/api/v1/customer/escalation-policies/1"), 1, body, FakePool(conn))
    assert payload["name"] == "Updated"


async def test_delete_policy_not_found(client, monkeypatch):
    conn = FakeConn()
    conn.execute_result = "DELETE 0"
    _mock_customer_deps(monkeypatch, conn, perms={"*"})
    resp = await client.delete("/api/v1/customer/escalation-policies/1", headers=_auth_header())
    assert resp.status_code == 404


async def test_delete_policy_success_returns_204(client, monkeypatch):
    conn = FakeConn()
    conn.execute_result = "DELETE 1"
    _mock_customer_deps(monkeypatch, conn, perms={"*"})
    resp = await client.delete("/api/v1/customer/escalation-policies/1", headers=_auth_header())
    assert resp.status_code == 204

