# Task 008: Fix alert_rules Table Permissions

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create/modify only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The `/api/v2/alert-rules` endpoint returns 500 Internal Server Error. The backend log shows:

```
asyncpg.exceptions.InsufficientPrivilegeError: permission denied for table alert_rules
```

The `alert_rules` table was created by the evaluator service AFTER migration 004 ran. Migration 004 uses `GRANT ... ON ALL TABLES` which only applies to tables that exist at that moment. So `pulse_app` and `pulse_operator` roles have no grants on `alert_rules`.

The fix is a new migration that:
1. Grants `pulse_app` and `pulse_operator` access to `alert_rules`
2. Enables RLS on `alert_rules` with a tenant isolation policy (same pattern as other tenant-scoped tables)
3. Sets `ALTER DEFAULT PRIVILEGES` so any future tables created by `iot` automatically get grants

**Read first**:
- `db/migrations/004_enable_rls.sql` — existing RLS migration pattern
- `services/ui_iot/db/pool.py` — how `pulse_app` role is used

---

## Task

### 8.1 Create migration

**File**: `db/migrations/017_alert_rules_rls.sql` (NEW)

```sql
-- Migration: 017_alert_rules_rls.sql
-- Purpose: Grant pulse_app/pulse_operator access to alert_rules and enable RLS
-- Date: 2026-02-05

-- ============================================
-- 1. Grant permissions on alert_rules
-- ============================================

GRANT SELECT, INSERT, UPDATE, DELETE ON alert_rules TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON alert_rules TO pulse_operator;

-- ============================================
-- 2. Enable RLS on alert_rules
-- ============================================

ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON alert_rules
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY tenant_isolation_policy ON alert_rules
    IS 'Restrict access to rows matching app.tenant_id session variable';

-- ============================================
-- 3. Default privileges for future tables
-- ============================================
-- Ensures any table created by the iot user in the future
-- automatically gets grants for pulse_app and pulse_operator.

ALTER DEFAULT PRIVILEGES FOR ROLE iot IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pulse_app;

ALTER DEFAULT PRIVILEGES FOR ROLE iot IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pulse_operator;

ALTER DEFAULT PRIVILEGES FOR ROLE iot IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO pulse_app;

ALTER DEFAULT PRIVILEGES FOR ROLE iot IN SCHEMA public
    GRANT USAGE ON SEQUENCES TO pulse_operator;
```

### 8.2 Apply the migration

```bash
docker compose exec postgres psql -U iot -d iotcloud -f /dev/stdin < /home/opsconductor/simcloud/db/migrations/017_alert_rules_rls.sql
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `db/migrations/017_alert_rules_rls.sql` | Grant permissions, enable RLS, set default privileges |

---

## Test

### Step 1: Verify the migration applied

```bash
docker compose exec postgres psql -U iot -d iotcloud -c "SELECT grantee, privilege_type FROM information_schema.table_privileges WHERE table_name = 'alert_rules' AND grantee = 'pulse_app';"
```

Should show 4 rows (SELECT, INSERT, UPDATE, DELETE).

### Step 2: Verify RLS is enabled

```bash
docker compose exec postgres psql -U iot -d iotcloud -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'alert_rules';"
```

Both `relrowsecurity` and `relforcerowsecurity` should be `t`.

### Step 3: Verify the endpoint works

```bash
curl -sk "https://192.168.10.53/api/v2/alert-rules?limit=200" -o /dev/null -w "%{http_code}"
```

Should return `401` (not 500).

### Step 4: Backend tests still pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

---

## Commit

```
Fix alert_rules permissions — grant pulse_app/operator access

The alert_rules table was created after migration 004 ran, so
pulse_app/pulse_operator roles had no grants. Added migration 017
with grants, RLS policy, and ALTER DEFAULT PRIVILEGES to prevent
this for future tables.
```
