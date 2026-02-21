# Phase 203 — Unit Test DB Isolation + WS Token Fallback Removal

## Goal

Fix the 442 unit tests that fail with `asyncpg.exceptions.InvalidPasswordError` because they make real database connections instead of using mocks. Also remove the deprecated `?token=` WebSocket fallback that has been sitting with a removal comment since phase 194.

## Current State (problem)

1. **442 unit test failures**: Tests marked `@pytest.mark.unit` are making real asyncpg connections. The `patch_route_connection_contexts` autouse fixture in `conftest.py` patches most routes but misses some test modules. Without a running PostgreSQL with the correct password, these tests error out.
2. **WS `?token=` fallback**: `services/ui_iot/routes/api_v2.py` still accepts `?token=<JWT>` in WebSocket upgrade URLs. A deprecation comment was added in phase 194 with a note to remove in phase 203. That's now.

## Target State

- All `@pytest.mark.unit` tests pass without a running database.
- `pytest -m unit -q` shows 0 errors (only pass/fail, no collection or runtime errors).
- `?token=` fallback removed from the WebSocket upgrade handler entirely.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-identify-unmocked-tests.md` | Find which test modules bypass the DB mock | — |
| 2 | `002-fix-db-mock-coverage.md` | Extend mock coverage or reclassify tests | Step 1 |
| 3 | `003-remove-ws-token-fallback.md` | Remove `?token=` from WebSocket handler | — |
| 4 | `004-update-documentation.md` | Update docs | Steps 1–3 |

## Verification

```bash
pytest -m unit -q 2>&1 | tail -5
# Must show 0 errors. Pass/fail counts only.

grep -n 'token=' services/ui_iot/routes/api_v2.py
# Must return zero results for the ?token= query param handling
```

## Documentation Impact

- `docs/development/testing.md` — Note that unit tests must not make real DB connections
- `docs/api/websocket.md` — Remove any mention of ?token= auth flow
