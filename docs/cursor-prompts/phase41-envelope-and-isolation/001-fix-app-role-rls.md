# Prompt 001 — Fix `app.role` Dead RLS Policy

## Context

The `telemetry` hypertable has an RLS policy called `operator_read` that checks `current_setting('app.role', true)`. However, the database connection pool in `db/pool.py` never sets `app.role` before queries are executed. This makes the policy dead code.

Operator access currently works only because the `pulse_operator` DB user has `BYPASSRLS` privilege — not because the policy is functioning. The dead policy is misleading and fragile: any future developer may rely on it and get a silent security gap.

## Your Task

**Read the following files first:**
- `db/pool.py` — find where connections are acquired/created
- All migration files in `db/migrations/` that contain `app.role` or `operator_read` — understand what the policy does
- `services/ui_iot/app.py` — find where operator DB context is established

**Then do ONE of the following (choose the simpler option):**

### Option A (Preferred): Drop the dead `operator_read` policy
If `pulse_operator` user already has `BYPASSRLS` and that is the correct operator bypass mechanism, then the `operator_read` policy checking `app.role` is redundant and misleading. Remove it:
- Write a new migration that drops the `operator_read` RLS policy from the `telemetry` table
- Add a comment in `db/pool.py` explaining that operator bypass uses `BYPASSRLS` on the `pulse_operator` role, not a runtime setting
- Do NOT change any application code

### Option B: Implement `app.role` correctly
If the intent is to have runtime-switchable role context (e.g., a single DB user that can act as either customer or operator), then:
- In `db/pool.py`, add a helper that wraps connection acquisition and calls `SET LOCAL app.role = 'operator'` or `SET LOCAL app.role = 'customer'` before yielding the connection
- Use this in operator route handlers
- Write a migration documenting that `pulse_operator` uses `BYPASSRLS` AND `app.role` as belt-and-suspenders

## Acceptance Criteria

- [ ] No dead RLS policies remain (policies that check settings that are never set)
- [ ] `db/pool.py` has a comment clearly documenting the operator bypass mechanism
- [ ] A new migration exists that either drops the dead policy OR properly implements the `app.role` setting
- [ ] `pytest -m unit -v` passes with no regressions

## Pattern Reference

Existing migrations are in `db/migrations/`. Follow the existing numbering convention. Migration files use plain SQL.
