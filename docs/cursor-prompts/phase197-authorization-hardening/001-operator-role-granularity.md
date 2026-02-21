# Task 1: Create Granular Operator Database Roles

## Context

`db/migrations/004_enable_rls.sql` creates `pulse_operator` with `BYPASSRLS` and `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES`. This is overly broad — a bug or compromised operator session can modify any tenant's data.

## Actions

1. Read `db/migrations/004_enable_rls.sql` and all subsequent migrations that reference `pulse_operator`.

2. Create a new migration file: `db/migrations/103_operator_role_granularity.sql`.

3. In the new migration, implement this role structure:

```sql
-- Read-only operator role: can view all tenant data (BYPASSRLS for cross-tenant queries)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pulse_operator_read') THEN
    CREATE ROLE pulse_operator_read NOLOGIN BYPASSRLS;
  END IF;
END
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO pulse_operator_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pulse_operator_read;

-- Write operator role: limited DML for specific operational tables only, NO BYPASSRLS
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pulse_operator_write') THEN
    CREATE ROLE pulse_operator_write NOLOGIN;
  END IF;
END
$$;

-- Only grant write to tables where operators legitimately need it:
GRANT INSERT, UPDATE ON device_registry TO pulse_operator_write;
GRANT INSERT, UPDATE ON fleet_alert TO pulse_operator_write;
GRANT INSERT, UPDATE ON subscriptions TO pulse_operator_write;
GRANT INSERT, UPDATE ON system_metrics TO pulse_operator_write;
-- Add other tables as needed based on actual operator use cases

-- Keep the old role as an alias for backward compatibility during transition
-- Revoke its BYPASSRLS and schema-wide grants after confirming new roles work
-- (Do NOT drop pulse_operator yet — that is a separate migration)
```

4. Do not drop or alter `pulse_operator` in this migration — that is done in a follow-on migration after Task 2 confirms the new roles work.

5. Number the migration appropriately. Check the current highest migration number in `db/migrations/` and use the next sequential number.

## Verification

```bash
# New migration file exists
ls db/migrations/ | grep operator_role

# Migration is syntactically valid SQL (no obvious errors)
grep -n 'pulse_operator_read\|pulse_operator_write' db/migrations/103_operator_role_granularity.sql
```
