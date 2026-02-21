# Prompt 004 — Unit Tests

## File: `tests/unit/test_rate_limiting.py`

Read `services/ui_iot/app.py` and `services/ui_iot/routes/customer.py`.
Use `httpx.AsyncClient` with the FastAPI test app.

Tests using `@pytest.mark.unit` and `@pytest.mark.asyncio`:

1. `test_rate_limit_key_uses_tenant_id` — request with tenant_id in state → key = tenant_id
2. `test_rate_limit_key_falls_back_to_ip` — request with no tenant_id → key = remote address
3. `test_429_response_is_json` — mock limiter to raise RateLimitExceeded → response is JSON with `detail` key
4. `test_429_has_retry_after_header` — 429 response includes `Retry-After` header
5. `test_health_endpoint_not_rate_limited` — GET /healthz has no limiter decorator
6. `test_rate_limit_env_var_default` — `RATE_LIMIT_CUSTOMER` defaults to "100/minute" when not set

All `@pytest.mark.unit` and `@pytest.mark.asyncio`.

## Acceptance Criteria

- [ ] 6 tests pass under `pytest -m unit -v`
- [ ] No existing tests broken
