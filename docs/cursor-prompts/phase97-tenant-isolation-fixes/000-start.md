# Phase 97 — Tenant Isolation Fixes

## Two distinct issues to fix

### Issue A — Ingest service writes telemetry without tenant RLS context (REAL SECURITY GAP)

The ingest service connects as the `iot` DB user with no `SET LOCAL ROLE` and no
`set_config('app.tenant_id', ...)`. This means all telemetry writes bypass RLS entirely.
A compromised or misconfigured ingest path could write to any tenant's data.

Subscription status IS checked (DeviceSubscriptionCache), so the business logic is correct.
But the DB-level tenant boundary is not enforced during writes.

**Fix:** Add `SET LOCAL ROLE pulse_app` and `set_config('app.tenant_id', ...)` to the ingest
DB connection context so RLS is enforced at the database level on all telemetry writes.

### Issue B — Dead `operator_read` RLS policy on telemetry (DEAD CODE)

`db/migrations/021_telemetry_hypertable.sql` creates a policy:
```sql
CREATE POLICY operator_read ON telemetry
    FOR SELECT
    USING (current_setting('app.role', true) IN ('operator', 'operator_admin'));
```

`app.role` is never set anywhere — `operator_connection()` uses `pulse_operator` role with
BYPASSRLS instead. This policy is effectively dead code: it never evaluates to true, but
operators can still read telemetry because BYPASSRLS skips all policies.

**Fix A (preferred):** Remove the dead policy and add a migration comment documenting that
operator access is controlled via the `pulse_operator` BYPASSRLS privilege.

**Fix B (alternative):** Add `set_config('app.role', 'operator', true)` in `operator_connection()`
so the policy works as originally intended. This would allow restricting BYPASSRLS later.

Use Fix A — the BYPASSRLS pattern is already correct and consistent. The dead policy is noise.

## Execution order

| File | What it does |
|------|-------------|
| `001-ingest-rls.md` | Add tenant RLS context to ingest DB writes |
| `002-dead-policy-cleanup.md` | Migration to drop dead operator_read policy |
| `003-verify.md` | Verify tenant isolation end-to-end |
