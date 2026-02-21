# Prompt 005 — Unit Tests

## File: `tests/unit/test_webhook_test_send.py`

Read a passing test file in `tests/unit/` for FakeConn/FakePool pattern.
Use `unittest.mock.patch` for httpx calls.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_test_send_success` — fetchrow returns webhook integration, httpx returns 200 → success=True, http_status=200
2. `test_test_send_not_found` — fetchrow returns None → 404
3. `test_test_send_not_webhook_type` — integration type='email' → 400
4. `test_test_send_disabled` — enabled=False → 400
5. `test_test_send_no_url` — config_json has no url → 400
6. `test_test_send_connection_error` — httpx raises exception → success=False, error in response
7. `test_list_delivery_jobs_default` — fetch returns rows → 200, jobs list
8. `test_list_delivery_jobs_filter_status` — ?status=FAILED → WHERE clause includes status
9. `test_list_delivery_jobs_invalid_status` — ?status=BOGUS → 400
10. `test_get_job_attempts_success` — job found, attempts returned
11. `test_get_job_attempts_not_found` — job not found → 404

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 11 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
