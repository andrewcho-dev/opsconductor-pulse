from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

import app as app_module
from middleware import auth as auth_module
from middleware import tenant as tenant_module
import dependencies as dependencies_module
from routes import customer as customer_routes
from routes import devices as devices_routes

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


class FakeConn:
    def __init__(self):
        self.fetchrow_result = None
        self.fetch_result = []
        self.execute_result = "DELETE 1"

    async def fetchrow(self, *args, **kwargs):
        return self.fetchrow_result

    async def fetch(self, *args, **kwargs):
        return self.fetch_result

    async def execute(self, *args, **kwargs):
        return self.execute_result

    async def fetchval(self, *args, **kwargs):
        return 0


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


def _mock_user_payload(role: str, tenant_id: str) -> dict:
    role_map = {
        "customer_admin": ["customer", "tenant-admin"],
        "customer_viewer": ["customer"],
        "operator": ["operator"],
        "operator_admin": ["operator-admin"],
    }
    return {
        "sub": "user-1",
        "tenant_id": tenant_id,
        "organization": {tenant_id: {}},
        "realm_access": {"roles": role_map.get(role, [role])},
    }


def _mock_customer_deps(monkeypatch, conn, role="customer_admin", tenant_id="tenant-a"):
    user_payload = _mock_user_payload(role, tenant_id)
    tenant_module.set_tenant_context(tenant_id, user_payload)
    monkeypatch.setattr(
        auth_module,
        "validate_token",
        AsyncMock(return_value=user_payload),
    )
    async def _override_get_db_pool(_request=None):
        return FakePool(conn)

    app_module.app.dependency_overrides[dependencies_module.get_db_pool] = _override_get_db_pool
    monkeypatch.setattr(customer_routes, "get_db_pool", AsyncMock(return_value=FakePool(conn)))
    monkeypatch.setattr(customer_routes, "tenant_connection", _tenant_connection(conn))


def _mock_async_client(response=None, exc=None):
    context = AsyncMock()
    client = AsyncMock()
    if exc is not None:
        client.post.side_effect = exc
        client.get.side_effect = exc
    else:
        client.post.return_value = response
        client.get.return_value = response
    context.__aenter__.return_value = client
    return context


@pytest.fixture
async def client():
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("csrf_token", "csrf")
        yield client


async def test_devices_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        devices_routes,
        "fetch_devices_v2",
        AsyncMock(return_value={"devices": [], "total": 0}),
    )

    resp = await client.get("/customer/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]


async def test_list_devices_endpoint_returns_total(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        devices_routes,
        "fetch_devices_v2",
        AsyncMock(
            return_value={
                "devices": [{"device_id": "d1", "site_id": "s1", "status": "ONLINE"}],
                "total": 42,
            }
        ),
    )
    conn.fetch_result = []

    resp = await client.get("/customer/devices", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["total"] == 42


async def test_list_devices_invalid_status_returns_400(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    resp = await client.get("/customer/devices?status=INVALID", headers=_auth_header())
    assert resp.status_code == 400


async def test_fleet_summary_endpoint(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(
        devices_routes,
        "fetch_fleet_summary",
        AsyncMock(return_value={"ONLINE": 5, "STALE": 2, "OFFLINE": 1, "total": 8}),
    )

    resp = await client.get("/customer/devices/summary", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["ONLINE"] == 5
    assert resp.json()["total"] == 8


async def test_alerts_json_format(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_alerts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/alerts", headers=_auth_header())
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]












































async def test_unauthenticated_rejected(client):
    resp = await client.get("/customer/devices")
    assert resp.status_code == 401


async def test_helpers_and_normalizers():
    assert customer_routes._validate_name(" Valid ") == "Valid"
    with pytest.raises(HTTPException):
        customer_routes._validate_name(" ")
    with pytest.raises(HTTPException):
        customer_routes._validate_name("Bad@Name")

    normalized = customer_routes._normalize_list([" CRITICAL ", "CRITICAL"], customer_routes.SEVERITIES, "severities")
    assert normalized == ["CRITICAL"]
    with pytest.raises(HTTPException):
        customer_routes._normalize_list(["BAD"], customer_routes.SEVERITIES, "severities")

    assert customer_routes._normalize_json({"a": 1}) == {"a": 1}
    assert customer_routes._normalize_json(b'{"a":1}') == {"a": 1}
    assert customer_routes._normalize_json("not json") == {}

    # generate_test_payload removed; test route-level helpers only.


async def test_get_alert_success(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = {
        "alert_id": "a1",
        "tenant_id": "tenant-a",
        "device_id": "d1",
        "site_id": "s1",
        "alert_type": "NO_HEARTBEAT",
        "severity": "WARNING",
        "confidence": 0.9,
        "summary": "Alert",
        "status": "OPEN",
        "created_at": datetime.now(timezone.utc),
    }

    resp = await client.get("/customer/alerts/a1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["alert"]["alert_id"] == "a1"


async def test_get_alert_not_found(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    conn.fetchrow_result = None

    resp = await client.get("/customer/alerts/a1", headers=_auth_header())
    assert resp.status_code == 404


async def test_get_device_detail_json(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(devices_routes, "fetch_device", AsyncMock(return_value={"device_id": "d1"}))
    monkeypatch.setattr(devices_routes, "fetch_device_events", AsyncMock(return_value=[]))
    monkeypatch.setattr(devices_routes, "fetch_device_telemetry", AsyncMock(return_value=[]))

    resp = await client.get("/customer/devices/d1", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["device"]["device_id"] == "d1"


















async def test_delivery_status(client, monkeypatch):
    conn = FakeConn()
    _mock_customer_deps(monkeypatch, conn)
    monkeypatch.setattr(customer_routes, "fetch_delivery_attempts", AsyncMock(return_value=[]))

    resp = await client.get("/customer/delivery-status", headers=_auth_header())
    assert resp.status_code == 200
    assert resp.json()["attempts"] == []




























async def test_app_helpers(monkeypatch):
    monkeypatch.setenv("SECURE_COOKIES", "true")
    assert app_module._secure_cookies_enabled() is True
    monkeypatch.setenv("UI_BASE_URL", "http://localhost:8080/")
    assert app_module.get_ui_base_url() == "http://localhost:8080"
    verifier, challenge = app_module.generate_pkce_pair()
    assert verifier and challenge
    assert app_module.generate_state()


async def test_login_redirects_to_keycloak(client, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    resp = await client.get("/login")
    assert resp.status_code == 302
    assert "kc.example" in resp.headers["location"]
    assert "code_challenge=challenge" in resp.headers["location"]


async def test_callback_missing_code(client):
    resp = await client.get("/callback")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=missing_code"


async def test_callback_state_mismatch(client, monkeypatch):
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"}))
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    resp = await client.get("/callback?code=abc&state=other", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=state_mismatch"


async def test_callback_token_exchange_failure(client, monkeypatch):
    response = SimpleNamespace(status_code=400, text="bad", json=lambda: {})
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))

    resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=invalid_code"


async def test_callback_success_customer(client, monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"}))

    resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"


async def test_logout_redirects_to_keycloak(client, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://public.example")
    resp = await client.get("/logout")
    assert resp.status_code == 302
    assert "public.example" in resp.headers["location"]


async def test_auth_status_no_cookie(client):
    resp = await client.get("/api/auth/status")
    assert resp.json() == {"authenticated": False}


async def test_auth_status_valid_token(client, monkeypatch):
    monkeypatch.setattr(app_module, "validate_token", AsyncMock(return_value={"exp": 2000, "email": "a@b.com"}))
    monkeypatch.setattr(app_module.time, "time", lambda: 1700)
    resp = await client.get("/api/auth/status", cookies={"pulse_session": "token"})
    assert resp.json()["authenticated"] is True


async def test_auth_refresh_no_cookie(client):
    resp = await client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": "csrf"},
        cookies={"csrf_token": "csrf"},
    )
    assert resp.status_code == 401


async def test_auth_refresh_success(client, monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 120, "refresh_expires_in": 300},
    )
    monkeypatch.setattr(app_module.httpx, "AsyncClient", lambda *a, **k: _mock_async_client(response))
    resp = await client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-Token": "csrf"},
        cookies={"pulse_refresh": "refresh", "csrf_token": "csrf"},
    )
    assert resp.status_code == 200


async def test_debug_auth_prod_mode(client, monkeypatch):
    monkeypatch.setenv("MODE", "PROD")
    resp = await client.get("/debug/auth")
    assert resp.status_code == 404


async def test_root_no_session(client):
    resp = await client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"


async def test_root_operator_session(client, monkeypatch):
    resp = await client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"
