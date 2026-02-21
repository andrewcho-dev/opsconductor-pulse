# Task 1: Build Complete RLS Inventory

## Context

Before fixing anything, we need to know the exact state of RLS across all tables. This task is a pure analysis task — no code changes.

## Actions

1. Read all migration files in `db/migrations/` (there are ~102 of them). For each, record:
   - Which tables are created (`CREATE TABLE`)
   - Which tables have `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
   - Which tables have `ALTER TABLE ... FORCE ROW LEVEL SECURITY`
   - Which tables have `CREATE POLICY` statements

2. Build a complete table list from the migrations. For each table, determine:
   - Does it contain tenant-specific data? (Has a `tenant_id` column or is joined to tenant data?)
   - Is RLS enabled?
   - Does it have any RLS policies?
   - Is there an obvious reason it might be exempt? (e.g., `system_metrics`, `stripe_events`, `audit_log`)

3. Create a markdown file `docs/architecture/rls-inventory.md` with a table:

```markdown
# RLS Inventory

Last updated: 2026-02-20

| Table | Has tenant_id | RLS Enabled | Policies | Status | Notes |
|-------|--------------|-------------|----------|--------|-------|
| device_registry | Yes | Yes | 3 | PROTECTED | — |
| fleet_alert | Yes | Yes | 2 | PROTECTED | — |
| system_metrics | No | No | 0 | EXEMPT | Platform-wide metrics, no tenant data |
| stripe_events | No | No | 0 | EXEMPT | Webhook log, keyed by Stripe event ID |
| ... | | | | | |
```

Status values:
- `PROTECTED` — RLS enabled with policies
- `EXEMPT` — No tenant data, intentionally excluded
- `GAP` — Has tenant data but RLS is missing (needs fixing)
- `REVIEW` — Unclear, needs investigation

4. This file will be used in Task 2 to identify which tables need migration fixes.

5. Do not write any migrations in this task.

## Verification

The `docs/architecture/rls-inventory.md` file exists and lists every table from the migrations with a Status of either PROTECTED, EXEMPT, GAP, or REVIEW.
