# Prompt 002 — DB Migration: Add `duration_seconds` to `alert_rules`

## Your Task

Create a new migration file: `db/migrations/054_alert_rules_duration_seconds.sql`

Follow the existing migration file convention (plain SQL, wrapped in BEGIN/COMMIT).

The migration must:

```sql
BEGIN;

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN alert_rules.duration_seconds IS
    'Minimum seconds the threshold must be continuously breached before an alert fires. 0 = fire immediately (default, backwards compatible).';

COMMIT;
```

That is the entire migration. Nothing else. Do NOT add indexes, do NOT change existing columns, do NOT seed data.

## Why `DEFAULT 0`

All existing rules have no duration concept — they fire immediately. `DEFAULT 0` means "fire immediately" and is backwards compatible. Every existing rule continues to behave exactly as before.

## Acceptance Criteria

- [ ] File `db/migrations/054_alert_rules_duration_seconds.sql` exists
- [ ] Migration is idempotent (`ADD COLUMN IF NOT EXISTS`)
- [ ] `DEFAULT 0` ensures backwards compatibility
- [ ] No other changes made
- [ ] `pytest -m unit -v` passes (no schema changes affect unit tests — unit tests use FakeConn)
