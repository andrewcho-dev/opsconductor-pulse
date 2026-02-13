import sys
import os
import time
import types
from unittest.mock import patch
import pytest

# Stub out modules not available in test environment
if "dateutil" not in sys.modules:
    parser_stub = types.SimpleNamespace(isoparse=lambda _v: None)
    sys.modules["dateutil"] = types.SimpleNamespace(parser=parser_stub)
    sys.modules["dateutil.parser"] = parser_stub

if "asyncpg" not in sys.modules:
    sys.modules["asyncpg"] = types.SimpleNamespace()

if "httpx" not in sys.modules:
    sys.modules["httpx"] = types.SimpleNamespace()

if "paho" not in sys.modules:
    mqtt_client_stub = types.SimpleNamespace(Client=lambda *args, **kwargs: None)
    mqtt_stub = types.SimpleNamespace(client=mqtt_client_stub)
    sys.modules["paho"] = types.SimpleNamespace(mqtt=mqtt_stub)
    sys.modules["paho.mqtt"] = mqtt_stub
    sys.modules["paho.mqtt.client"] = mqtt_client_stub

services_dir = os.path.join(os.path.dirname(__file__), "..", "..", "services")
sys.path.insert(0, services_dir)
from shared.ingest_core import (  # noqa: E402
    DeviceAuthCache,
    TokenBucket,
    sha256_hex,
    validate_and_prepare,
)


@pytest.mark.unit
def test_cache_miss_returns_none():
    cache = DeviceAuthCache()
    assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_put_and_get():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    entry = cache.get("t1", "d1")
    assert entry["token_hash"] == "hash"
    assert entry["site_id"] == "site-1"
    assert entry["status"] == "ACTIVE"


@pytest.mark.unit
def test_cache_hit_increments_counter():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    cache.get("t1", "d1")
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0


@pytest.mark.unit
def test_cache_miss_increments_counter():
    cache = DeviceAuthCache()
    cache.get("t1", "d1")
    assert cache.stats()["misses"] == 1


@pytest.mark.unit
def test_cache_ttl_expiration():
    cache = DeviceAuthCache(ttl_seconds=60)
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    with patch("shared.ingest_core.time.time", return_value=time.time() + 61):
        assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_max_size_eviction():
    cache = DeviceAuthCache(max_size=10)
    for i in range(10):
        cache.put("t1", f"d{i}", f"hash{i}", f"site-{i}", "ACTIVE")
    cache.put("t1", "d10", "hash10", "site-10", "ACTIVE")
    assert cache.stats()["size"] == 10


@pytest.mark.unit
def test_cache_invalidate():
    cache = DeviceAuthCache()
    cache.put("t1", "d1", "hash", "site-1", "ACTIVE")
    cache.invalidate("t1", "d1")
    assert cache.get("t1", "d1") is None


@pytest.mark.unit
def test_cache_stats_size():
    cache = DeviceAuthCache()
    for i in range(5):
        cache.put("t1", f"d{i}", f"hash{i}", f"site-{i}", "ACTIVE")
    assert cache.stats()["size"] == 5


class _DummyConn:
    def __init__(self, row):
        self._row = row

    async def fetchrow(self, *_args, **_kwargs):
        return self._row


class _DummyAcquire:
    def __init__(self, row):
        self._row = row

    async def __aenter__(self):
        return _DummyConn(self._row)

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


class _DummyPool:
    def __init__(self, row):
        self._row = row

    def acquire(self):
        return _DummyAcquire(self._row)


@pytest.mark.asyncio
async def test_validate_and_prepare_unregistered_device():
    result = await validate_and_prepare(
        pool=_DummyPool(None),
        auth_cache=DeviceAuthCache(),
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {"temp": 1.0}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is False
    assert result.reason == "UNREGISTERED_DEVICE"


@pytest.mark.asyncio
async def test_validate_and_prepare_token_missing():
    auth_cache = DeviceAuthCache()
    auth_cache.put("t1", "d1", sha256_hex("token"), "s1", "ACTIVE")
    result = await validate_and_prepare(
        pool=None,
        auth_cache=auth_cache,
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token=None,
        payload={"metrics": {}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is False
    assert result.reason == "TOKEN_MISSING"


@pytest.mark.asyncio
async def test_validate_and_prepare_token_invalid():
    auth_cache = DeviceAuthCache()
    auth_cache.put("t1", "d1", sha256_hex("token"), "s1", "ACTIVE")
    result = await validate_and_prepare(
        pool=None,
        auth_cache=auth_cache,
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="wrong",
        payload={"metrics": {}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is False
    assert result.reason == "TOKEN_INVALID"


@pytest.mark.asyncio
async def test_validate_and_prepare_device_revoked():
    auth_cache = DeviceAuthCache()
    auth_cache.put("t1", "d1", sha256_hex("token"), "s1", "SUSPENDED")
    result = await validate_and_prepare(
        pool=None,
        auth_cache=auth_cache,
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is False
    assert result.reason == "DEVICE_REVOKED"


@pytest.mark.asyncio
async def test_validate_and_prepare_site_mismatch():
    auth_cache = DeviceAuthCache()
    auth_cache.put("t1", "d1", sha256_hex("token"), "site-a", "ACTIVE")
    result = await validate_and_prepare(
        pool=None,
        auth_cache=auth_cache,
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="site-b",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is False
    assert result.reason == "SITE_MISMATCH"


@pytest.mark.asyncio
async def test_validate_and_prepare_rate_limited():
    bucket = TokenBucket()
    bucket.tokens = 0.0
    bucket.updated = time.time()
    result = await validate_and_prepare(
        pool=None,
        auth_cache=DeviceAuthCache(),
        rate_buckets={("t1", "d1"): bucket},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {}},
        max_payload_bytes=1024,
        rps=0.0,
        burst=0.0,
        require_token=False,
    )
    assert result.success is False
    assert result.reason == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_validate_and_prepare_payload_too_large():
    result = await validate_and_prepare(
        pool=None,
        auth_cache=DeviceAuthCache(),
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {"data": "x" * 100}},
        max_payload_bytes=10,
        rps=5.0,
        burst=5.0,
        require_token=False,
    )
    assert result.success is False
    assert result.reason == "PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_validate_and_prepare_success_cached():
    auth_cache = DeviceAuthCache()
    auth_cache.put("t1", "d1", sha256_hex("token"), "s1", "ACTIVE")
    result = await validate_and_prepare(
        pool=None,
        auth_cache=auth_cache,
        rate_buckets={},
        tenant_id="t1",
        device_id="d1",
        site_id="s1",
        msg_type="telemetry",
        provision_token="token",
        payload={"metrics": {"temp": 1.0}},
        max_payload_bytes=1024,
        rps=5.0,
        burst=5.0,
        require_token=True,
    )
    assert result.success is True
