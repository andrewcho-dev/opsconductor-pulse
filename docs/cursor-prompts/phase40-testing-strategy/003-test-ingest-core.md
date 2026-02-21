# 003: Unit Tests for shared/ingest_core.py

## Why
`services/shared/ingest_core.py` (335 LOC) has ZERO tests. It contains `DeviceAuthCache`, `TokenBucket`, `TimescaleBatchWriter`, and `validate_and_prepare` — critical infrastructure used by every telemetry message in the system. A bug here silently drops data or allows unauthorized writes.

## Source File
Read: `services/shared/ingest_core.py`

## Pattern to Follow
Read: `tests/unit/test_customer_route_handlers.py` (lines 1-80) for the FakeConn/FakePool/AsyncMock pattern.

## Test File to Create
`tests/unit/test_ingest_core.py`

## Test Scenarios (~25 tests)

### TokenBucket (6 tests)
```
test_token_bucket_allows_within_rate
  - Create bucket with rps=5, burst=10
  - Call allow() 5 times rapidly → all return True

test_token_bucket_blocks_over_burst
  - Create bucket with rps=1, burst=3
  - Call allow() 4 times → 4th returns False

test_token_bucket_refills_over_time
  - Create bucket, exhaust burst
  - Advance time by 1 second (mock time.time)
  - Call allow() → returns True (refilled)

test_token_bucket_max_tokens_capped_at_burst
  - Create bucket, wait long time
  - Tokens should not exceed burst value

test_token_bucket_concurrent_access
  - Multiple concurrent allow() calls don't corrupt state

test_token_bucket_cleanup_stale_entries
  - Add entries, advance time past cleanup threshold
  - Verify stale entries are removed
```

### DeviceAuthCache (7 tests)
```
test_cache_miss_returns_none
  - Empty cache, get() returns None

test_cache_set_and_get
  - set(tenant, device, data), get() returns data

test_cache_ttl_expiry
  - set() then advance time past TTL
  - get() returns None (expired)

test_cache_within_ttl_returns_data
  - set() then advance time within TTL
  - get() returns data

test_cache_max_size_eviction
  - Set max_size=2, add 3 entries
  - Oldest entry evicted

test_cache_update_existing
  - set() twice for same key
  - get() returns latest data

test_cache_different_tenants_isolated
  - set(tenant-a, device-1, data_a)
  - set(tenant-b, device-1, data_b)
  - get(tenant-a, device-1) returns data_a (not data_b)
```

### validate_and_prepare (10 tests)
```
test_valid_telemetry_message_accepted
  - Valid tenant, device, site, token, metrics
  - Returns TelemetryRecord with correct fields

test_missing_site_id_rejected
  - Payload without site_id → rejected with "MISSING_SITE_ID"

test_tenant_mismatch_rejected
  - Topic says tenant-a, payload says tenant-b
  - Rejected with "TENANT_MISMATCH_TOPIC_VS_PAYLOAD"

test_unregistered_device_rejected
  - Device not in registry, auto_provision=False
  - Rejected with "UNREGISTERED_DEVICE"

test_revoked_device_rejected
  - Device with status="REVOKED"
  - Rejected with "DEVICE_REVOKED"

test_invalid_token_rejected
  - Token hash doesn't match registry
  - Rejected with "TOKEN_INVALID"

test_missing_token_rejected
  - REQUIRE_TOKEN=True, no token provided
  - Rejected with "TOKEN_MISSING"

test_rate_limited_rejected
  - Exhaust rate limit bucket
  - Rejected with "RATE_LIMITED"

test_payload_too_large_rejected
  - Payload > MAX_PAYLOAD_BYTES
  - Rejected with "PAYLOAD_TOO_LARGE"

test_heartbeat_message_accepted
  - msg_type="heartbeat", empty metrics
  - Returns TelemetryRecord with msg_type="heartbeat"
```

### TimescaleBatchWriter (2 tests)
```
test_batch_writer_flushes_at_batch_size
  - Add BATCH_SIZE records
  - Verify flush is called with all records

test_batch_writer_flushes_on_interval
  - Add 1 record, wait FLUSH_INTERVAL_MS
  - Verify flush is called
```

## Implementation Notes
- Mock `asyncpg` connections using FakeConn pattern from `tests/unit/test_customer_route_handlers.py`
- Mock `time.time()` for TTL/refill tests using `monkeypatch.setattr`
- Use markers: `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- Import from `services/shared/ingest_core` — check `tests/conftest.py` (11KB) for sys.path setup
- `pytest.ini` sets `testpaths = tests` and `asyncio_mode = auto`
- The `validate_and_prepare` function signature takes: `pool, tenant_id, device_id, provision_token, msg_type, payload_dict, client_ip`
- `TokenBucket` constructor: `__init__(self, rps, burst)` with `allow()` method
- `DeviceAuthCache` constructor: `__init__(self, ttl_seconds, max_size)` with `get(tenant, device)` / `set(tenant, device, data)` methods
- `TimescaleBatchWriter` is async — `__init__(self, pool, batch_size, flush_interval_ms)` with `add(record)` and `flush()` methods
- The module also has `TelemetryRecord` and `IngestResult` dataclasses — test these as part of `validate_and_prepare` tests

## Verify
```bash
pytest tests/unit/test_ingest_core.py -v
```
