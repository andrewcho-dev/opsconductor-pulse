# Prompt 004 — Unit Tests

## File: `tests/unit/test_jwks_cache.py`

Read `services/shared/jwks_cache.py`. Write tests using `pytest.mark.unit` and `pytest.mark.asyncio`.

Use `unittest.mock.AsyncMock` and `patch` to mock `httpx.AsyncClient`.

Tests:

1. `test_get_keys_fetches_on_first_call` — cache empty → fetches JWKS → returns keys
2. `test_get_keys_returns_cache_when_fresh` — cache populated, not stale → no HTTP call
3. `test_get_keys_refetches_when_stale` — cache stale (mock `is_stale` True) → refetches
4. `test_force_refresh_refetches` — always fetches even if fresh
5. `test_retry_on_failure` — first 2 attempts raise exception, 3rd succeeds → returns keys
6. `test_all_retries_fail_raises` — all attempts raise → raises exception
7. `test_is_stale_true_when_old` — `_fetched_at` set to long ago → `is_stale()` returns True
8. `test_is_stale_false_when_fresh` — `_fetched_at` = now → `is_stale()` returns False
9. `test_concurrent_get_keys_single_fetch` — two concurrent `get_keys()` calls → only one HTTP request (lock works)

All tests `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] All 9 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
