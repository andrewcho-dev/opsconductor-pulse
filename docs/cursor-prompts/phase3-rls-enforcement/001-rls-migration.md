# Task 001: RLS Migration

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Tenant isolation is currently enforced at the application level only. If a bug bypasses the query builders, cross-tenant data could leak. Row-Level Security (RLS) adds database-level enforcement as defense-in-depth.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Phase 3 section)
- `db/migrations/` (existing migration patterns)
- PostgreSQL RLS documentation

**Depends on**: Phase 2 complete

## Task

### 1.1 Create database roles

Create two roles for RLS:

**Role 1**: `pulse_app` — Application role (subject to RLS)
```sql
CREATE ROLE pulse_app NOLOGIN;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulse_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_app;
```

**Role 2**: `pulse_operator` — Operator role (bypasses RLS)
```sql
CREATE ROLE pulse_operator NOLOGIN BYPASSRLS;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulse_operator;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_operator;
```

**Grant to application user**:
```sql
GRANT pulse_app TO iot;
GRANT pulse_operator TO iot;
```

### 1.2 Enable RLS on tenant-scoped tables

Enable RLS on these tables:

| Table | Has tenant_id | Enable RLS |
|-------|---------------|------------|
| `device_state` | Yes | Yes |
| `fleet_alert` | Yes | Yes |
| `delivery_attempts` | Yes | Yes |
| `integrations` | Yes | Yes |
| `integration_routes` | Yes | Yes |
| `raw_events` | Yes | Yes |
| `rate_limits` | Yes | Yes |
| `operator_audit_log` | No (user_id) | No |

For each table:
```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
```

**Note**: `FORCE ROW LEVEL SECURITY` ensures RLS applies even to table owners.

### 1.3 Create tenant isolation policies

For each RLS-enabled table, create a policy:

```sql
CREATE POLICY tenant_isolation_policy ON {table}
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

**Key points**:
- `FOR ALL`: Applies to SELECT, INSERT, UPDATE, DELETE
- `TO pulse_app`: Only applies to the app role (not pulse_operator)
- `current_setting('app.tenant_id', true)`: The `true` means return NULL if not set (fail-closed)
- `USING`: Filter for SELECT/UPDATE/DELETE
- `WITH CHECK`: Validation for INSERT/UPDATE

### 1.4 Handle NULL tenant_id case

When `app.tenant_id` is not set, `current_setting` returns NULL. Comparing `tenant_id = NULL` returns false for all rows, which is fail-closed behavior (returns zero rows).

This is the desired behavior — no data leaks if context is missing.

### 1.5 Create the migration file

Create `db/migrations/004_enable_rls.sql`:

```sql
-- Migration: 004_enable_rls.sql
-- Purpose: Enable Row-Level Security for tenant isolation
-- Date: 2026-02-02

-- ============================================
-- 1. Create application roles
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pulse_app') THEN
        CREATE ROLE pulse_app NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pulse_operator') THEN
        CREATE ROLE pulse_operator NOLOGIN BYPASSRLS;
    END IF;
END
$$;

-- Grant permissions to roles
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulse_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pulse_operator;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_operator;

-- Grant roles to application user
GRANT pulse_app TO iot;
GRANT pulse_operator TO iot;

-- ============================================
-- 2. Enable RLS on tenant-scoped tables
-- ============================================

-- device_state
ALTER TABLE device_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_state FORCE ROW LEVEL SECURITY;

-- fleet_alert
ALTER TABLE fleet_alert ENABLE ROW LEVEL SECURITY;
ALTER TABLE fleet_alert FORCE ROW LEVEL SECURITY;

-- delivery_attempts
ALTER TABLE delivery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_attempts FORCE ROW LEVEL SECURITY;

-- integrations
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations FORCE ROW LEVEL SECURITY;

-- integration_routes
ALTER TABLE integration_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE integration_routes FORCE ROW LEVEL SECURITY;

-- raw_events
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_events FORCE ROW LEVEL SECURITY;

-- rate_limits
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits FORCE ROW LEVEL SECURITY;

-- ============================================
-- 3. Create tenant isolation policies
-- ============================================

-- device_state
CREATE POLICY tenant_isolation_policy ON device_state
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- fleet_alert
CREATE POLICY tenant_isolation_policy ON fleet_alert
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- delivery_attempts
CREATE POLICY tenant_isolation_policy ON delivery_attempts
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- integrations
CREATE POLICY tenant_isolation_policy ON integrations
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- integration_routes
CREATE POLICY tenant_isolation_policy ON integration_routes
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- raw_events
CREATE POLICY tenant_isolation_policy ON raw_events
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- rate_limits
CREATE POLICY tenant_isolation_policy ON rate_limits
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- ============================================
-- 4. Comments
-- ============================================

COMMENT ON POLICY tenant_isolation_policy ON device_state IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON fleet_alert IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON delivery_attempts IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON integrations IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON integration_routes IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON raw_events IS 'Restrict access to rows matching app.tenant_id session variable';
COMMENT ON POLICY tenant_isolation_policy ON rate_limits IS 'Restrict access to rows matching app.tenant_id session variable';
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/004_enable_rls.sql` |

## Acceptance Criteria

- [ ] Migration runs without errors
- [ ] Roles `pulse_app` and `pulse_operator` exist
- [ ] RLS enabled on all 7 tenant-scoped tables
- [ ] Policies created for all 7 tables
- [ ] Verify RLS is enabled:
  ```sql
  SELECT tablename, rowsecurity FROM pg_tables
  WHERE schemaname = 'public' AND tablename IN
  ('device_state', 'fleet_alert', 'integrations');
  ```
- [ ] Verify policies exist:
  ```sql
  SELECT tablename, policyname FROM pg_policies;
  ```

## Commit

```
Add RLS migration for tenant isolation

- Create pulse_app role (subject to RLS)
- Create pulse_operator role (BYPASSRLS)
- Enable RLS on 7 tenant-scoped tables
- Create tenant_isolation_policy using app.tenant_id setting
- Fail-closed: missing context returns zero rows

Part of Phase 3: RLS Enforcement
```
