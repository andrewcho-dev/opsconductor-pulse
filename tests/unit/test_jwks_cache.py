import asyncio
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.shared.jwks_cache import JwksCache

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _mock_async_client(response: httpx.Response | None = None, exc: Exception | None = None):
    context = AsyncMock()
    client = AsyncMock()
    if exc is not None:
        client.get.side_effect = exc
    else:
        client.get.return_value = response
    context.__aenter__.return_value = client
    return context


async def test_get_keys_fetches_on_first_call():
    cache = JwksCache("http://kc/certs")
    response = httpx.Response(200, json={"keys": [{"kid": "k1"}]}, request=httpx.Request("GET", "http://kc/certs"))
    with patch("services.shared.jwks_cache.httpx.AsyncClient", return_value=_mock_async_client(response)):
        keys = await cache.get_keys()
    assert keys == [{"kid": "k1"}]


async def test_get_keys_returns_cache_when_fresh():
    cache = JwksCache("http://kc/certs")
    cache._keys = [{"kid": "k1"}]
    cache._fetched_at = time.monotonic()
    with patch("services.shared.jwks_cache.httpx.AsyncClient") as client_cls:
        keys = await cache.get_keys()
    assert keys == [{"kid": "k1"}]
    client_cls.assert_not_called()


async def test_get_keys_refetches_when_stale():
    cache = JwksCache("http://kc/certs")
    cache._keys = [{"kid": "old"}]
    cache._fetched_at = 0
    response = httpx.Response(200, json={"keys": [{"kid": "new"}]}, request=httpx.Request("GET", "http://kc/certs"))
    with patch("services.shared.jwks_cache.httpx.AsyncClient", return_value=_mock_async_client(response)):
        keys = await cache.get_keys()
    assert keys == [{"kid": "new"}]


async def test_force_refresh_refetches():
    cache = JwksCache("http://kc/certs")
    cache._keys = [{"kid": "old"}]
    cache._fetched_at = time.monotonic()
    response = httpx.Response(200, json={"keys": [{"kid": "fresh"}]}, request=httpx.Request("GET", "http://kc/certs"))
    with patch("services.shared.jwks_cache.httpx.AsyncClient", return_value=_mock_async_client(response)):
        keys = await cache.force_refresh()
    assert keys == [{"kid": "fresh"}]


async def test_retry_on_failure():
    cache = JwksCache("http://kc/certs")
    cache.max_staleness = 3600
    cache._keys = [{"kid": "stale"}]
    cache._fetched_at = time.monotonic() - (cache.ttl_seconds + 1)
    req = httpx.Request("GET", "http://kc/certs")
    with patch(
        "services.shared.jwks_cache.httpx.AsyncClient",
        return_value=_mock_async_client(exc=httpx.RequestError("down1", request=req)),
    ):
        keys = await cache.get_keys()
    assert keys == [{"kid": "stale"}]


async def test_all_retries_fail_raises():
    cache = JwksCache("http://kc/certs")
    cache.max_staleness = 1
    cache._fetched_at = 0
    req = httpx.Request("GET", "http://kc/certs")
    with patch(
        "services.shared.jwks_cache.httpx.AsyncClient",
        return_value=_mock_async_client(exc=httpx.RequestError("down", request=req)),
    ):
        with pytest.raises(RuntimeError):
            await cache.get_keys()


async def test_is_stale_true_when_old():
    cache = JwksCache("http://kc/certs")
    cache._fetched_at = time.monotonic() - 1000
    assert cache.is_stale() is True


async def test_is_stale_false_when_fresh():
    cache = JwksCache("http://kc/certs")
    cache._fetched_at = time.monotonic()
    assert cache.is_stale() is False


async def test_concurrent_get_keys_single_fetch():
    cache = JwksCache("http://kc/certs")
    response = httpx.Response(200, json={"keys": [{"kid": "k1"}]}, request=httpx.Request("GET", "http://kc/certs"))
    context = AsyncMock()
    client = AsyncMock()

    async def _slow_get(*_args, **_kwargs):
        await asyncio.sleep(0.01)
        return response

    client.get.side_effect = _slow_get
    context.__aenter__.return_value = client

    with patch("services.shared.jwks_cache.httpx.AsyncClient", return_value=context), patch.object(
        cache, "ttl_seconds", 3600
    ):
        results = await asyncio.gather(cache.get_keys(), cache.get_keys())

    assert results[0] == [{"kid": "k1"}]
    assert results[1] == [{"kid": "k1"}]
    assert client.get.call_count >= 1
