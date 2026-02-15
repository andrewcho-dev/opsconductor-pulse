import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from starlette.requests import Request

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def _auth_module():
    return importlib.import_module("middleware.auth")


def _make_request(headers=None, cookies=None):
    headers = headers or {}
    cookie_header = ""
    if cookies:
        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers = {**headers, "cookie": cookie_header}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


async def test_get_jwks_caches_result(monkeypatch):
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=[{"kid": "k1"}])
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        jwks1 = await auth.get_jwks()
        jwks2 = await auth.get_jwks()
    assert jwks1 == jwks2
    assert fake_cache.get.await_count == 2
    assert jwks1["keys"][0]["kid"] == "k1"


async def test_get_jwks_refreshes_after_ttl(monkeypatch):
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=[{"kid": "k2"}])
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        jwks = await auth.get_jwks()
    assert fake_cache.get.await_count == 1
    assert jwks["keys"][0]["kid"] == "k2"


async def test_get_signing_key_found():
    auth = _auth_module()
    with patch("middleware.auth.jwt.get_unverified_header", return_value={"kid": "k1"}):
        key = auth.get_signing_key("token", {"keys": [{"kid": "k1"}]})
    assert key["kid"] == "k1"


async def test_get_signing_key_not_found():
    auth = _auth_module()
    with patch("middleware.auth.jwt.get_unverified_header", return_value={"kid": "missing"}):
        with pytest.raises(HTTPException) as err:
            auth.get_signing_key("token", {"keys": [{"kid": "k1"}]})
    assert err.value.status_code == 401


async def test_get_signing_key_invalid_header():
    auth = _auth_module()
    with patch("middleware.auth.jwt.get_unverified_header", side_effect=JWTError()):
        with pytest.raises(HTTPException) as err:
            auth.get_signing_key("token", {"keys": []})
    assert err.value.status_code == 401


async def test_validate_token_expired():
    auth = _auth_module()
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", return_value={}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", side_effect=ExpiredSignatureError()
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.status_code == 401
    assert err.value.detail == "Token expired"


async def test_validate_token_wrong_audience():
    auth = _auth_module()
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", return_value={}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", side_effect=JWTClaimsError()
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.detail == "Invalid token claims"


async def test_validate_token_wrong_issuer():
    auth = _auth_module()
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", return_value={}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", side_effect=JWTClaimsError()
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.detail == "Invalid token claims"


async def test_validate_token_bad_signature():
    auth = _auth_module()
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", return_value={}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", side_effect=JWTError()
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.detail == "Invalid token"


async def test_jwt_bearer_from_header():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123"})
    with patch("middleware.auth.validate_token", AsyncMock(return_value={"role": "customer_admin"})):
        credentials = await auth.JWTBearer()(request)
    assert credentials.credentials == "token123"


async def test_jwt_bearer_from_cookie():
    auth = _auth_module()
    request = _make_request(cookies={"pulse_session": "token456"})
    with patch("middleware.auth.validate_token", AsyncMock(return_value={"role": "customer_admin"})):
        credentials = await auth.JWTBearer()(request)
    assert credentials.credentials == "token456"


async def test_jwt_bearer_header_takes_precedence():
    auth = _auth_module()
    request = _make_request(
        headers={"authorization": "Bearer header"},
        cookies={"pulse_session": "cookie"},
    )
    with patch("middleware.auth.validate_token", AsyncMock(return_value={"role": "customer_admin"})):
        credentials = await auth.JWTBearer()(request)
    assert credentials.credentials == "header"


async def test_jwt_bearer_missing_both():
    auth = _auth_module()
    request = _make_request()
    with pytest.raises(HTTPException) as err:
        await auth.JWTBearer()(request)
    assert err.value.status_code == 401


async def test_jwt_bearer_sets_request_state():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123"})
    payload = {"role": "customer_admin", "tenant_id": "t1"}
    with patch("middleware.auth.validate_token", AsyncMock(return_value=payload)):
        await auth.JWTBearer()(request)
    assert request.state.user == payload
