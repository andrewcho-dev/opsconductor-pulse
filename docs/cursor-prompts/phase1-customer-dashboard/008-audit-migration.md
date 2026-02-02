# Task 008: Audit Log Migration

## Context

Operator routes log access to `operator_audit_log` table. This table needs to be created via migration.

**Read first**:
- `db/migrations/001_webhook_delivery_v1.sql` (existing migration pattern)
- `services/ui_iot/db/audit.py` (audit logging function)

**Depends on**: None (can run early, before other tasks)

## Task

### 8.1 Create `db/migrations/002_operator_audit_log.sql`

Create the audit log table for operator access tracking.

```sql
-- Migration: 002_operator_audit_log.sql
-- Purpose: Audit log for operator cross-tenant access
-- Date: 2026-02-02

-- Operator audit log table
CREATE TABLE IF NOT EXISTS operator_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    tenant_filter TEXT,
    resource_type TEXT,
    resource_id TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Index for querying by user
CREATE INDEX IF NOT EXISTS operator_audit_log_user_idx
    ON operator_audit_log(user_id);

-- Index for querying by time (recent activity)
CREATE INDEX IF NOT EXISTS operator_audit_log_created_idx
    ON operator_audit_log(created_at DESC);

-- Index for querying by action
CREATE INDEX IF NOT EXISTS operator_audit_log_action_idx
    ON operator_audit_log(action);

-- Composite index for user + time queries
CREATE INDEX IF NOT EXISTS operator_audit_log_user_time_idx
    ON operator_audit_log(user_id, created_at DESC);

-- Add comment
COMMENT ON TABLE operator_audit_log IS 'Audit trail for operator cross-tenant access';
COMMENT ON COLUMN operator_audit_log.user_id IS 'Keycloak user sub claim';
COMMENT ON COLUMN operator_audit_log.action IS 'Action performed (view_dashboard, list_devices, etc.)';
COMMENT ON COLUMN operator_audit_log.tenant_filter IS 'Tenant filter applied, if any';
COMMENT ON COLUMN operator_audit_log.resource_type IS 'Type of resource accessed (device, alert, etc.)';
COMMENT ON COLUMN operator_audit_log.resource_id IS 'ID of specific resource accessed';
```

### 8.2 Run the migration

After creating the file, run it against the database:

```bash
# From project root
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/002_operator_audit_log.sql
```

Or if using docker-compose:
```bash
docker-compose exec postgres psql -U iot -d iotcloud < db/migrations/002_operator_audit_log.sql
```

### 8.3 Verify table exists

```bash
docker exec -i iot-postgres psql -U iot -d iotcloud -c "\d operator_audit_log"
```

Expected output:
```
                                         Table "public.operator_audit_log"
    Column     |           Type           | Collation | Nullable |                    Default
---------------+--------------------------+-----------+----------+------------------------------------------------
 id            | bigint                   |           | not null | nextval('operator_audit_log_id_seq'::regclass)
 user_id       | text                     |           | not null |
 action        | text                     |           | not null |
 tenant_filter | text                     |           |          |
 resource_type | text                     |           |          |
 resource_id   | text                     |           |          |
 ip_address    | inet                     |           |          |
 user_agent    | text                     |           |          |
 created_at    | timestamp with time zone |           | not null | now()
Indexes:
    "operator_audit_log_pkey" PRIMARY KEY, btree (id)
    "operator_audit_log_action_idx" btree (action)
    "operator_audit_log_created_idx" btree (created_at DESC)
    "operator_audit_log_user_idx" btree (user_id)
    "operator_audit_log_user_time_idx" btree (user_id, created_at DESC)
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/002_operator_audit_log.sql` |

## Acceptance Criteria

- [ ] Migration file exists at `db/migrations/002_operator_audit_log.sql`
- [ ] Migration runs without errors
- [ ] Table `operator_audit_log` exists in database
- [ ] All indexes are created
- [ ] Comments are applied to table and columns
- [ ] Test insert works:
  ```sql
  INSERT INTO operator_audit_log (user_id, action, tenant_filter)
  VALUES ('test-user', 'test_action', 'tenant-a');
  SELECT * FROM operator_audit_log WHERE user_id = 'test-user';
  DELETE FROM operator_audit_log WHERE user_id = 'test-user';
  ```

## Commit

```
Add operator audit log migration

- operator_audit_log table for cross-tenant access tracking
- Indexes for user, time, and action queries
- Supports Phase 1 operator route auditing

Part of Phase 1: Customer Read-Only Dashboard
```
