# Phase 141 — Fix 30 Broken Test Files

## Goal

Fix 30 test files that fail during `pytest --collect-only` due to:
1. Imports of deleted `delivery_worker` modules (3 files)
2. Missing environment variables at module-level import time (27 files)

## Execution Order

| Step | File | What |
|------|------|------|
| 1 | `001-delete-dead-test-files.md` | Delete 3 test files for removed services |
| 2 | `002-add-conftest-env-defaults.md` | Add missing env var defaults to conftest.py |
| 3 | `003-convert-environ-to-getenv.md` | Convert 13 `os.environ[]` calls to `os.getenv()` |
| 4 | `004-cleanup-pycache.md` | Remove __pycache__ from deleted services |
| 5 | `005-verify-and-fix-remaining.md` | Run test collection, fix any stragglers |

## Key Constraint

- Every `os.environ["KEY"]` at module level must become `os.getenv("KEY", default)`
- Defaults must match what `tests/conftest.py` already sets (e.g., `PG_PASS` → `"iot_dev"`)
- Production deploys always set these explicitly via `.env` / compose, so defaults are safe

## Verification

```bash
pytest tests/unit/ -m unit --co -q 2>&1 | tail -5
# Should show "X tests collected" with 0 errors
```
