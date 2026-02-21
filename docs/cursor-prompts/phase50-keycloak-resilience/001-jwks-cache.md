# Prompt 001 — JWKS Cache Module

Read `services/shared/` to understand existing shared utilities.
Read `services/ui_iot/auth.py` (or wherever JWT verification happens) to understand current JWKS fetch behavior.

## Create `services/shared/jwks_cache.py`

Implement a JWKS cache with these behaviors:

```python
import asyncio
import time
import httpx
from typing import Optional

class JwksCache:
    """
    Caches Keycloak public keys (JWKS) to avoid per-request Keycloak calls.

    - Keys are fetched once and cached for `ttl_seconds` (default 300).
    - On fetch failure, retries up to `max_retries` times with exponential backoff.
    - `get_keys()` returns cached keys if fresh, otherwise re-fetches.
    - Thread-safe for asyncio (single-event-loop) usage.
    """

    def __init__(self, jwks_uri: str, ttl_seconds: int = 300, max_retries: int = 3):
        self.jwks_uri = jwks_uri
        self.ttl_seconds = ttl_seconds
        self.max_retries = max_retries
        self._keys: Optional[list] = None
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_keys(self) -> list:
        """Return cached keys or fetch fresh ones."""
        ...

    async def _fetch_with_retry(self) -> list:
        """Fetch JWKS from Keycloak with exponential backoff."""
        ...

    async def force_refresh(self) -> list:
        """Force a cache refresh (called on 401 with stale keys)."""
        ...

    def is_stale(self) -> bool:
        return time.time() - self._fetched_at > self.ttl_seconds
```

Implement each method:
- `get_keys()`: acquire lock, check staleness, return cache or call `_fetch_with_retry()`
- `_fetch_with_retry()`: loop `max_retries` times; on each attempt, `httpx.AsyncClient().get(jwks_uri)`; on failure sleep `2**attempt` seconds; raise last exception if all retries fail; on success update `_keys` and `_fetched_at`
- `force_refresh()`: reset `_fetched_at = 0` then call `get_keys()`
- `is_stale()`: returns True if cache age > ttl_seconds

Export a module-level singleton factory:
```python
_cache: Optional[JwksCache] = None

def get_jwks_cache() -> JwksCache:
    return _cache

def init_jwks_cache(jwks_uri: str, ttl_seconds: int = 300) -> JwksCache:
    global _cache
    _cache = JwksCache(jwks_uri, ttl_seconds)
    return _cache
```

## Acceptance Criteria

- [ ] `JwksCache` class with `get_keys()`, `force_refresh()`, `is_stale()`
- [ ] Exponential backoff on fetch failure
- [ ] Module-level `init_jwks_cache()` and `get_jwks_cache()`
- [ ] `pytest -m unit -v` passes
