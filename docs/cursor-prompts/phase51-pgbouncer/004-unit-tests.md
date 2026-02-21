# Prompt 004 — Unit Tests

## File: `tests/unit/test_pgbouncer_bypass.py`

Write tests verifying the LISTEN/NOTIFY bypass logic. Use FakeConn/FakePool pattern.

Tests:
1. `test_listen_uses_notify_conn` — verify that `add_listener` is called on `notify_conn`, not on a pool connection
2. `test_queries_use_pool` — verify regular DB queries use pool.acquire(), not notify_conn
3. `test_notify_conn_fallback_to_database_url` — when `NOTIFY_DATABASE_URL` not set, falls back to `DATABASE_URL`
4. `test_notify_conn_closed_on_shutdown` — shutdown calls `notify_conn.close()`

All tests `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 4 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
