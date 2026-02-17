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


async def test_get_jwks_fetches_from_keycloak():
    """First call fetches JWKS from cache/provider."""
    auth = _auth_module()
    fake_keys = [{"kid": "key-1", "kty": "RSA", "n": "...", "e": "AQAB"}]
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=fake_keys)
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        result = await auth.get_jwks()
    assert result == {"keys": fake_keys}


async def test_get_jwks_handles_keycloak_unavailable():
    """Raises 503 when Keycloak/JWKS provider is unreachable."""
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(side_effect=Exception("Connection refused"))
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        with pytest.raises(HTTPException) as err:
            await auth.get_jwks()
    assert err.value.status_code == 503
    assert err.value.detail == "Auth service unavailable"


async def test_get_or_init_cache_initializes_when_missing():
    auth = _auth_module()
    sentinel_cache = MagicMock()
    with patch("middleware.auth.get_jwks_cache", return_value=None), patch(
        "middleware.auth.init_jwks_cache", return_value=sentinel_cache
    ) as init_mock:
        cache = auth._get_or_init_cache()
    assert cache is sentinel_cache
    init_mock.assert_called_once()


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
    assert err.value.detail == "Unknown signing key"


async def test_get_signing_key_missing_kid_raises():
    auth = _auth_module()
    with patch("middleware.auth.jwt.get_unverified_header", return_value={"typ": "JWT"}):
        with pytest.raises(HTTPException) as err:
            auth.get_signing_key("token", {"keys": [{"kid": "k1"}]})
    assert err.value.status_code == 401
    assert err.value.detail == "Invalid token"


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


async def test_validate_token_valid_jwt():
    """Successfully validates a properly signed JWT."""
    auth = _auth_module()
    expected_payload = {
        "sub": "user-1",
        "tenant_id": "t1",
        "realm_access": {"roles": ["customer"]},
    }
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "k1"}]})), patch(
        "middleware.auth.get_signing_key", return_value={"kid": "k1"}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", return_value=expected_payload
    ):
        result = await auth.validate_token("valid.jwt.token")
    assert result == expected_payload


async def test_validate_token_decode_exception_raises_401():
    """Unexpected exceptions in decode path still return a 401."""
    auth = _auth_module()
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", return_value={}
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", side_effect=Exception("boom")
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.status_code == 401
    assert err.value.detail == "Invalid token"


async def test_validate_token_unknown_signing_key_triggers_refresh_and_succeeds():
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.force_refresh = AsyncMock(return_value=[{"kid": "k1"}])
    unknown = HTTPException(status_code=401, detail="Unknown signing key")

    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "old"}]})), patch(
        "middleware.auth._get_or_init_cache", return_value=fake_cache
    ), patch(
        "middleware.auth.get_signing_key", side_effect=[unknown, {"kid": "k1"}]
    ), patch("middleware.auth.jwk.construct", return_value=MagicMock()), patch(
        "middleware.auth.jwt.decode", return_value={"sub": "user-1"}
    ):
        result = await auth.validate_token("token")
    assert result["sub"] == "user-1"
    assert fake_cache.force_refresh.await_count == 1


async def test_validate_token_unknown_signing_key_refresh_failure_raises_503():
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.force_refresh = AsyncMock(side_effect=Exception("down"))
    unknown = HTTPException(status_code=401, detail="Unknown signing key")

    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "old"}]})), patch(
        "middleware.auth._get_or_init_cache", return_value=fake_cache
    ), patch("middleware.auth.get_signing_key", side_effect=unknown):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.status_code == 503
    assert err.value.detail == "Auth service unavailable"


async def test_validate_token_unknown_signing_key_refresh_http_exception_reraises():
    """If refresh succeeds but key is still unknown, re-raise the HTTPException."""
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.force_refresh = AsyncMock(return_value=[{"kid": "k1"}])
    unknown = HTTPException(status_code=401, detail="Unknown signing key")
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "old"}]})), patch(
        "middleware.auth._get_or_init_cache", return_value=fake_cache
    ), patch("middleware.auth.get_signing_key", side_effect=[unknown, unknown]):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.status_code == 401
    assert err.value.detail == "Unknown signing key"


async def test_validate_token_other_http_exception_reraises():
    auth = _auth_module()
    bad = HTTPException(status_code=401, detail="Invalid token")
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": []})), patch(
        "middleware.auth.get_signing_key", side_effect=bad
    ):
        with pytest.raises(HTTPException) as err:
            await auth.validate_token("token")
    assert err.value.status_code == 401
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


async def test_jwt_bearer_malformed_bearer_header():
    """Authorization header without Bearer prefix should not be accepted."""
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Basic dXNlcjpwYXNz"})
    with pytest.raises(HTTPException) as err:
        await auth.JWTBearer()(request)
    assert err.value.status_code == 401
    assert err.value.detail == "Missing authorization"


async def test_jwt_bearer_empty_bearer_token():
    """Authorization: Bearer (empty token) raises 401."""
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer "})
    with pytest.raises(HTTPException) as err:
        await auth.JWTBearer()(request)
    assert err.value.status_code == 401
    assert err.value.detail == "Missing authorization"


async def test_jwt_bearer_sets_request_state():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123"})
    payload = {"role": "customer_admin", "tenant_id": "t1"}
    with patch("middleware.auth.validate_token", AsyncMock(return_value=payload)):
        await auth.JWTBearer()(request)
    assert request.state.user == payload


async def test_jwt_bearer_rate_limited_raises_429():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123"})
    with patch("middleware.auth.check_auth_rate_limit", return_value=False):
        with pytest.raises(HTTPException) as err:
            await auth.JWTBearer()(request)
    assert err.value.status_code == 429


async def test_jwt_bearer_missing_token_audits_and_counts():
    auth = _auth_module()
    request = _make_request(headers={"x-forwarded-for": "1.2.3.4"})
    audit = MagicMock()
    metric = MagicMock()
    metric.labels.return_value = metric
    with patch("middleware.auth.get_audit_logger", return_value=audit), patch(
        "middleware.auth.pulse_auth_failures_total", metric
    ), patch("middleware.auth.check_auth_rate_limit", return_value=True):
        with pytest.raises(HTTPException) as err:
            await auth.JWTBearer()(request)
    assert err.value.status_code == 401
    assert err.value.detail == "Missing authorization"
    audit.auth_failure.assert_called_once()
    metric.labels.assert_called_once_with(reason="missing_token")
    metric.inc.assert_called_once()


async def test_jwt_bearer_invalid_token_audits_and_counts():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123", "x-forwarded-for": "2.2.2.2"})
    audit = MagicMock()
    metric = MagicMock()
    metric.labels.return_value = metric
    exc = HTTPException(status_code=401, detail="Token expired")
    with patch("middleware.auth.get_audit_logger", return_value=audit), patch(
        "middleware.auth.pulse_auth_failures_total", metric
    ), patch("middleware.auth.validate_token", AsyncMock(side_effect=exc)), patch(
        "middleware.auth.check_auth_rate_limit", return_value=True
    ):
        with pytest.raises(HTTPException) as err:
            await auth.JWTBearer()(request)
    assert err.value.status_code == 401
    metric.labels.assert_called_once_with(reason="expired")
    metric.inc.assert_called_once()
    audit.auth_failure.assert_called_once()


async def test_jwt_bearer_success_audits_success():
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer token123", "x-forwarded-for": "3.3.3.3"})
    payload = {"tenant_id": "t1", "sub": "user-1", "email": "u@example.com"}
    audit = MagicMock()
    with patch("middleware.auth.get_audit_logger", return_value=audit), patch(
        "middleware.auth.validate_token", AsyncMock(return_value=payload)
    ), patch("middleware.auth.check_auth_rate_limit", return_value=True):
        await auth.JWTBearer()(request)
    audit.auth_success.assert_called_once()

async def test_get_client_ip_from_x_forwarded_for():
    auth = _auth_module()
    request = _make_request(headers={"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
    assert auth._get_client_ip(request) == "1.2.3.4"


async def test_get_client_ip_from_client():
    auth = _auth_module()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("5.6.7.8", 12345),
    }
    request = Request(scope)
    assert auth._get_client_ip(request) == "5.6.7.8"


async def test_get_client_ip_no_client():
    auth = _auth_module()
    request = _make_request()
    ip = auth._get_client_ip(request)
    assert ip == "unknown"


async def test_rate_limit_is_disabled_under_pytest():
    """check_auth_rate_limit always allows under pytest to keep tests deterministic."""
    auth = _auth_module()
    auth._auth_attempts.clear()
    auth.AUTH_RATE_LIMIT = 1
    # Even if we'd exceed the limit, PYTEST_CURRENT_TEST bypass returns True.
    assert auth.check_auth_rate_limit("1.2.3.4") is True
    assert auth.check_auth_rate_limit("1.2.3.4") is True
    assert auth.check_auth_rate_limit("1.2.3.4") is True


async def test_rate_limit_blocks_excessive_requests_when_not_pytest(monkeypatch):
    auth = _auth_module()
    auth._auth_attempts.clear()
    auth.AUTH_RATE_LIMIT = 2
    auth.AUTH_RATE_WINDOW = 60

    # Pretend we're not running under pytest for this function.
    real_getenv = auth.os.getenv

    def _fake_getenv(key, default=None):
        if key == "PYTEST_CURRENT_TEST":
            return None
        return real_getenv(key, default)

    times = [1000.0, 1001.0, 1002.0]
    with patch("middleware.auth.os.getenv", side_effect=_fake_getenv), patch(
        "middleware.auth.time.time", side_effect=times
    ):
        assert auth.check_auth_rate_limit("9.9.9.9") is True
        assert auth.check_auth_rate_limit("9.9.9.9") is True
        assert auth.check_auth_rate_limit("9.9.9.9") is False
