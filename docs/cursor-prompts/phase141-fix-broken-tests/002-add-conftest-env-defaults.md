# Task 2: Add Missing Env Var Defaults to conftest.py

## Context

`tests/conftest.py` sets `PG_PASS` via `os.environ.setdefault` on line 26, but it is missing defaults for `KEYCLOAK_ADMIN_PASSWORD` and `DATABASE_URL`. These are needed because:

- `services/ui_iot/services/keycloak_admin.py:22` uses `os.environ["KEYCLOAK_ADMIN_PASSWORD"]` at module level
- `services/subscription_worker/worker.py:39` uses `os.environ["DATABASE_URL"]` at module level
- The import chain in conftest.py (`from app import app` on line 40) triggers these imports

## File to Edit

`tests/conftest.py`

## Change

Add two `setdefault` lines **after line 26** (after the existing `PG_PASS` setdefault, before line 27 which is blank):

**Before (lines 26-27):**
```python
os.environ.setdefault("PG_PASS", "iot_dev")
```

**After:**
```python
os.environ.setdefault("PG_PASS", "iot_dev")
os.environ.setdefault("KEYCLOAK_ADMIN_PASSWORD", "admin")
os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("ADMIN_KEY", "test-admin-key")
```

## Why These Defaults

| Variable | Default | Reason |
|----------|---------|--------|
| `KEYCLOAK_ADMIN_PASSWORD` | `"admin"` | Matches standard dev/test Keycloak setup |
| `DATABASE_URL` | `""` | Prevents KeyError; subscription_worker tests mock the pool anyway |
| `ADMIN_KEY` | `"test-admin-key"` | Prevents KeyError in provision_api/app.py; tests mock auth anyway |

These must be set **before** any service imports happen (the imports start at line 35).
