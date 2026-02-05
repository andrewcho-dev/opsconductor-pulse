import importlib
import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def _get_app_module():
    return importlib.import_module("app")


@pytest.fixture
async def client():
    app_module = _get_app_module()
    app_module.app.router.on_startup.clear()
    app_module.app.router.on_shutdown.clear()
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _mock_async_client(response: MagicMock | None = None, exc: Exception | None = None):
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


def _make_request(headers=None):
    headers = headers or {}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


async def test_login_redirects_to_keycloak(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://kc.internal")
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    response = await client.get("/login")

    assert response.status_code == 302
    assert "kc.example" in response.headers["location"]
    assert "client_id=pulse-ui" in response.headers["location"]
    assert "code_challenge=challenge" in response.headers["location"]
    assert "state=state123" in response.headers["location"]


async def test_login_sets_state_cookie(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    response = await client.get("/login")

    cookies = response.headers.get_list("set-cookie")
    state_cookie = [c for c in cookies if c.startswith("oauth_state=")][0]
    assert "httponly" in state_cookie.lower()
    assert "samesite=lax" in state_cookie.lower()


async def test_login_sets_verifier_cookie(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    response = await client.get("/login")

    cookies = response.headers.get_list("set-cookie")
    verifier_cookie = [c for c in cookies if c.startswith("oauth_verifier=")][0]
    assert "oauth_verifier=" in verifier_cookie


async def test_login_uses_public_keycloak_url(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://public.example")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://internal.example")
    monkeypatch.setattr(app_module, "generate_pkce_pair", lambda: ("verifier", "challenge"))
    monkeypatch.setattr(app_module, "generate_state", lambda: "state123")

    response = await client.get("/login")

    assert "public.example" in response.headers["location"]
    assert "internal.example" not in response.headers["location"]


async def test_callback_missing_code(client):
    response = await client.get("/callback")
    assert response.status_code == 302
    assert response.headers["location"] == "/?error=missing_code"


async def test_callback_missing_state_cookie(client, monkeypatch):
    app_module = _get_app_module()
    with patch.object(app_module.logger, "warning") as warning:
        response = await client.get("/callback?code=abc&state=state123")

    assert response.status_code == 302
    assert response.headers["location"] == "/?error=missing_state"
    warning.assert_called_once()


async def test_callback_state_mismatch(client, monkeypatch):
    app_module = _get_app_module()
    cookies = {"oauth_state": "state123"}
    with patch.object(app_module.logger, "warning") as warning:
        response = await client.get("/callback?code=abc&state=other", cookies=cookies)

    assert response.status_code == 302
    assert response.headers["location"] == "/?error=state_mismatch"
    warning.assert_called_once()


async def test_callback_missing_verifier(client, monkeypatch):
    app_module = _get_app_module()
    cookies = {"oauth_state": "state123"}
    with patch.object(app_module.logger, "warning") as warning:
        response = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert response.status_code == 302
    assert response.headers["location"] == "/?error=missing_verifier"
    warning.assert_called_once()


async def test_callback_token_exchange_failure(client, monkeypatch):
    app_module = _get_app_module()
    response = MagicMock(status_code=400, text="bad", json=lambda: {})
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module.logger, "warning"
    ) as warning:
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=invalid_code"
    warning.assert_called_once()


async def test_callback_token_exchange_server_error(client):
    response = MagicMock(status_code=500, text="oops", json=lambda: {})
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 503


async def test_callback_token_exchange_network_error(client):
    req = httpx.Request("POST", "http://kc/token")
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(exc=httpx.RequestError("boom", request=req))):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 503


async def test_callback_token_validation_failure(client):
    app_module = _get_app_module()
    response = MagicMock(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module, "validate_token", AsyncMock(side_effect=Exception("bad"))
    ), patch.object(app_module.logger, "warning") as warning:
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/?error=invalid_token"
    warning.assert_called_once()


async def test_callback_success_customer(client):
    app_module = _get_app_module()
    response = MagicMock(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"})
    ):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"
    cookies_out = resp.headers.get_list("set-cookie")
    assert any(c.startswith("pulse_session=") for c in cookies_out)
    assert any(c.startswith("pulse_refresh=") for c in cookies_out)


async def test_callback_success_operator(client):
    app_module = _get_app_module()
    response = MagicMock(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module, "validate_token", AsyncMock(return_value={"role": "operator"})
    ):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"


async def test_callback_unknown_role(client):
    app_module = _get_app_module()
    response = MagicMock(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module, "validate_token", AsyncMock(return_value={"role": "unknown"})
    ):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    assert resp.status_code == 302
    assert resp.headers["location"] == "/app/"


async def test_callback_clears_oauth_cookies(client):
    app_module = _get_app_module()
    response = MagicMock(
        status_code=200,
        text="ok",
        json=lambda: {"access_token": "token", "refresh_token": "refresh", "expires_in": 300},
    )
    cookies = {"oauth_state": "state123", "oauth_verifier": "verifier"}

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)), patch.object(
        app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"})
    ):
        resp = await client.get("/callback?code=abc&state=state123", cookies=cookies)

    cookies_out = resp.headers.get_list("set-cookie")
    assert any("oauth_state=" in c and "max-age=0" in c.lower() for c in cookies_out)
    assert any("oauth_verifier=" in c and "max-age=0" in c.lower() for c in cookies_out)


async def test_logout_redirects_to_keycloak(client, monkeypatch):
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://public.example")
    response = await client.get("/logout")

    assert response.status_code == 302
    assert "public.example" in response.headers["location"]
    assert "logout" in response.headers["location"]


async def test_logout_clears_session_cookies(client):
    response = await client.get("/logout")
    cookies_out = response.headers.get_list("set-cookie")
    assert any("pulse_session=" in c and "max-age=0" in c.lower() for c in cookies_out)
    assert any("pulse_refresh=" in c and "max-age=0" in c.lower() for c in cookies_out)


async def test_auth_status_no_cookie(client):
    response = await client.get("/api/auth/status")
    assert response.json() == {"authenticated": False}


async def test_auth_status_valid_token(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setattr(app_module.time, "time", lambda: 1000)
    payload = {"exp": 1300, "email": "a@b.com", "role": "customer_admin", "tenant_id": "t1"}
    with patch.object(app_module, "validate_token", AsyncMock(return_value=payload)):
        response = await client.get("/api/auth/status", cookies={"pulse_session": "token"})

    data = response.json()
    assert data["authenticated"] is True
    assert data["expires_in"] == 300
    assert data["user"]["email"] == "a@b.com"


async def test_auth_status_expired_token(client):
    app_module = _get_app_module()
    with patch.object(app_module, "validate_token", AsyncMock(side_effect=Exception("expired"))):
        response = await client.get("/api/auth/status", cookies={"pulse_session": "token"})

    assert response.json() == {"authenticated": False}


async def test_refresh_no_cookie(client):
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 401


async def test_refresh_success(client):
    response = MagicMock(
        status_code=200,
        json=lambda: {
            "access_token": "token",
            "refresh_token": "refresh",
            "expires_in": 120,
            "refresh_expires_in": 300,
        },
    )
    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.post("/api/auth/refresh", cookies={"pulse_refresh": "refresh"})

    assert resp.status_code == 200
    cookies_out = resp.headers.get_list("set-cookie")
    assert any(c.startswith("pulse_session=") for c in cookies_out)
    assert any(c.startswith("pulse_refresh=") for c in cookies_out)


async def test_refresh_keycloak_rejects(client):
    response = MagicMock(status_code=401, json=lambda: {"error": "invalid"})
    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.post("/api/auth/refresh", cookies={"pulse_refresh": "refresh"})

    assert resp.status_code == 401
    cookies_out = resp.headers.get_list("set-cookie")
    assert any("pulse_session=" in c and "max-age=0" in c.lower() for c in cookies_out)
    assert any("pulse_refresh=" in c and "max-age=0" in c.lower() for c in cookies_out)


async def test_refresh_keycloak_down(client):
    req = httpx.Request("POST", "http://kc/token")
    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(exc=httpx.RequestError("down", request=req))):
        resp = await client.post("/api/auth/refresh", cookies={"pulse_refresh": "refresh"})

    assert resp.status_code == 503


async def test_debug_auth_dev_mode(client, monkeypatch):
    app_module = _get_app_module()
    monkeypatch.setenv("MODE", "DEV")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://kc.example")
    monkeypatch.setenv("UI_BASE_URL", "http://kc.example:8080")
    response = MagicMock(status_code=200, json=lambda: {"issuer": "http://kc.example/realms/pulse"})

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.get("/debug/auth")

    assert resp.status_code == 200
    assert "status" in resp.json()


async def test_debug_auth_prod_mode(client, monkeypatch):
    monkeypatch.setenv("MODE", "PROD")
    resp = await client.get("/debug/auth")
    assert resp.status_code == 404


async def test_debug_auth_hostname_match(client, monkeypatch):
    monkeypatch.setenv("MODE", "DEV")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://kc.example")
    monkeypatch.setenv("UI_BASE_URL", "http://kc.example:8080")
    response = MagicMock(status_code=200, json=lambda: {"issuer": "http://kc.example/realms/pulse"})

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.get("/debug/auth")

    assert resp.json()["hostname_check"]["verdict"] == "OK"


async def test_debug_auth_hostname_mismatch(client, monkeypatch):
    monkeypatch.setenv("MODE", "DEV")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    monkeypatch.setenv("KEYCLOAK_INTERNAL_URL", "http://kc.example")
    monkeypatch.setenv("UI_BASE_URL", "http://ui.example")
    response = MagicMock(status_code=200, json=lambda: {"issuer": "http://kc.example/realms/pulse"})

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.get("/debug/auth")

    assert resp.json()["hostname_check"]["verdict"].startswith("FAIL")


async def test_debug_auth_keycloak_unreachable(client, monkeypatch):
    req = httpx.Request("GET", "http://kc/.well-known")
    monkeypatch.setenv("MODE", "DEV")
    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(exc=httpx.RequestError("down", request=req))):
        resp = await client.get("/debug/auth")

    assert resp.json()["keycloak_check"]["verdict"] == "FAIL: Keycloak unreachable"


async def test_debug_auth_issuer_mismatch(client, monkeypatch):
    monkeypatch.setenv("MODE", "DEV")
    monkeypatch.setenv("KEYCLOAK_PUBLIC_URL", "http://kc.example")
    response = MagicMock(status_code=200, json=lambda: {"issuer": "http://wrong/realms/pulse"})

    with patch("app.httpx.AsyncClient", return_value=_mock_async_client(response)):
        resp = await client.get("/debug/auth")

    assert resp.json()["keycloak_check"]["verdict"] == "FAIL: token iss claim won't match validator"


async def test_root_no_session(client):
    response = await client.get("/")
    assert response.status_code == 302
    assert response.headers["location"] == "/app/"


async def test_root_customer_session(client):
    app_module = _get_app_module()
    with patch.object(app_module, "validate_token", AsyncMock(return_value={"role": "customer_admin"})):
        response = await client.get("/", cookies={"pulse_session": "token"})

    assert response.status_code == 302
    assert response.headers["location"] == "/app/"


async def test_root_operator_session(client):
    app_module = _get_app_module()
    with patch.object(app_module, "validate_token", AsyncMock(return_value={"role": "operator"})):
        response = await client.get("/", cookies={"pulse_session": "token"})

    assert response.status_code == 302
    assert response.headers["location"] == "/app/"


async def test_root_invalid_session(client):
    app_module = _get_app_module()
    with patch.object(app_module, "validate_token", AsyncMock(side_effect=Exception("bad"))):
        response = await client.get("/", cookies={"pulse_session": "token"})

    assert response.status_code == 302
    assert response.headers["location"] == "/app/"
