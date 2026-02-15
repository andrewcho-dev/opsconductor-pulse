import asyncio
import logging
import os
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger("pulse.jwks_cache")


class JwksCache:
    def __init__(self, jwks_uri: str, ttl_seconds: int = 600):
        self.jwks_uri = jwks_uri
        self.ttl_seconds = ttl_seconds
        self.refresh_interval = int(os.getenv("JWKS_REFRESH_INTERVAL", "300"))
        self.fetch_timeout = float(os.getenv("JWKS_FETCH_TIMEOUT", "5.0"))
        self.max_staleness = int(os.getenv("JWKS_MAX_STALENESS", "3600"))
        self._keys: list[dict[str, Any]] = []
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._fetch()
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop(), name="jwks_refresh")

    async def stop(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None

    async def get(self) -> list[dict[str, Any]]:
        age = time.monotonic() - self._fetched_at
        if age > self.ttl_seconds:
            await self._try_refresh()
        return self._keys

    async def get_keys(self) -> list[dict[str, Any]]:
        return await self.get()

    async def force_refresh(self) -> list[dict[str, Any]]:
        await self._fetch()
        return self._keys

    def is_stale(self) -> bool:
        if not self._fetched_at:
            return True
        return (time.monotonic() - self._fetched_at) > self.ttl_seconds

    async def _try_refresh(self) -> None:
        try:
            await self._fetch()
        except Exception as exc:
            age = time.monotonic() - self._fetched_at
            if not self._keys or age > self.max_staleness:
                logger.error(
                    "jwks_cache_expired_and_unreachable",
                    extra={"error": str(exc), "age_s": round(age)},
                )
                raise RuntimeError("JWKS cache expired and Keycloak is unreachable") from exc
            logger.warning(
                "jwks_refresh_failed_using_stale",
                extra={"age_s": round(age), "error": str(exc)},
            )

    async def _fetch(self) -> None:
        async with self._lock:
            async with httpx.AsyncClient(timeout=self.fetch_timeout) as client:
                resp = await client.get(self.jwks_uri)
                resp.raise_for_status()
                data = resp.json()
            self._keys = data.get("keys", [])
            self._fetched_at = time.monotonic()
            logger.info("jwks_refreshed", extra={"key_count": len(self._keys)})

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(self.refresh_interval)
            try:
                await self._fetch()
            except Exception as exc:
                logger.warning("jwks_background_refresh_failed", extra={"error": str(exc)})


_cache: Optional[JwksCache] = None


def get_jwks_cache() -> Optional[JwksCache]:
    return _cache


def init_jwks_cache(jwks_uri: str, ttl_seconds: int = 600) -> JwksCache:
    global _cache
    if _cache is None:
        _cache = JwksCache(jwks_uri=jwks_uri, ttl_seconds=ttl_seconds)
    return _cache
