# Phase 196 — Backend Exception Handling and Race Conditions

## Goal

Fix three classes of reliability problems: (1) bare `except Exception` handlers that swallow errors and hide failures, (2) a race condition on NATS client initialization, and (3) the audit logger holding a lock across I/O. These are not security vulnerabilities but they make the system hard to debug in production and can cause subtle data loss.

## Current State (problem)

1. **Bare excepts**: 30+ `except Exception: pass` or `except Exception: logger.warning(...)` across `ingest_iot`, `evaluator_iot`, and `ui_iot`. Fatal errors (OOM, pool exhaustion) are silently suppressed.
2. **NATS race**: `ui_iot/app.py:533-539` initializes the NATS client lazily with no lock — two concurrent requests can both create connections.
3. **Audit logger lock**: `shared/audit.py:154-176` holds `self._lock` while doing a database COPY, blocking all event producers during I/O.

## Target State

- Exception handlers distinguish between recoverable errors (log + continue) and fatal errors (log + reraise or crash).
- NATS client is initialized once at startup, not lazily on first request.
- Audit logger releases its lock after draining the buffer, then writes to the database outside the lock.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-fix-nats-race-condition.md` | Move NATS init to app startup | — |
| 2 | `002-fix-audit-logger-lock.md` | Release lock before I/O in audit logger | — |
| 3 | `003-fix-bare-excepts-ingest.md` | Fix bare excepts in `ingest_iot` | — |
| 4 | `004-fix-bare-excepts-evaluator.md` | Fix bare excepts in `evaluator_iot` | — |
| 5 | `005-fix-bare-excepts-ui-iot.md` | Fix bare excepts in `ui_iot` | — |
| 6 | `006-update-documentation.md` | Update affected docs | Steps 1–5 |

## Verification

```bash
# No bare pass in except blocks
grep -rn 'except.*:\s*$' services/ -A1 | grep -E '^\s*pass\s*$'
# Should return very few or zero results

# NATS client initialized at startup, not lazily
grep -n '_nats_client.*None' services/ui_iot/app.py
# Should not show lazy initialization inside request handlers
```

## Documentation Impact

- No external-facing docs change. Update `docs/development/conventions.md` if it exists with error handling guidelines.
