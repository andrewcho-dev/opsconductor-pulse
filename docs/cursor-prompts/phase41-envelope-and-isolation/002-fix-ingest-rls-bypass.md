# Prompt 002 — Fix Ingest Service RLS Bypass

## Context

The `ingest_iot` service (MQTT ingest) connects to the database as the `iot` user, which has been granted both `pulse_app` and `pulse_operator` roles. Because `SET LOCAL ROLE` is never called inside ingest transactions, the connection effectively runs with elevated privileges and bypasses RLS.

Device-level tenant isolation is currently enforced by:
1. Device auth cache (`DeviceAuthCache`) — validates provision token against `device_registry`
2. Topic-based tenant validation — extracts `tenant_id` from MQTT topic
3. Subscription checks (partially — see prompt 003)

These are application-level guards, not database-level. If any of them fail or are bypassed, a compromised ingest service could write telemetry to any tenant's data. The fix is to add `SET LOCAL ROLE pulse_app` at the start of each ingest database transaction, so that even if application guards fail, the DB enforces tenant isolation via RLS.

## Your Task

**Read the following files first:**
- `services/ingest_iot/main.py` — MQTT message handler, find where DB writes happen
- `services/shared/ingest_core.py` — `TimescaleBatchWriter`, find where `COPY` or `INSERT` executes
- `db/pool.py` — understand how connections are acquired

**Then:**

1. In the ingest path (both `ingest_iot` MQTT handler AND `services/ui_iot/routes/ingest.py` HTTP handler), ensure that before any DB write the connection executes:
   ```sql
   SET LOCAL ROLE pulse_app
   ```
   This must be inside the same transaction as the write, so `LOCAL` scope is correct.

2. If `TimescaleBatchWriter` uses a COPY command (which runs outside a typical transaction), investigate whether COPY respects RLS. If not, wrap it in an explicit transaction with the role set first.

3. Do NOT change the `DeviceAuthCache` or subscription check logic — those are addressed in prompt 003.

## Acceptance Criteria

- [ ] Every DB write in the MQTT ingest path sets `ROLE pulse_app` before writing
- [ ] Every DB write in the HTTP ingest path sets `ROLE pulse_app` before writing
- [ ] `pytest -m unit -v` passes with no regressions
- [ ] No new DB connections are opened — reuse existing pool patterns

## Pattern Reference

Follow the existing connection pool pattern in `db/pool.py`. Do not create a new pool. The role set must be `LOCAL` (transaction-scoped), not `SESSION`-scoped.
