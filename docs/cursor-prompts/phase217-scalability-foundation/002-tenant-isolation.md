# Task 2: Per-Tenant Exception Isolation and Wall-Clock Budget

## File — services/evaluator_iot/evaluator.py

## Problem

The current `for r in rows:` loop (starting around line 1254) iterates all
devices from all tenants in a flat list. The outer `except Exception` (around
line 1748) wraps the entire cycle. If any device evaluation throws an
unhandled exception — bad data type, unexpected None, DB error on a single
tenant's rule — the whole cycle is aborted and every other tenant misses that
evaluation round.

## Change 1 — Add constants near the top (after existing optional_env calls)

After the block of `optional_env` calls near lines 55–60, add:

```python
TENANT_BUDGET_MS = float(optional_env("TENANT_BUDGET_MS", "500"))
```

## Change 2 — Group rows by tenant and wrap each tenant in isolation

Locate the block starting with:
```python
                for r in rows:
                    tenant_id = r["tenant_id"]
```

This loop processes all devices in a flat iteration. Replace the entire flat
loop with a tenant-grouped version. The transformation is:

**Before (schematic):**
```python
tenant_rules_cache = {}
tenant_mapping_cache = {}

for r in rows:
    tenant_id = r["tenant_id"]
    device_id = r["device_id"]
    # ... per-device evaluation ...
```

**After (schematic):**
```python
tenant_rules_cache = {}
tenant_mapping_cache = {}

# Group rows by tenant for isolation
rows_by_tenant: dict[str, list] = {}
for r in rows:
    rows_by_tenant.setdefault(r["tenant_id"], []).append(r)

for tenant_id, tenant_rows in rows_by_tenant.items():
    tenant_start = time.monotonic()
    try:
        for r in tenant_rows:
            device_id = r["device_id"]
            # ... rest of existing per-device logic unchanged ...

            # After processing each device, check wall-clock budget
            elapsed_ms = (time.monotonic() - tenant_start) * 1000
            if elapsed_ms > TENANT_BUDGET_MS:
                log_event(
                    logger,
                    "tenant_budget_exceeded",
                    level="WARNING",
                    tenant_id=tenant_id,
                    elapsed_ms=round(elapsed_ms, 1),
                    devices_processed=tenant_rows.index(r) + 1,
                    devices_total=len(tenant_rows),
                )
                break

    except Exception as exc:
        COUNTERS["evaluation_errors"] += 1
        evaluator_evaluation_errors_total.inc()
        log_event(
            logger,
            "tenant_evaluation_failed",
            level="ERROR",
            tenant_id=tenant_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        # Do NOT re-raise. Continue to next tenant.
        continue
```

## Important

- The existing per-device logic inside the loop is **unchanged**. Only the
  outer grouping and the try/except wrapper are new.
- The existing outer `except Exception` around the full cycle (around line 1748)
  is **kept**. It now only triggers for errors *outside* the per-tenant loop
  (e.g., `fetch_rollup_timescaledb` failure, pool acquisition failure).
- Import `time` is already present (line 5). No new imports needed.
- `evaluator_evaluation_errors_total` is already imported (line 19).
- Budget check uses `break` not `continue` — it stops processing further
  devices for this tenant this cycle, then moves to the next tenant.

## Verification

After applying:
```bash
docker compose -f compose/docker-compose.yml build evaluator
docker compose -f compose/docker-compose.yml up -d evaluator
docker compose -f compose/docker-compose.yml logs evaluator | grep -E "tenant_evaluation_failed|tenant_budget_exceeded|tick_done"
```

Confirm the evaluator starts cleanly and `tick_done` appears in logs. The
new log keys will only appear if a tenant actually fails or exceeds budget.
