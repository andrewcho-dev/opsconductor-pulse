# Task 2: Write Migration to Fix RLS Gaps

## Context

Using the inventory from Task 1, write a migration that enables RLS and creates appropriate policies on any table marked as `GAP` (has tenant data but no RLS).

## Actions

1. Read `docs/architecture/rls-inventory.md` from Task 1.

2. For each table marked `GAP`:
   - Read the table's CREATE statement in the migrations to understand its schema.
   - Read existing RLS policies on similar tables (e.g., `device_registry`) to understand the policy pattern used throughout the codebase.

3. The standard RLS policy pattern used in this codebase is:
   ```sql
   -- Tenant users see only their tenant's rows
   CREATE POLICY tenant_isolation ON <table_name>
     USING (tenant_id = current_setting('app.tenant_id', true)::text);

   -- Operator role bypasses RLS (already set via pulse_operator_read role)
   ```
   Adapt this pattern for each gap table.

4. Determine the next migration file number (should be ~104 based on the 103 migration added in phase 197). Create `db/migrations/104_rls_gap_fixes.sql`.

5. For each gap table, add:
   ```sql
   -- Enable RLS on <table_name> (missed in original schema)
   ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
   ALTER TABLE <table_name> FORCE ROW LEVEL SECURITY;

   -- Drop any existing policy to avoid conflicts
   DROP POLICY IF EXISTS tenant_isolation ON <table_name>;

   CREATE POLICY tenant_isolation ON <table_name>
     USING (tenant_id = current_setting('app.tenant_id', true)::text);
   ```

6. For tables marked `REVIEW`: do not add RLS yet. Add a comment in the migration file noting they need further investigation.

7. For tables intentionally exempt (`EXEMPT`), add a comment to the original migration file:
   ```sql
   -- RLS: EXEMPT — reason here
   ```
   This is a documentation change only, no schema change.

8. Do not change any existing RLS policies.

## Verification

```bash
# Migration exists
ls db/migrations/ | grep 104_rls

# Migration is valid SQL (no syntax errors visible)
grep 'ENABLE ROW LEVEL SECURITY' db/migrations/104_rls_gap_fixes.sql
```
