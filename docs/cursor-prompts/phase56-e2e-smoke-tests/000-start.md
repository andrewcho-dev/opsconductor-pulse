# Phase 56: E2E Smoke Test Harness

## What Exists

- Playwright E2E infrastructure in `tests/e2e/conftest.py`:
  - `authenticated_customer_page` fixture — logged in as customer1
  - `authenticated_operator_page` fixture — logged in as operator1
  - `db_connection` fixture — direct asyncpg connection
  - `RUN_E2E` environment variable gate
  - Base URL from `UI_BASE_URL` env var
- Existing E2E tests: login, dashboard, navigation, integrations, subscriptions, visual regression
- `pytest.mark.e2e` marker (or similar) should be used

## What This Phase Adds

A focused **smoke test suite** (`tests/e2e/test_smoke.py`) that verifies:
1. The compose stack is healthy end-to-end
2. Core user flows work after a deployment

The smoke suite is fast (< 60 seconds), non-destructive, and safe to run against any environment.

## Smoke Test Scope

| Test | Description |
|------|-------------|
| stack health | All service /healthz endpoints return 200 |
| customer login | Can log in as customer1, sees dashboard |
| device list | /devices page loads, shows device table |
| alert list | /alerts page loads |
| sites page | /sites page loads |
| integrations page | /integrations page loads |
| operator login | Can log in as operator1, sees operator dashboard |
| API auth | Unauthenticated API request returns 401 |
| alert rule create | Can navigate to rule create form |
| delivery log | /delivery-log page loads |

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Smoke test file (stack health + page load tests) |
| 002 | CI integration (pytest marker, GitHub Actions job) |
| 003 | Verify |

## Key Files

- `tests/e2e/conftest.py` — existing fixtures (read before writing)
- `tests/e2e/test_smoke.py` — new (prompt 001)
- `.github/workflows/` — CI wiring (prompt 002)
