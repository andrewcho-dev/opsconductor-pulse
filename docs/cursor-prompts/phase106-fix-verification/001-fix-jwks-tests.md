# Phase 106b — Fix 9 JWKS Test Failures

## Problem

9 unit tests fail after the Phase 103 JWKS cache refactor:
- `tests/unit/test_auth_middleware.py` — 5 failures patching `fetch_jwks` / old httpx target
- `tests/unit/test_jwks_cache.py` — 4 failures: constructor signature / method names don't match

## Step 1: Read both test files

Read `tests/unit/test_auth_middleware.py` and `tests/unit/test_jwks_cache.py` in full.

Then read the actual implementations:
- `services/shared/jwks_cache.py`
- `services/ui_iot/middleware/auth.py`

Note the exact public API: constructor args, method names, how the cache is
obtained inside the middleware.

## Step 2: Fix test_jwks_cache.py

Update the tests to match the actual `JwksCache` constructor and methods.

### Constructor

If the old tests called `JwksCache(url=...)` but the class now takes
`JwksCache(jwks_uri=...)`, update the calls:

```python
# OLD
cache = JwksCache(url="http://fake-keycloak/certs")

# NEW (match actual signature)
cache = JwksCache(jwks_uri="http://fake-keycloak/certs")
```

### Async get() method

If tests called `cache.fetch()` or `cache.keys()`, update to `await cache.get()`.

### Mocking the HTTP call

The cache uses `httpx.AsyncClient`. Patch it correctly:

```python
import respx
import httpx

FAKE_KEYS = [{"kid": "key1", "kty": "RSA"}]
FAKE_JWKS = {"keys": FAKE_KEYS}

@respx.mock
async def test_get_returns_keys():
    respx.get("http://fake-keycloak/certs").mock(
        return_value=httpx.Response(200, json=FAKE_JWKS)
    )
    cache = JwksCache(jwks_uri="http://fake-keycloak/certs")
    await cache._fetch()
    keys = await cache.get()
    assert keys == FAKE_KEYS
```

Or with `unittest.mock.patch` if the project doesn't use respx:

```python
from unittest.mock import AsyncMock, patch, MagicMock

async def test_get_returns_keys():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"keys": [{"kid": "k1"}]}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("shared.jwks_cache.httpx.AsyncClient", return_value=mock_client):
        cache = JwksCache(jwks_uri="http://fake/certs")
        await cache._fetch()
        keys = await cache.get()
    assert keys == [{"kid": "k1"}]
```

Use whichever pattern is consistent with the rest of the test suite.

### Stale fallback test

```python
async def test_stale_fallback_on_fetch_error():
    """Cache returns stale keys when refresh fails and staleness < MAX_STALENESS."""
    cache = JwksCache(jwks_uri="http://fake/certs")
    # Pre-populate cache with keys
    cache._keys = [{"kid": "stale-key"}]
    cache._fetched_at = time.monotonic() - (JWKS_TTL_SECONDS + 1)

    with patch("shared.jwks_cache.httpx.AsyncClient", side_effect=Exception("network error")):
        keys = await cache.get()

    assert keys == [{"kid": "stale-key"}]
```

### No-keys + error → RuntimeError test

```python
async def test_empty_cache_plus_error_raises():
    """If cache is empty and fetch fails, get() raises RuntimeError."""
    cache = JwksCache(jwks_uri="http://fake/certs")
    # _keys is empty, _fetched_at is 0 (far in the past)
    cache._fetched_at = 0.0

    with patch("shared.jwks_cache.httpx.AsyncClient", side_effect=Exception("network error")):
        with pytest.raises(RuntimeError):
            await cache.get()
```

## Step 3: Fix test_auth_middleware.py

### Find and replace old patch targets

Old tests likely patch:
```python
# OLD — patching a function that no longer exists
with patch("ui_iot.middleware.auth.fetch_jwks", ...) as mock:
    ...

# OLD — patching httpx directly in auth module
with patch("ui_iot.middleware.auth.httpx.get", ...) as mock:
    ...
```

New pattern — patch `JwksCache.get` on the singleton used by the middleware:

```python
from unittest.mock import AsyncMock, patch

FAKE_KEYS = [{"kid": "key1", "kty": "RSA", "n": "...", "e": "AQAB"}]

async def test_valid_token_passes(test_client):
    with patch(
        "shared.jwks_cache.JwksCache.get",
        new_callable=AsyncMock,
        return_value=FAKE_KEYS,
    ):
        resp = await test_client.get("/protected", headers={"Authorization": "Bearer fake-jwt"})
        # assertion depends on whether fake-jwt is a real signed token or not
```

**Important**: Read `middleware/auth.py` to see exactly how it obtains the
JWKS cache instance (module-level singleton? dependency injection? imported
function?). Patch at the correct import path.

If auth.py does:
```python
from shared.jwks_cache import JwksCache
_cache = JwksCache(jwks_uri=os.environ["KEYCLOAK_JWKS_URI"])
```

Then patch:
```python
with patch.object(_cache_instance, "get", new_callable=AsyncMock, return_value=FAKE_KEYS):
    ...
```

Or if it imports via a getter:
```python
# auth.py:
from auth import get_jwks_cache
keys = await get_jwks_cache().get()

# test:
with patch("ui_iot.middleware.auth.get_jwks_cache") as mock_getter:
    mock_getter.return_value.get = AsyncMock(return_value=FAKE_KEYS)
    ...
```

Match the patch target to the actual import path used in `auth.py`.

## Step 4: Verify

```bash
pytest tests/unit/test_auth_middleware.py tests/unit/test_jwks_cache.py -v --no-cov 2>&1 | tail -20
```

Expected: 0 failures (9 tests pass).

```bash
pytest tests/unit/ -q --no-cov 2>&1 | tail -5
```

Expected: 0 failures, 691 passed, 7 skipped.

## Step 5: Commit

```bash
git add tests/unit/test_auth_middleware.py tests/unit/test_jwks_cache.py

git commit -m "fix: update JWKS unit tests for Phase 103 cache refactor

- test_jwks_cache.py: update constructor arg (jwks_uri=), method names (get()),
  mock httpx.AsyncClient instead of requests.get
- test_auth_middleware.py: patch get_jwks_cache() / JwksCache.get instead of
  deleted fetch_jwks function
- Result: 0 failures in full unit suite"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `pytest tests/unit/test_auth_middleware.py` — 0 failures
- [ ] `pytest tests/unit/test_jwks_cache.py` — 0 failures
- [ ] Full unit suite `pytest tests/unit/ -q --no-cov` — 0 failures
