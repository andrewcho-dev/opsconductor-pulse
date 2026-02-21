# Completion Report: boto3 Bootstrap + WS Legacy Comment + `sites` RLS

**From:** Cursor Agent  
**Date:** 2026-02-20  
**Sequence:** 000007  
**In response to:** `000011`

---

## 1) boto3 test bootstrap fix

### Diagnosis run

Executed:

```bash
pytest -m unit --collect-only 2>&1 | rg 'ERROR|ImportError|ModuleNotFound' | head -20
rg 'import boto3|from boto3' services/
```

Findings:
- Initial collector failure was `ModuleNotFoundError: No module named 'boto3'` during `conftest` import path.
- `boto3` imports were found in:
  - `services/ui_iot/routes/exports.py`
  - `services/ops_worker/workers/export_worker.py`

### Fix applied

Applied **soft import guards** in both files:
- wrapped `boto3` / `botocore.config.Config` imports in `try/except ImportError`
- added runtime guard in `get_s3_client()`:
  - raises explicit `RuntimeError("boto3 is required for S3 export operations...")` when missing

This removes hard import-time failure while preserving explicit runtime failure for S3 features if dependency is absent.

### Additional fail-fast env blockers encountered and addressed in tests

After boto3 was fixed, collection failed on required env vars introduced by earlier hardening. Added test defaults in `tests/conftest.py`:
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `MQTT_INTERNAL_AUTH_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SMTP_PASSWORD`

Current collection blocker is now unrelated to boto3:
- `ImportError: cannot import name 'get_client_ip' from 'routes.ingest'` in `tests/unit/test_ingest_routes.py`

---

## 2) WS `?token=` deprecation comment

Added in `services/ui_iot/routes/api_v2.py` at the token fallback branch:

```python
# LEGACY: ?token= URL param retained for backward compatibility.
# Remove in phase203 once confirmed no active clients use it.
# Added: 2026-02-20
```

Note: fallback implementation exists in `routes/api_v2.py` (not `app.py`).

---

## 3) `sites` table RLS resolution

### Verification

Located table definition:
- `db/migrations/052_seed_test_data.sql`
- `sites` includes `tenant_id TEXT NOT NULL ...`

### Fix applied

Updated `db/migrations/118_rls_gap_fixes.sql` to add `sites` RLS:
- `ALTER TABLE sites ENABLE ROW LEVEL SECURITY;`
- `ALTER TABLE sites FORCE ROW LEVEL SECURITY;`
- drop/create `tenant_isolation` policy on `sites`

Updated documentation:
- `docs/architecture/rls-inventory.md`
  - `sites` changed `REVIEW -> PROTECTED`
  - summary counts updated to:
    - `PROTECTED: 61`
    - `EXEMPT: 21`
    - `REVIEW: 0`
    - `GAP (unfixed): 0`
- `docs/architecture/tenant-isolation.md`
  - coverage line updated to `61/21/0/0`

---

## 4) Test execution results

Executed:

```bash
pytest -m unit -q 2>&1 | tail -20
pytest -m integration -q 2>&1 | tail -20
```

Result summary:
- boto3 import collection error is resolved.
- test run still exits non-zero due existing unrelated collection error:
  - `tests/unit/test_ingest_routes.py` importing missing symbol `get_client_ip` from `routes.ingest`
- coverage gate also fails in these filtered runs (`19.11% < required 30%`) because collection aborts early.

---

## Files changed for this execution

- `services/ui_iot/routes/exports.py`
- `services/ops_worker/workers/export_worker.py`
- `services/ui_iot/routes/api_v2.py`
- `db/migrations/118_rls_gap_fixes.sql`
- `docs/architecture/rls-inventory.md`
- `docs/architecture/tenant-isolation.md`
- `tests/conftest.py`
