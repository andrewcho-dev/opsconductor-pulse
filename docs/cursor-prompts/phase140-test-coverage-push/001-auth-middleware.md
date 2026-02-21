# 140-001: Critical Path — Auth Middleware (Target: 90%+)

## Task
Write comprehensive tests for `services/ui_iot/middleware/auth.py` (182 lines).

## File
`tests/unit/test_auth_middleware.py` (extend existing file)

## Current Coverage
~20% — only basic tests exist for JWKS caching, token from header/cookie, and a few error cases.

## Key Functions to Test
From `services/ui_iot/middleware/auth.py`:
1. `get_jwks()` — fetches and caches JWKS from Keycloak
2. `get_signing_key(token, jwks)` — extracts KID from token header, finds matching key
3. `validate_token(token)` — verifies JWT signature, expiry, claims
4. `JWTBearer.__call__(request)` — FastAPI dependency that validates auth
5. `check_auth_rate_limit(client_ip)` — rate limits auth attempts
6. `_get_client_ip(request)` — extracts client IP from X-Forwarded-For or client

## Existing Test Pattern
```python
import importlib
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.requests import Request

def _auth_module():
    return importlib.import_module("middleware.auth")

def _make_request(headers=None, cookies=None):
    headers = headers or {}
    cookie_header = ""
    if cookies:
        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers = {**headers, "cookie": cookie_header}
    scope = {
        "type": "http", "method": "GET", "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)
```

## Test Cases to Add

### get_jwks()
```python
async def test_get_jwks_fetches_from_keycloak():
    """First call fetches JWKS from Keycloak endpoint."""
    auth = _auth_module()
    fake_keys = [{"kid": "key-1", "kty": "RSA", "n": "...", "e": "AQAB"}]
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(return_value=fake_keys)
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        result = await auth.get_jwks()
    assert result == fake_keys

async def test_get_jwks_returns_cached_on_second_call():
    """Subsequent calls return cached JWKS without re-fetching."""
    # Already tested, but verify cache hit behavior

async def test_get_jwks_handles_keycloak_unavailable():
    """Raises appropriate error when Keycloak is unreachable."""
    auth = _auth_module()
    fake_cache = MagicMock()
    fake_cache.get = AsyncMock(side_effect=Exception("Connection refused"))
    with patch("middleware.auth._get_or_init_cache", return_value=fake_cache):
        with pytest.raises(Exception):
            await auth.get_jwks()
```

### get_signing_key()
```python
async def test_get_signing_key_finds_matching_kid():
    """Finds the correct key by KID from JWKS."""

async def test_get_signing_key_unknown_kid_raises():
    """Raises when token KID doesn't match any JWKS key."""
    auth = _auth_module()
    jwks = {"keys": [{"kid": "known-key", "kty": "RSA"}]}
    # Create a token with KID "unknown-key"
    with pytest.raises(HTTPException) as err:
        await auth.get_signing_key("token.with.unknown-kid", jwks)
    assert err.value.status_code == 401
```

### validate_token()
```python
async def test_validate_token_valid_jwt():
    """Successfully validates a properly signed JWT."""
    auth = _auth_module()
    expected_payload = {"sub": "user-1", "tenant_id": "t1", "realm_access": {"roles": ["customer"]}}
    with patch("middleware.auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "k1"}]})), \
         patch("middleware.auth.get_signing_key", return_value={"kid": "k1"}), \
         patch("middleware.auth.jwk.construct", return_value=MagicMock()), \
         patch("middleware.auth.jwt.decode", return_value=expected_payload):
        result = await auth.validate_token("valid.jwt.token")
    assert result == expected_payload

async def test_validate_token_expired_raises_401():
    """Expired JWT raises 401."""
    # Use jwt.ExpiredSignatureError side_effect

async def test_validate_token_invalid_signature_raises_401():
    """Invalid signature raises 401."""
    # Use jwt.InvalidSignatureError side_effect

async def test_validate_token_malformed_raises_401():
    """Malformed JWT string raises 401."""
    # Use jwt.DecodeError side_effect

async def test_validate_token_missing_claims():
    """JWT with missing required claims."""
    # Return payload without required fields
```

### JWTBearer.__call__()
```python
async def test_jwt_bearer_valid_bearer_header():
    """Extracts token from Authorization: Bearer <token>."""
    # Already exists, extend if needed

async def test_jwt_bearer_valid_cookie():
    """Extracts token from pulse_session cookie when no header."""

async def test_jwt_bearer_header_takes_precedence_over_cookie():
    """Header auth is preferred over cookie auth."""

async def test_jwt_bearer_missing_auth_raises_401():
    """No header and no cookie raises 401."""
    auth = _auth_module()
    request = _make_request()
    with pytest.raises(HTTPException) as err:
        await auth.JWTBearer()(request)
    assert err.value.status_code == 401

async def test_jwt_bearer_malformed_bearer_header():
    """Authorization header without 'Bearer' prefix."""
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Basic dXNlcjpwYXNz"})
    with pytest.raises(HTTPException) as err:
        await auth.JWTBearer()(request)
    assert err.value.status_code == 401

async def test_jwt_bearer_sets_request_state_user():
    """request.state.user is set after successful auth."""
    auth = _auth_module()
    payload = {"sub": "user-1", "role": "customer_admin", "tenant_id": "t1"}
    request = _make_request(headers={"authorization": "Bearer token123"})
    with patch("middleware.auth.validate_token", AsyncMock(return_value=payload)):
        await auth.JWTBearer()(request)
    assert request.state.user == payload

async def test_jwt_bearer_empty_bearer_token():
    """Authorization: Bearer (empty token) raises 401."""
    auth = _auth_module()
    request = _make_request(headers={"authorization": "Bearer "})
    with pytest.raises(HTTPException):
        await auth.JWTBearer()(request)
```

### _get_client_ip()
```python
def test_get_client_ip_from_x_forwarded_for():
    """Extracts IP from X-Forwarded-For header."""
    auth = _auth_module()
    request = _make_request(headers={"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
    assert auth._get_client_ip(request) == "1.2.3.4"

def test_get_client_ip_from_client():
    """Falls back to request.client.host."""
    auth = _auth_module()
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "client": ("5.6.7.8", 12345)}
    request = Request(scope)
    assert auth._get_client_ip(request) == "5.6.7.8"

def test_get_client_ip_no_client():
    """Returns fallback when no client info available."""
    auth = _auth_module()
    request = _make_request()
    ip = auth._get_client_ip(request)
    assert ip is not None  # should return some default
```

### check_auth_rate_limit()
```python
async def test_rate_limit_allows_normal_requests():
    """Normal request rate is allowed."""

async def test_rate_limit_blocks_excessive_requests():
    """Too many requests from same IP raises 429."""
    # May be skipped during pytest (check if there's a PYTEST flag)
```

## Verification
```bash
pytest tests/unit/test_auth_middleware.py -v --cov=services/ui_iot/middleware/auth --cov-report=term-missing
# Target: >= 90% coverage on auth.py
```
