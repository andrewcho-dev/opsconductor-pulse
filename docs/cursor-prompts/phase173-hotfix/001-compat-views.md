# Task 1: Create Compatibility Views + Fix Error Handling

## 1. Create Migration `db/migrations/116_metric_compat_views.sql`

This migration creates backward-compatibility views for the two metric tables that were renamed in migration 115 but didn't get views (unlike `sensors` and `device_connections`).

```sql
-- Migration 116: Backward-compat views for deprecated metric tables
-- Phase 173 migration 115 renamed these tables but forgot compatibility views.
-- The metrics/reference endpoint and other code still query by old names.

BEGIN;

-- ============================================================
-- normalized_metrics: view over the renamed table
-- ============================================================

CREATE OR REPLACE VIEW normalized_metrics AS
SELECT
    id,
    tenant_id,
    normalized_name,
    display_unit,
    description,
    expected_min,
    expected_max,
    created_at,
    updated_at
FROM _deprecated_normalized_metrics;

GRANT SELECT ON normalized_metrics TO pulse_app;

-- ============================================================
-- metric_mappings: view over the renamed table
-- ============================================================

CREATE OR REPLACE VIEW metric_mappings AS
SELECT
    id,
    tenant_id,
    raw_metric,
    normalized_name,
    multiplier,
    offset_value,
    created_at
FROM _deprecated_metric_mappings;

GRANT SELECT ON metric_mappings TO pulse_app;

COMMIT;
```

Write this file exactly as shown to `db/migrations/116_metric_compat_views.sql`.

---

## 2. Add try/except to `get_metrics_reference`

**File:** `services/ui_iot/routes/metrics.py`

The `get_metrics_reference` endpoint (line 16-81) is the only endpoint in the file without a `try/except` wrapper. Add one to match every other endpoint:

```python
# OLD (lines 16-81):
@router.get("/metrics/reference")
async def get_metrics_reference(pool=Depends(get_db_pool)):
    """Return discovered raw metrics, mappings, and normalized metrics."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        raw_rows = await conn.fetch(...)
        mapping_rows = await conn.fetch(...)
        normalized_rows = await conn.fetch(...)

    # ... processing ...
    return { ... }

# NEW:
@router.get("/metrics/reference")
async def get_metrics_reference(pool=Depends(get_db_pool)):
    """Return discovered raw metrics, mappings, and normalized metrics."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            raw_rows = await conn.fetch(...)
            mapping_rows = await conn.fetch(...)
            normalized_rows = await conn.fetch(...)
    except Exception:
        logger.exception("Failed to fetch metrics reference")
        raise HTTPException(status_code=500, detail="Internal server error")

    # ... rest of the processing stays outside the try/except (it's pure Python, no DB) ...
```

Wrap ONLY the `async with tenant_connection(...)` block (the 3 DB queries) in the try/except. The processing logic after the `async with` block (lines 53-81) is pure Python dict operations and stays outside.

---

## Verification

```bash
# 1. Migration file exists with correct content
cat db/migrations/116_metric_compat_views.sql

# 2. Frontend still builds
cd frontend && npx tsc --noEmit

# 3. Check the endpoint has try/except
grep -A 5 "get_metrics_reference" services/ui_iot/routes/metrics.py
```

After deploying migration 116:
- `GET /api/v1/customer/metrics/reference` returns 200 with raw_metrics, normalized_metrics, and unmapped arrays
- No more 500 error
- AlertRuleDialog metric selector loads correctly
