# Phase 103 — JWKS Cache Module

## File to create
`services/shared/jwks_cache.py`

## Content

```python
"""
JWKS cache with TTL and stale-on-error fallback.

Usage:
    cache = JwksCache(jwks_uri="https://keycloak/realms/pulse/protocol/openid-connect/certs")
    await cache.start()          # starts background refresh task
    keys = await cache.get()     # returns cached JWKS keys, refreshes if stale
    await cache.stop()           # cancels background task on shutdown
"""

import asyncio
import logging
import os
import time
from typing import Any

import httpx

from shared.log import get_logger

logger = get_logger("pulse.jwks_cache")

JWKS_TTL_SECONDS = int(os.getenv("JWKS_TTL_SECONDS", "600"))        # 10 min
JWKS_REFRESH_INTERVAL = int(os.getenv("JWKS_REFRESH_INTERVAL", "300"))  # 5 min
JWKS_FETCH_TIMEOUT = float(os.getenv("JWKS_FETCH_TIMEOUT", "5.0"))
JWKS_MAX_STALENESS = int(os.getenv("JWKS_MAX_STALENESS", "3600"))    # 1 hour hard limit


class JwksCache:
    def __init__(self, jwks_uri: str):
        self._uri = jwks_uri
        self._keys: list[dict[str, Any]] = []
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Fetch JWKS immediately, then start background refresh loop."""
        await self._fetch()
        self._refresh_task = asyncio.create_task(self._refresh_loop(), name="jwks_refresh")

    async def stop(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def get(self) -> list[dict[str, Any]]:
        """
        Return current keys.
        If cache is older than TTL, attempt a refresh.
        If refresh fails but cache is not yet past MAX_STALENESS, return stale keys.
        If cache is empty and refresh fails, raise RuntimeError.
        """
        age = time.monotonic() - self._fetched_at
        if age > JWKS_TTL_SECONDS:
            await self._try_refresh()
        return self._keys

    async def _try_refresh(self) -> None:
        try:
            await self._fetch()
        except Exception as exc:
            age = time.monotonic() - self._fetched_at
            if age > JWKS_MAX_STALENESS:
                logger.error("jwks_cache_expired_and_unreachable", extra={"error": str(exc)})
                raise RuntimeError("JWKS cache expired and Keycloak is unreachable") from exc
            logger.warning(
                "jwks_refresh_failed_using_stale",
                extra={"age_s": round(age), "error": str(exc)},
            )

    async def _fetch(self) -> None:
        async with self._lock:
            async with httpx.AsyncClient(timeout=JWKS_FETCH_TIMEOUT) as client:
                resp = await client.get(self._uri)
                resp.raise_for_status()
                data = resp.json()
            self._keys = data.get("keys", [])
            self._fetched_at = time.monotonic()
            logger.info("jwks_refreshed", extra={"key_count": len(self._keys)})

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(JWKS_REFRESH_INTERVAL)
            try:
                await self._fetch()
            except Exception as exc:
                logger.warning("jwks_background_refresh_failed", extra={"error": str(exc)})
```

## Notes

- `start()` must be called at service startup (in FastAPI `lifespan` or `@app.on_event("startup")`).
- `stop()` must be called at shutdown.
- The cache is a singleton per process — instantiate once and share across requests.
