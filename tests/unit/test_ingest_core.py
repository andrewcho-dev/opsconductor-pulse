import asyncio
import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytest

from services.shared.ingest_core import (
    DeviceAuthCache,
    IngestResult,
    TelemetryRecord,
    TimescaleBatchWriter,
    TokenBucket,
    validate_and_prepare,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class FakeConn:
    def __init__(self, fetchrow_result=None):
        self.fetchrow_result = fetchrow_result
        self.fetchrow_calls = 0
        self.executemany_calls = []
        self.copy_calls = []

    async def fetchrow(self, *_args, **_kwargs):
        self.fetchrow_calls += 1
        return self.fetchrow_result

    async def executemany(self, _query, rows):
        self.executemany_calls.append(rows)

    async def copy_records_to_table(self, _table, records, columns):
        self.copy_calls.append((records, columns))


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _active_row(site_id="site-a", token="token-1"):
    return {
        "site_id": site_id,
        "status": "ACTIVE",
        "provision_token_hash": _hash_token(token),
    }


async def _valid_ingest(**kwargs):
    conn = FakeConn(fetchrow_result=_active_row())
    pool = FakePool(conn)
    auth_cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    rate_buckets = {}
    result = await validate_and_prepare(
        pool=pool,
        auth_cache=auth_cache,
        rate_buckets=rate_buckets,
        tenant_id=kwargs.get("tenant_id", "tenant-a"),
        device_id=kwargs.get("device_id", "device-1"),
        site_id=kwargs.get("site_id", "site-a"),
        msg_type=kwargs.get("msg_type", "telemetry"),
        provision_token=kwargs.get("provision_token", "token-1"),
        payload=kwargs.get("payload", {"site_id": "site-a", "metrics": {"temp_c": 20}}),
        max_payload_bytes=kwargs.get("max_payload_bytes", 8192),
        rps=kwargs.get("rps", 5.0),
        burst=kwargs.get("burst", 10.0),
        require_token=kwargs.get("require_token", True),
    )
    return result, conn, auth_cache, rate_buckets


async def test_device_auth_cache_miss_returns_none():
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    assert cache.get("tenant-a", "device-1") is None


async def test_device_auth_cache_put_and_get():
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    cache.put("tenant-a", "device-1", "hash-1", "site-a", "ACTIVE")
    entry = cache.get("tenant-a", "device-1")
    assert entry is not None
    assert entry["token_hash"] == "hash-1"
    assert entry["site_id"] == "site-a"


async def test_device_auth_cache_ttl_expiry(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: now)
    cache = DeviceAuthCache(ttl_seconds=10, max_size=100)
    cache.put("tenant-a", "device-1", "hash-1", "site-a", "ACTIVE")

    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: now + 11)
    assert cache.get("tenant-a", "device-1") is None


async def test_device_auth_cache_within_ttl_returns_data(monkeypatch):
    now = 2000.0
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: now)
    cache = DeviceAuthCache(ttl_seconds=10, max_size=100)
    cache.put("tenant-a", "device-1", "hash-1", "site-a", "ACTIVE")

    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: now + 5)
    assert cache.get("tenant-a", "device-1") is not None


async def test_device_auth_cache_max_size_eviction(monkeypatch):
    t = {"v": 0.0}
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: t["v"])
    cache = DeviceAuthCache(ttl_seconds=60, max_size=2)
    cache.put("tenant-a", "device-1", "h1", "site-a", "ACTIVE")
    t["v"] += 1
    cache.put("tenant-a", "device-2", "h2", "site-a", "ACTIVE")
    t["v"] += 1
    cache.put("tenant-a", "device-3", "h3", "site-a", "ACTIVE")

    assert cache.get("tenant-a", "device-1") is None
    assert cache.get("tenant-a", "device-2") is not None
    assert cache.get("tenant-a", "device-3") is not None


async def test_device_auth_cache_update_existing():
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    cache.put("tenant-a", "device-1", "h1", "site-a", "ACTIVE")
    cache.put("tenant-a", "device-1", "h2", "site-b", "ACTIVE")
    entry = cache.get("tenant-a", "device-1")
    assert entry["token_hash"] == "h2"
    assert entry["site_id"] == "site-b"


async def test_device_auth_cache_tenant_isolation():
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    cache.put("tenant-a", "device-1", "ha", "site-a", "ACTIVE")
    cache.put("tenant-b", "device-1", "hb", "site-b", "ACTIVE")
    assert cache.get("tenant-a", "device-1")["token_hash"] == "ha"
    assert cache.get("tenant-b", "device-1")["token_hash"] == "hb"


async def test_token_bucket_initial_state():
    bucket = TokenBucket()
    assert bucket.tokens == 0.0
    assert isinstance(bucket.updated, float)


async def test_validate_and_prepare_allows_within_rate(monkeypatch):
    now = {"v": 1000.0}
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: now["v"])
    conn = FakeConn(fetchrow_result=_active_row())
    pool = FakePool(conn)
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}
    for _ in range(5):
        result = await validate_and_prepare(
            pool=pool,
            auth_cache=cache,
            rate_buckets=buckets,
            tenant_id="tenant-a",
            device_id="device-1",
            site_id="site-a",
            msg_type="telemetry",
            provision_token="token-1",
            payload={"metrics": {"v": 1}},
            max_payload_bytes=8192,
            rps=5.0,
            burst=5.0,
            require_token=True,
        )
        assert result.success is True


async def test_validate_and_prepare_blocks_over_burst(monkeypatch):
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: 1000.0)
    conn = FakeConn(fetchrow_result=_active_row())
    result = None
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}
    for _ in range(4):
        result = await validate_and_prepare(
            pool=FakePool(conn),
            auth_cache=cache,
            rate_buckets=buckets,
            tenant_id="tenant-a",
            device_id="device-1",
            site_id="site-a",
            msg_type="telemetry",
            provision_token="token-1",
            payload={"metrics": {"v": 1}},
            max_payload_bytes=8192,
            rps=0.0,
            burst=3.0,
            require_token=True,
        )
    assert result == IngestResult(False, "RATE_LIMITED")


async def test_validate_and_prepare_refills_over_time(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: t["v"])
    conn = FakeConn(fetchrow_result=_active_row())
    pool = FakePool(conn)
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}
    for _ in range(3):
        res = await validate_and_prepare(
            pool=pool,
            auth_cache=cache,
            rate_buckets=buckets,
            tenant_id="tenant-a",
            device_id="device-1",
            site_id="site-a",
            msg_type="telemetry",
            provision_token="token-1",
            payload={"metrics": {"v": 1}},
            max_payload_bytes=8192,
            rps=1.0,
            burst=3.0,
            require_token=True,
        )
        assert res.success

    blocked = await validate_and_prepare(
        pool=pool,
        auth_cache=cache,
        rate_buckets=buckets,
        tenant_id="tenant-a",
        device_id="device-1",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=1.0,
        burst=3.0,
        require_token=True,
    )
    assert blocked.reason == "RATE_LIMITED"

    t["v"] += 1.1
    allowed = await validate_and_prepare(
        pool=pool,
        auth_cache=cache,
        rate_buckets=buckets,
        tenant_id="tenant-a",
        device_id="device-1",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=1.0,
        burst=3.0,
        require_token=True,
    )
    assert allowed.success is True


async def test_validate_and_prepare_token_bucket_capped_at_burst(monkeypatch):
    t = {"v": 1000.0}
    monkeypatch.setattr("services.shared.ingest_core.time.time", lambda: t["v"])
    conn = FakeConn(fetchrow_result=_active_row())
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}
    await validate_and_prepare(
        pool=FakePool(conn),
        auth_cache=cache,
        rate_buckets=buckets,
        tenant_id="tenant-a",
        device_id="device-1",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=1.0,
        burst=3.0,
        require_token=True,
    )
    t["v"] += 1000.0
    await validate_and_prepare(
        pool=FakePool(conn),
        auth_cache=cache,
        rate_buckets=buckets,
        tenant_id="tenant-a",
        device_id="device-1",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=1.0,
        burst=3.0,
        require_token=True,
    )
    assert buckets[("tenant-a", "device-1")].tokens <= 3.0


async def test_validate_and_prepare_concurrent_access():
    conn = FakeConn(fetchrow_result=_active_row())
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}

    async def _call():
        return await validate_and_prepare(
            pool=FakePool(conn),
            auth_cache=cache,
            rate_buckets=buckets,
            tenant_id="tenant-a",
            device_id="device-1",
            site_id="site-a",
            msg_type="telemetry",
            provision_token="token-1",
            payload={"metrics": {"v": 1}},
            max_payload_bytes=8192,
            rps=0.0,
            burst=10.0,
            require_token=True,
        )

    results = await asyncio.gather(*[_call() for _ in range(20)])
    success = sum(1 for r in results if r.success)
    assert 1 <= success <= 10
    assert any((not r.success and r.reason == "RATE_LIMITED") for r in results)


async def test_validate_and_prepare_valid_message_accepted():
    result, conn, _cache, _buckets = await _valid_ingest()
    assert result.success is True
    assert conn.fetchrow_calls == 1


async def test_validate_and_prepare_payload_too_large_rejected():
    result, _conn, _cache, _buckets = await _valid_ingest(
        payload={"x": "y" * 200},
        max_payload_bytes=20,
    )
    assert result == IngestResult(False, "PAYLOAD_TOO_LARGE")


async def test_validate_and_prepare_unregistered_device_rejected():
    conn = FakeConn(fetchrow_result=None)
    result = await validate_and_prepare(
        pool=FakePool(conn),
        auth_cache=DeviceAuthCache(),
        rate_buckets={},
        tenant_id="tenant-a",
        device_id="missing-device",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=10.0,
        burst=10.0,
        require_token=True,
    )
    assert result == IngestResult(False, "UNREGISTERED_DEVICE")


async def test_validate_and_prepare_revoked_device_rejected():
    conn = FakeConn(
        fetchrow_result={
            "site_id": "site-a",
            "status": "REVOKED",
            "provision_token_hash": _hash_token("token-1"),
        }
    )
    result = await validate_and_prepare(
        pool=FakePool(conn),
        auth_cache=DeviceAuthCache(),
        rate_buckets={},
        tenant_id="tenant-a",
        device_id="device-1",
        site_id="site-a",
        msg_type="telemetry",
        provision_token="token-1",
        payload={"metrics": {"v": 1}},
        max_payload_bytes=8192,
        rps=10.0,
        burst=10.0,
        require_token=True,
    )
    assert result == IngestResult(False, "DEVICE_REVOKED")


async def test_validate_and_prepare_site_mismatch_rejected():
    result, _conn, _cache, _buckets = await _valid_ingest(site_id="site-b")
    assert result == IngestResult(False, "SITE_MISMATCH")


async def test_validate_and_prepare_invalid_token_rejected():
    result, _conn, _cache, _buckets = await _valid_ingest(provision_token="bad-token")
    assert result == IngestResult(False, "TOKEN_INVALID")


async def test_validate_and_prepare_missing_token_rejected():
    result, _conn, _cache, _buckets = await _valid_ingest(provision_token=None, require_token=True)
    assert result == IngestResult(False, "TOKEN_MISSING")


async def test_validate_and_prepare_heartbeat_accepted():
    result, _conn, _cache, _buckets = await _valid_ingest(
        msg_type="heartbeat",
        payload={"site_id": "site-a", "metrics": {}},
    )
    assert result.success is True


async def test_validate_and_prepare_uses_cache_after_first_lookup():
    conn = FakeConn(fetchrow_result=_active_row())
    pool = FakePool(conn)
    cache = DeviceAuthCache(ttl_seconds=60, max_size=100)
    buckets = {}
    for _ in range(2):
        res = await validate_and_prepare(
            pool=pool,
            auth_cache=cache,
            rate_buckets=buckets,
            tenant_id="tenant-a",
            device_id="device-1",
            site_id="site-a",
            msg_type="telemetry",
            provision_token="token-1",
            payload={"metrics": {"v": 1}},
            max_payload_bytes=8192,
            rps=100.0,
            burst=100.0,
            require_token=True,
        )
        assert res.success is True
    assert conn.fetchrow_calls == 1


def _record(idx: int) -> TelemetryRecord:
    return TelemetryRecord(
        time=datetime.now(timezone.utc),
        tenant_id="tenant-a",
        device_id=f"device-{idx}",
        site_id="site-a",
        msg_type="telemetry",
        seq=idx,
        metrics={"value": idx},
    )


async def test_batch_writer_flushes_at_batch_size():
    conn = FakeConn()
    writer = TimescaleBatchWriter(pool=FakePool(conn), batch_size=2, flush_interval_ms=10000)
    await writer.add(_record(1))
    assert writer.get_stats()["pending_records"] == 1
    await writer.add(_record(2))
    stats = writer.get_stats()
    assert stats["pending_records"] == 0
    assert stats["records_written"] == 2
    assert len(conn.executemany_calls) == 1


async def test_batch_writer_flushes_on_interval():
    conn = FakeConn()
    writer = TimescaleBatchWriter(pool=FakePool(conn), batch_size=50, flush_interval_ms=50)
    await writer.start()
    await writer.add(_record(1))
    await asyncio.sleep(0.12)
    await writer.stop()
    stats = writer.get_stats()
    assert stats["records_written"] >= 1
    assert stats["batches_flushed"] >= 1


async def test_batch_writer_large_batch_uses_copy():
    conn = FakeConn()
    writer = TimescaleBatchWriter(pool=FakePool(conn), batch_size=101, flush_interval_ms=10000)
    await writer.add_many([_record(i) for i in range(101)])
    assert len(conn.copy_calls) == 1
