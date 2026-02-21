# 004: Unit Tests for shared/rate_limiter.py

## Why
`services/shared/rate_limiter.py` (232 LOC) has ZERO tests. It enforces per-device, per-IP, and global rate limits on the HTTP ingest path. If broken, it either blocks legitimate traffic or allows DoS attacks through.

## Source File
Read: `services/shared/rate_limiter.py`

## Test File to Create
`tests/unit/test_rate_limiter_unit.py`

(Named `_unit` to avoid collision with any existing rate limiter test file.)

## Test Scenarios (~15 tests)

### SlidingWindowCounter / Rate Limiter Core (5 tests)
```
test_allows_requests_within_limit
  - Configure limit=10 per window=60s
  - Make 10 requests → all allowed

test_blocks_requests_over_limit
  - Configure limit=5 per window=60s
  - Make 6 requests → 6th blocked

test_window_slides_and_allows_after_expiry
  - Configure limit=2 per window=1s
  - Make 2 requests (exhausted)
  - Advance time by 1.1 seconds
  - Make 1 request → allowed

test_different_keys_tracked_independently
  - Configure limit=1
  - Request from key-A → allowed
  - Request from key-B → allowed (separate counter)
  - Request from key-A → blocked
```

### Device-Level Rate Limiting (3 tests)
```
test_device_rate_limit_per_device
  - Configure device limit=2/1s
  - 2 requests for device-1 → allowed
  - 3rd for device-1 → blocked
  - 1st for device-2 → allowed (different device)

test_unknown_device_gets_stricter_limit
  - Unknown device IP limit: 10/60s
  - Known device IP limit: 200/1s
  - Verify unknown device hits limit faster

test_device_rate_limit_returns_429
  - Verify the correct HTTP status code / error message
```

### IP-Level Rate Limiting (3 tests)
```
test_ip_rate_limit_known_device
  - Configure IP-known limit=200/1s
  - 200 requests → allowed
  - 201st → blocked

test_ip_rate_limit_unknown_device
  - Configure IP-unknown limit=10/60s
  - 10 requests → allowed
  - 11th → blocked

test_ip_extracted_from_x_forwarded_for
  - Request with X-Forwarded-For header
  - Rate limit applied to forwarded IP, not socket IP
```

### Global Rate Limiting (2 tests)
```
test_global_limit_returns_503
  - Configure global limit=10000/1s
  - Exceed it → returns 503 Service Unavailable (not 429)

test_global_limit_blocks_all_sources
  - Exceed global limit
  - Even new IP/device combinations blocked
```

### Edge Cases (2 tests)
```
test_concurrent_rate_limit_checks
  - Multiple simultaneous requests don't corrupt counters

test_cleanup_removes_expired_entries
  - Add many entries, advance time
  - Verify memory doesn't grow unboundedly
```

## Implementation Notes
- Mock `time.time()` or `time.monotonic()` for time-dependent tests using `monkeypatch.setattr`
- Use markers: `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- The module contains `RateLimiter` and `SlidingWindow` classes
- `RateLimiter` has methods for per-device, per-IP, and global checks
- `SlidingWindow` tracks counts over a time window — constructor takes `(limit, window_seconds)`
- The rate limiter is configured via env vars: `DEVICE_RATE_LIMIT`, `IP_RATE_LIMIT_KNOWN`, `IP_RATE_LIMIT_UNKNOWN`, `GLOBAL_RATE_LIMIT` — mock with `monkeypatch.setenv` or `os.getenv`
- Uses `threading` for concurrent access safety
- Follow import patterns from `tests/unit/test_customer_route_handlers.py`
- The module path is `services/shared/rate_limiter.py` — check conftest.py for path setup

## Verify
```bash
pytest tests/unit/test_rate_limiter_unit.py -v
```
