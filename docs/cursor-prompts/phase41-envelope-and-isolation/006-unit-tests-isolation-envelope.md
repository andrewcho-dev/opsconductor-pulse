# Prompt 006 — Unit Tests for Isolation Fixes + Envelope Version Handling

## Context

Prompts 001-004 made security and correctness fixes. This prompt adds unit tests to lock those fixes in place so they can never regress silently.

## Your Task

Add unit tests to the existing test suite in `tests/unit/`. Follow the existing patterns exactly:
- Use `FakeConn` / `FakePool` for DB mocking
- Use `monkeypatch` and `AsyncMock`
- All tests get markers: `pytestmark = [pytest.mark.unit, pytest.mark.asyncio]`
- Reference pattern: `tests/unit/test_customer_route_handlers.py`

### Test File 1: `tests/unit/test_ingest_rls_enforcement.py`

Tests for the RLS role-setting fix (prompt 002):

1. **`test_mqtt_ingest_sets_pulse_app_role`** — mock the DB connection, process a valid MQTT message through the ingest path, assert that `SET LOCAL ROLE pulse_app` was executed on the connection before any INSERT/COPY
2. **`test_http_ingest_sets_pulse_app_role`** — same for HTTP ingest path
3. **`test_ingest_role_is_local_not_session`** — assert the role set is `LOCAL` scoped, not `SESSION` scoped

### Test File 2: `tests/unit/test_ingest_subscription_enforcement.py`

Tests for subscription enforcement (prompt 003):

1. **`test_mqtt_ingest_rejects_suspended_subscription`** — mock device auth cache to return a device with SUSPENDED subscription; assert the message is rejected with reason `SUBSCRIPTION_SUSPENDED` and written to `quarantine_events`
2. **`test_http_ingest_rejects_suspended_subscription`** — same for HTTP path
3. **`test_active_subscription_allows_ingest`** — happy path, ACTIVE subscription, message is accepted
4. **`test_suspended_subscription_does_not_write_telemetry`** — assert that the `telemetry` table INSERT/COPY is never called when subscription is SUSPENDED

### Test File 3: `tests/unit/test_envelope_version.py`

Tests for envelope version field (prompt 004):

1. **`test_valid_payload_with_version_1`** — payload with `version: "1"` passes `validate_and_prepare()`
2. **`test_valid_payload_without_version`** — payload without `version` field defaults to v1 and passes
3. **`test_unknown_version_rejected`** — payload with `version: "2"` is rejected with `UNSUPPORTED_ENVELOPE_VERSION`
4. **`test_unknown_version_quarantined`** — rejected payload is written to `quarantine_events` with correct reason code
5. **`test_version_field_stored_in_telemetry`** — when version is present, it is stored (or at minimum not dropped silently)

## Acceptance Criteria

- [ ] All three test files exist in `tests/unit/`
- [ ] All tests use `pytest.mark.unit` and `pytest.mark.asyncio`
- [ ] `pytest -m unit -v` passes with no failures
- [ ] No real DB connections — all DB calls mocked with FakeConn/FakePool
- [ ] Each test has a clear docstring explaining what it verifies
