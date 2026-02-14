import asyncio
import time
from typing import Optional

import httpx


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
        async with self._lock:
            if self._keys is not None and not self.is_stale():
                return self._keys
            return await self._fetch_with_retry()

    async def _fetch_with_retry(self) -> list:
        """Fetch JWKS from Keycloak with exponential backoff."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(self.jwks_uri)
                    response.raise_for_status()
                    payload = response.json()
                    keys = payload.get("keys", [])
                    self._keys = keys
                    self._fetched_at = time.time()
                    return keys
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
        assert last_exc is not None
        raise last_exc

    async def force_refresh(self) -> list:
        """Force a cache refresh (called on key lookup failures)."""
        async with self._lock:
            self._fetched_at = 0.0
            self._keys = None
        return await self.get_keys()

    def is_stale(self) -> bool:
        return time.time() - self._fetched_at > self.ttl_seconds


_cache: Optional[JwksCache] = None


def get_jwks_cache() -> Optional[JwksCache]:
    return _cache


def init_jwks_cache(jwks_uri: str, ttl_seconds: int = 300) -> JwksCache:
    global _cache
    _cache = JwksCache(jwks_uri=jwks_uri, ttl_seconds=ttl_seconds)
    return _cache
