# Phase 40: Testing Strategy — Eliminate Test Debt, Enforce Quality Gates

## Goal
Eliminate all testing technical debt and establish enforcement mechanisms so coverage never regresses.

## Current State
- **E2E**: 30 of 85 tests failing (stale selectors, route changes, auth issues)
- **Backend unit coverage**: ~21% overall. Critical modules (evaluator, ingest, rate limiter) have ZERO tests
- **Frontend tests**: 9 files, 36 tests. Not in CI pipeline
- **Coverage enforcement**: `.coveragerc` has `fail_under = 60` but `pytest.ini` overrides with `--cov-fail-under=0`

## Target State
- **E2E**: 85/85 passing
- **Backend unit coverage**: 50%+ overall, 40%+ on critical modules
- **Frontend tests**: 70+ tests covering core pages, hooks, and auth
- **CI**: Frontend tests in pipeline, coverage gates enforced
- **Ratchet**: Coverage can never decrease — enforced in CI and pre-commit

## Execution Order

Execute prompts **in numerical order**. Each prompt is self-contained.

| Prompt | Description | New Tests | Priority |
|--------|-------------|-----------|----------|
| 001 | Fix E2E tests: add missing element IDs to frontend | 0 (fixes 17) | CRITICAL |
| 002 | Fix E2E tests: routes, auth, component selectors | 0 (fixes 13) | CRITICAL |
| 003 | Unit tests: shared/ingest_core.py (335 LOC) | ~25 | CRITICAL |
| 004 | Unit tests: shared/rate_limiter.py (232 LOC) | ~15 | CRITICAL |
| 005 | Unit tests: evaluator_iot/evaluator.py (580 LOC) | ~20 | CRITICAL |
| 006 | Unit tests: routes/system.py (859 LOC) | ~20 | HIGH |
| 007 | Unit tests: routes/users.py (948 LOC) + routes/ingest.py (336 LOC) | ~30 | HIGH |
| 008 | Unit tests: services (keycloak, subscription, dispatcher, snmp) | ~47 | HIGH |
| 009 | Frontend test expansion | ~36 | MEDIUM |
| 010 | CI: add frontend tests to GitHub Actions | 0 | HIGH |
| 011 | Coverage ratchet: thresholds + enforcement | 0 | HIGH |

## Verification After All Prompts Complete

```bash
# Backend unit tests
pytest -m unit -v

# Frontend tests
cd frontend && npm run test -- --run && cd ..

# E2E tests (requires running services)
RUN_E2E=1 pytest -m e2e -v

# Coverage check
python scripts/check_coverage.py

# Frontend build
cd frontend && npm run build && cd ..
```

## Patterns to Follow

**Backend tests**: Follow `tests/unit/test_customer_route_handlers.py` — uses FakeConn/FakePool, monkeypatch, AsyncMock, httpx.ASGITransport. All tests use markers:
```python
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
```

**Frontend tests**: Follow `frontend/src/hooks/use-devices.test.ts` — uses vi.mock(), renderHook with QueryClient wrapper (retry: false), @testing-library/react. All tests use Vitest globals (describe, it, expect).

**E2E tests**: Follow `tests/e2e/conftest.py` — uses Playwright with `authenticated_customer_page` / `authenticated_operator_page` fixtures. Auth goes through Keycloak OAuth flow. Session cookie: `pulse_session`.

## Key File Paths

### Backend Source (under `services/`)
- `services/shared/ingest_core.py` — TokenBucket, DeviceAuthCache, TimescaleBatchWriter, validate_and_prepare
- `services/shared/rate_limiter.py` — RateLimiter, SlidingWindow
- `services/evaluator_iot/evaluator.py` — evaluate_threshold, normalize_value, fetch_rollup_timescaledb
- `services/ui_iot/routes/system.py` — 8 operator system endpoints
- `services/ui_iot/routes/users.py` — 20+ user management endpoints
- `services/ui_iot/routes/ingest.py` — 3 HTTP ingest endpoints
- `services/ui_iot/services/keycloak_admin.py` — Keycloak admin API
- `services/ui_iot/services/subscription.py` — subscription management
- `services/ui_iot/services/alert_dispatcher.py` — AlertPayload, dispatch_alert, DeliveryResult
- `services/ui_iot/services/snmp_sender.py` — SNMPSender class, send_alert_trap

### Frontend Source (under `frontend/src/`)
- `frontend/src/app/router.tsx` — route definitions, RequireOperator/RequireCustomer guards
- `frontend/src/services/auth/AuthProvider.tsx` — Keycloak auth, role extraction
- `frontend/src/features/devices/DeviceListPage.tsx` — device list
- `frontend/src/features/devices/DeviceDetailPage.tsx` — device detail
- `frontend/src/features/operator/OperatorDevices.tsx` — operator device view
- `frontend/src/features/integrations/{WebhookPage,SnmpPage,EmailPage,MqttPage}.tsx`

### Existing Tests
- `tests/unit/` — 20+ files (test_customer_route_handlers, test_dispatcher_logic, test_delivery_snmp_sender, etc.)
- `tests/e2e/` — 11 files (test_integration_crud, test_login_flow, test_navigation, etc.)
- `frontend/src/**/*.test.{ts,tsx}` — 9 files (hooks, components, services)

### Config
- `pytest.ini` — test config with `--cov-fail-under=0` (to fix)
- `.coveragerc` — `fail_under = 60`
- `scripts/check_coverage.py` — critical module thresholds
- `.github/workflows/test.yml` — CI (5 jobs: unit, integration, e2e, lint, benchmarks)
- `.pre-commit-config.yaml` — pytest + ruff hooks
- `frontend/vitest.config.ts` — jsdom env, setupTests.ts, coverage v8
