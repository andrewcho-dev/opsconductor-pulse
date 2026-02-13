from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from services.ui_iot.services import keycloak_admin as ka

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _Resp:
    def __init__(self, status_code=200, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text
        self.content = b"" if json_data is None else b"json"

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            req = httpx.Request("GET", "http://test")
            resp = httpx.Response(self.status_code, request=req, text=self.text)
            raise httpx.HTTPStatusError("error", request=req, response=resp)


class _ClientCtx:
    def __init__(self, post=None, request=None):
        self._post = post
        self._request = request

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return await self._post(*args, **kwargs)

    async def request(self, *args, **kwargs):
        return await self._request(*args, **kwargs)


async def test_get_admin_token_success(monkeypatch):
    ka._token_cache["token"] = None
    ka._token_cache["expires_at"] = None

    async def _post(*_args, **_kwargs):
        return _Resp(200, {"access_token": "abc", "expires_in": 300})

    monkeypatch.setattr(ka.httpx, "AsyncClient", lambda **_kwargs: _ClientCtx(post=_post, request=None))
    token = await ka._get_admin_token()
    assert token == "abc"
    assert ka._token_cache["token"] == "abc"


async def test_get_admin_token_failure(monkeypatch):
    ka._token_cache["token"] = None
    ka._token_cache["expires_at"] = None

    async def _post(*_args, **_kwargs):
        return _Resp(401, {"error": "unauthorized"}, text="unauthorized")

    monkeypatch.setattr(ka.httpx, "AsyncClient", lambda **_kwargs: _ClientCtx(post=_post, request=None))
    with pytest.raises(ka.KeycloakAdminError):
        await ka._get_admin_token()


async def test_get_admin_token_uses_cache_when_not_expired():
    ka._token_cache["token"] = "cached"
    ka._token_cache["expires_at"] = datetime.utcnow() + timedelta(minutes=5)
    token = await ka._get_admin_token()
    assert token == "cached"


async def test_list_users_with_search_params(monkeypatch):
    admin_request = AsyncMock(return_value=[{"id": "u1"}])
    monkeypatch.setattr(ka, "_admin_request", admin_request)
    users = await ka.list_users(search="alice", first=5, max_results=10)
    assert users == [{"id": "u1"}]
    assert admin_request.await_args.kwargs["params"]["search"] == "alice"


async def test_create_user_sends_correct_payload(monkeypatch):
    monkeypatch.setattr(ka, "_get_admin_token", AsyncMock(return_value="tok"))
    monkeypatch.setattr(ka, "get_user", AsyncMock(return_value={"id": "u1", "username": "alice"}))

    captured = {}

    async def _post(_url, headers=None, json=None):
        captured["headers"] = headers
        captured["json"] = json
        return _Resp(201, None, headers={"Location": "http://kc/users/u1"})

    monkeypatch.setattr(ka.httpx, "AsyncClient", lambda **_kwargs: _ClientCtx(post=_post, request=None))
    user = await ka.create_user(
        username="alice",
        email="alice@example.com",
        first_name="Alice",
        last_name="Ops",
        attributes={"tenant_id": ["tenant-a"]},
    )
    assert user["id"] == "u1"
    assert captured["json"]["username"] == "alice"
    assert captured["json"]["attributes"]["tenant_id"] == ["tenant-a"]


async def test_get_user_roles_returns_realm_roles(monkeypatch):
    monkeypatch.setattr(ka, "_admin_request", AsyncMock(return_value=[{"name": "operator"}]))
    roles = await ka.get_user_roles("u1")
    assert roles[0]["name"] == "operator"


async def test_assign_realm_role_sends_role_representation(monkeypatch):
    monkeypatch.setattr(ka, "get_realm_roles", AsyncMock(return_value=[{"name": "operator", "id": "r1"}]))
    admin_request = AsyncMock(return_value=None)
    monkeypatch.setattr(ka, "_admin_request", admin_request)
    await ka.assign_realm_role("u1", "operator")
    assert admin_request.await_args.kwargs["json"][0]["name"] == "operator"


async def test_remove_realm_role(monkeypatch):
    monkeypatch.setattr(ka, "get_realm_roles", AsyncMock(return_value=[{"name": "operator", "id": "r1"}]))
    admin_request = AsyncMock(return_value=None)
    monkeypatch.setattr(ka, "_admin_request", admin_request)
    await ka.remove_realm_role("u1", "operator")
    assert admin_request.await_args.args[0] == "DELETE"


async def test_admin_token_refresh_on_expiry(monkeypatch):
    ka._token_cache["token"] = "old-token"
    ka._token_cache["expires_at"] = datetime.utcnow() - timedelta(seconds=1)

    async def _post(*_args, **_kwargs):
        return _Resp(200, {"access_token": "new-token", "expires_in": 300})

    monkeypatch.setattr(ka.httpx, "AsyncClient", lambda **_kwargs: _ClientCtx(post=_post, request=None))
    token = await ka._get_admin_token()
    assert token == "new-token"


async def test_admin_request_http_error_raises(monkeypatch):
    monkeypatch.setattr(ka, "_get_admin_token", AsyncMock(return_value="tok"))

    async def _request(*_args, **_kwargs):
        return _Resp(500, {"error": "boom"}, text="boom")

    monkeypatch.setattr(ka.httpx, "AsyncClient", lambda **_kwargs: _ClientCtx(post=None, request=_request))
    with pytest.raises(ka.KeycloakAdminError):
        await ka._admin_request("GET", "/users")
