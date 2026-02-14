# Phase 97 — Fix Ingest Tenant RLS Context

## File to modify
`services/ingest_iot/ingest.py`

## Problem

Ingest service acquires DB connections directly via `asyncpg` with no role switch and no
tenant context. All writes go through the `iot` user which has full table access and bypasses
all RLS policies.

## Fix

Wrap every DB write in the ingest path with tenant context — same pattern used in ui_iot's
`tenant_connection()`:
1. `SET LOCAL ROLE pulse_app` — switches to the RLS-governed role
2. `SELECT set_config('app.tenant_id', $1, true)` — sets tenant context for RLS policies

This must be inside a transaction so `SET LOCAL` is scoped to that transaction.

## Find the write path

In `services/ingest_iot/ingest.py`, locate where telemetry rows are inserted into the
`telemetry` table and where `device_state` is upserted. These are the two write paths
that need tenant context.

Look for:
- `INSERT INTO telemetry`
- `INSERT INTO device_state` or `UPDATE device_state`
- `INSERT INTO quarantine_events`

## Pattern to apply

Wherever you find a DB connection being acquired for a write, wrap it like this:

```python
async with pool.acquire() as conn:
    async with conn.transaction():
        # Set tenant RLS context
        await conn.execute("SET LOCAL ROLE pulse_app")
        await conn.execute(
            "SELECT set_config('app.tenant_id', $1, true)",
            tenant_id
        )
        # ... existing INSERT/UPDATE statements stay here unchanged
```

**Important:** `tenant_id` must be the validated tenant_id extracted from the MQTT topic
or HTTP path — not user-supplied input. It is already extracted and validated earlier in
the ingest path via `topic_extract()` and device auth cache lookup.

## What NOT to change

- Do NOT change the device auth cache logic
- Do NOT change subscription status checks
- Do NOT change the topic parsing (`topic_extract()`)
- Do NOT change batch writer logic — only add the role/config calls around the actual DB execute

## If the ingest service uses a shared batch writer (TimescaleBatchWriter)

The batch writer in `services/shared/ingest_core.py` may flush multiple tenants' rows in
a single batch. In that case, you cannot set a single `app.tenant_id` for the whole batch.

Two options:
1. **Per-tenant flush**: Group batch rows by tenant_id before flushing, set context per group
2. **Writer-level bypass with audit**: Keep the batch writer using `iot` role (for performance),
   but add an explicit check in the batch writer that each row's tenant_id matches the
   device's registered tenant before insertion

Check how `TimescaleBatchWriter` works. If it inserts mixed-tenant rows in one COPY command,
use option 2 (explicit tenant_id check) since COPY cannot be wrapped in tenant-scoped
transactions easily.

Document whichever approach is chosen with a comment:
```python
# SECURITY: tenant_id is validated against device auth cache before enqueue.
# Batch writes use the iot role (bypasses RLS) for COPY performance.
# Tenant isolation enforced by: (1) device auth cache, (2) topic-based tenant_id validation.
```

## Verify

```bash
# Check that a device from tenant A cannot write to tenant B's slot
# (This is hard to test directly — verify the code review above is correct)

# At minimum, confirm the ingest service still starts and accepts messages
docker compose -f compose/docker-compose.yml logs ingest --tail=20
# Expected: no errors, telemetry still flowing
```
