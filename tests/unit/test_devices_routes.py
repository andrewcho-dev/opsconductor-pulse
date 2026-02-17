from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

import app as app_module
import dependencies as dependencies_module
from middleware import auth as auth_module
from middleware import permissions as permissions_module
from middleware import tenant as tenant_module
from routes import devices as devices_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    # Override the integration DB bootstrap fixture from tests/conftest.py
    # so this file remains pure unit tests.
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
        self.fetchval_result = 0
        self.executed = []

    async def fetchrow(self, query, *args):
        if self.fetchrow_results is not None:
            if not self.fetchrow_results:
                return None
            return self.fetchrow_results.pop(0)
        return self.fetchrow_result

    async def fetch(self, query, *args):
        return self.fetch_result

    async def fetchval(self, query, *args):
        return self.fetchval_result

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "OK"

    async def executemany(self, query, args):
        self.executed.append((query, tuple(args)))
        return None

    def transaction(self):
        return _Tx()


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


def _mock_customer_deps(monkeypatch, conn: FakeConn, tenant_id: str = "tenant-a"):
    user_payload = {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": ["customer", "tenant-admin"]},
        "email": "u@example.com",
    }
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(auth_module, "validate_token", AsyncMock(return_value=user_payload))

    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(devices_routes, "tenant_connection", _tenant_connection(conn))

    async def _allow_all(_request):
        permissions_module.permissions_context.set({"*"})
        return None

    monkeypatch.setattr(permissions_module, "inject_permissions", AsyncMock(side_effect=_allow_all))
    # Some endpoints are slowapi-decorated but don't accept a `response` parameter.
    # In unit tests we don't care about rate-limit headers; avoid strict checks,
    # but always return the response so Starlette middleware doesn't break.
    monkeypatch.setattr(
        devices_routes.limiter, "_inject_headers", lambda response, *args, **kwargs: response
    )


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.cookies.set("csrf_token", "csrf")
        yield c
    app_module.app.dependency_overrides.clear()


async def test_devices_requires_auth(client):
    resp = await client.get("/api/v1/customer/devices")
    assert resp.status_code == 401


async def test_list_devices_returns_paginated(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    devices = [{"device_id": "d1"}, {"device_id": "d2"}]
    monkeypatch.setattr(
        devices_routes,
        "fetch_devices_v2",
        AsyncMock(return_value={"devices": devices, "total": 2}),
    )
    conn.fetch_result = [
        {"device_id": "d1", "subscription_id": "s1", "subscription_type": "MAIN", "subscription_status": "ACTIVE"},
        {"device_id": "d2", "subscription_id": "s1", "subscription_type": "MAIN", "subscription_status": "ACTIVE"},
    ]

    resp = await client.get("/api/v1/customer/devices?limit=50&offset=0", headers=_auth_header())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["devices"]) == 2


async def test_list_devices_with_search_filter(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    async def _fake_fetch(conn, tenant_id, **kwargs):
        assert kwargs.get("q") == "sensor"
        return {"devices": [{"device_id": "sensor-01"}], "total": 1}

    monkeypatch.setattr(devices_routes, "fetch_devices_v2", AsyncMock(side_effect=_fake_fetch))

    resp = await client.get("/api/v1/customer/devices?search=sensor", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_devices_page_beyond_total(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        devices_routes,
        "fetch_devices_v2",
        AsyncMock(return_value={"devices": [], "total": 5}),
    )

    resp = await client.get("/api/v1/customer/devices?page=100&limit=50", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["devices"] == []


async def test_list_devices_invalid_limit(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/api/v1/customer/devices?limit=-1", headers=_auth_header())
    assert resp.status_code == 422


async def test_get_device_detail_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(devices_routes, "fetch_device_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(devices_routes, "fetch_device_telemetry", AsyncMock(return_value=[]))
    conn.fetchrow_result = {"tier_id": 1, "tier_name": "basic", "tier_display_name": "Basic"}

    resp = await client.get("/api/v1/customer/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


async def test_get_device_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "fetch_device", AsyncMock(return_value=None))
    resp = await client.get("/api/v1/customer/devices/nonexistent", headers=_auth_header())
    assert resp.status_code == 404


async def test_create_device_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    monkeypatch.setattr(
        devices_routes,
        "check_device_limit",
        AsyncMock(return_value={"allowed": True, "status_code": 200, "message": ""}),
    )
    monkeypatch.setattr(devices_routes, "create_device_on_subscription", AsyncMock(return_value=None))
    conn.fetchrow_result = {"subscription_id": "sub-1"}

    resp = await client.post(
        "/api/v1/customer/devices",
        headers=_auth_header(),
        json={"device_id": "new-device", "site_id": "site-1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_id"] == "new-device"
    assert body["subscription_id"] == "sub-1"


async def test_create_device_over_limit(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)

    monkeypatch.setattr(
        devices_routes,
        "check_device_limit",
        AsyncMock(return_value={"allowed": False, "status_code": 402, "message": "Upgrade"}),
    )

    resp = await client.post(
        "/api/v1/customer/devices",
        headers=_auth_header(),
        json={"device_id": "new-device", "site_id": "site-1"},
    )
    assert resp.status_code == 402


async def test_update_device_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = {"tenant_id": "tenant-a", "device_id": "d1"}
    monkeypatch.setattr(devices_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1", "model": "DHT22-v2"}))

    resp = await client.patch(
        "/api/v1/customer/devices/d1",
        headers=_auth_header(),
        json={"model": "DHT22-v2"},
    )
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


async def test_delete_device_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = {"subscription_id": None}
    monkeypatch.setattr(devices_routes, "log_subscription_event", AsyncMock(return_value=None))

    resp = await client.delete("/api/v1/customer/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device_id"] == "d1"


async def test_delete_device_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None

    resp = await client.delete("/api/v1/customer/devices/missing", headers=_auth_header())
    assert resp.status_code == 404


async def test_list_device_tiers(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetch_result = [
        {"tier_id": 1, "name": "basic", "display_name": "Basic", "description": "", "features": '{"x":true}'}
    ]
    resp = await client.get("/api/v1/customer/device-tiers", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["tiers"][0]["tier_id"] == 1
    assert body["tiers"][0]["features"]["x"] is True


async def test_assign_device_tier(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_results = [
        {"device_id": "d1", "subscription_id": "sub-1", "tier_id": None},  # device
        {"tier_id": 2, "name": "premium", "display_name": "Premium"},  # tier
        {"slot_limit": 10, "slots_used": 0},  # allocation
    ]

    resp = await client.put(
        "/api/v1/customer/devices/d1/tier",
        headers=_auth_header(),
        json={"tier_id": 2},
    )
    assert resp.status_code == 200
    assert resp.json()["tier_id"] == 2


async def test_remove_device_tier(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_results = [
        {"device_id": "d1", "subscription_id": "sub-1", "tier_id": 2},  # device
    ]
    resp = await client.delete("/api/v1/customer/devices/d1/tier", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["tier_id"] is None


async def test_list_device_tokens_filters_revoked(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchval_result = 1  # device exists
    conn.fetch_result = [
        {"id": "t1", "client_id": "c1", "label": "ok", "created_at": "x", "revoked_at": None},
        {"id": "t2", "client_id": "c2", "label": "revoked", "created_at": "x", "revoked_at": "2026-01-01"},
    ]
    resp = await client.get("/api/v1/customer/devices/d1/tokens", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["tokens"][0]["client_id"] == "c1"


async def test_revoke_device_token_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None
    resp = await client.delete(
        "/api/v1/customer/devices/d1/tokens/00000000-0000-0000-0000-000000000000",
        headers=_auth_header(),
    )
    assert resp.status_code == 404


async def test_get_device_telemetry_points_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        devices_routes,
        "fetch_device_telemetry",
        AsyncMock(return_value=[{"time": "t1", "metrics": {"temp_c": 1}}]),
    )
    resp = await client.get("/api/v1/customer/devices/d1/telemetry?hours=1&limit=1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_get_device_telemetry_points_invalid_start_end(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/api/v1/customer/devices/d1/telemetry?start=not-a-time",
        headers=_auth_header(),
    )
    assert resp.status_code == 400


async def test_get_telemetry_history_invalid_range(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get(
        "/api/v1/customer/devices/d1/telemetry/history?metric=temp_c&range=999h",
        headers=_auth_header(),
    )
    assert resp.status_code == 400


async def test_jsonb_to_dict_parses_string_and_handles_invalid(monkeypatch):
    assert devices_routes._jsonb_to_dict({"a": 1}) == {"a": 1}
    assert devices_routes._jsonb_to_dict('{"a": 1}') == {"a": 1}
    assert devices_routes._jsonb_to_dict("{not json") == {}


async def test_publish_shadow_desired_success(monkeypatch):
    ok_result = SimpleNamespace(success=True, error=None)
    monkeypatch.setattr(devices_routes, "publish_alert", AsyncMock(return_value=ok_result))
    await devices_routes._publish_shadow_desired("tenant-a", "d1", {"x": 1}, desired_version=1)


async def test_clear_shadow_desired_retained_failure(monkeypatch):
    bad_result = SimpleNamespace(success=False, error="nope")
    monkeypatch.setattr(devices_routes, "publish_alert", AsyncMock(return_value=bad_result))
    await devices_routes._clear_shadow_desired_retained("tenant-a", "d1")
