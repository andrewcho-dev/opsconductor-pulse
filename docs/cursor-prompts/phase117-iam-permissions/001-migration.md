# 001 — SQL Migration: IAM Permission Tables

## Task

Create `db/migrations/080_iam_permissions.sql` with 4 tables, seed data for 28 permissions and 6 system roles, and RLS policies.

## Context

- Migration runner: `db/migrate.py` — reads `db/migrations/*.sql` in numeric order, wraps each in a transaction, tracks in `schema_migrations` table
- Latest migration: `079_device_commands.sql`
- RLS pattern used throughout: `current_setting('app.tenant_id', true)` with `pulse_app` / `pulse_operator` roles
- DB roles: `pulse_app` (NOLOGIN, subject to RLS), `pulse_operator` (NOLOGIN, BYPASSRLS), `iot` (service user, holds both)
- Pool helper: `services/ui_iot/db/pool.py` — `tenant_connection(pool, tenant_id)` sets `SET LOCAL ROLE pulse_app` + `set_config('app.tenant_id', ...)`

## Create File: `db/migrations/080_iam_permissions.sql`

```sql
-- Migration 080: IAM-Style Granular Permission System
-- Creates tables for atomic permissions, role bundles, role-permission mappings,
-- and user-role assignments. Seeds 28 permissions and 6 system roles.
-- Date: 2026-02-15
```

### Table 1: `permissions`

```sql
CREATE TABLE IF NOT EXISTS permissions (
    id          SERIAL PRIMARY KEY,
    action      TEXT UNIQUE NOT NULL,     -- e.g. 'devices.read'
    category    TEXT NOT NULL,            -- e.g. 'devices'
    description TEXT
);
```

No RLS needed — permissions are global/read-only.

### Table 2: `roles`

```sql
CREATE TABLE IF NOT EXISTS roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT,                     -- NULL = system-defined (immutable)
    name        TEXT NOT NULL,
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

**RLS for `roles`:** Enable RLS. Create TWO policies:
1. `roles_system_visible` — `FOR SELECT` — `USING (is_system = true)` — everyone can see system roles
2. `roles_tenant_isolation` — `FOR ALL` — `USING (tenant_id = current_setting('app.tenant_id', true))` `WITH CHECK (tenant_id = current_setting('app.tenant_id', true))` — tenant can only manage their own custom roles

### Table 3: `role_permissions`

```sql
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);
```

No RLS needed — joins through `roles` which has RLS.

### Table 4: `user_role_assignments`

```sql
CREATE TABLE IF NOT EXISTS user_role_assignments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL,
    user_id     TEXT NOT NULL,            -- Keycloak sub claim
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by TEXT,                     -- Keycloak sub of assigner
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, role_id)
);
```

**RLS for `user_role_assignments`:** Enable RLS + FORCE RLS.
- `user_role_assignments_tenant_isolation` — `FOR ALL TO pulse_app` — `USING (tenant_id = current_setting('app.tenant_id', true))` `WITH CHECK (tenant_id = current_setting('app.tenant_id', true))`

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_user
    ON user_role_assignments (tenant_id, user_id);

CREATE INDEX IF NOT EXISTS idx_user_role_assignments_role
    ON user_role_assignments (role_id);

CREATE INDEX IF NOT EXISTS idx_roles_tenant
    ON roles (tenant_id) WHERE tenant_id IS NOT NULL;
```

### Seed: 28 Permissions

Insert all 28 permissions using `INSERT ... ON CONFLICT (action) DO NOTHING`:

| category | action | description |
|----------|--------|-------------|
| dashboard | dashboard.read | View dashboard |
| devices | devices.read | View devices |
| devices | devices.write | Edit device properties |
| devices | devices.create | Register/provision devices |
| devices | devices.delete | Decommission devices |
| devices | devices.commands | Send commands |
| alerts | alerts.read | View alerts |
| alerts | alerts.acknowledge | Acknowledge alerts |
| alerts | alerts.close | Close/resolve alerts |
| alerts | alerts.rules.read | View alert rules |
| alerts | alerts.rules.write | Create/edit/delete alert rules |
| integrations | integrations.read | View integrations |
| integrations | integrations.write | Manage integrations |
| integrations | integrations.routes | Manage routing rules |
| users | users.read | View team members |
| users | users.invite | Invite new users |
| users | users.edit | Edit user details |
| users | users.remove | Remove users |
| users | users.roles | Assign/change roles |
| reports | reports.read | View reports |
| reports | reports.export | Export data |
| sites | sites.read | View sites |
| sites | sites.write | Manage sites |
| subscriptions | subscriptions.read | View subscription |
| subscriptions | subscriptions.write | Manage subscription |
| maintenance | maintenance.read | View maintenance windows |
| maintenance | maintenance.write | Manage maintenance windows |
| settings | settings.read | View settings |

### Seed: 6 System Roles

Use a `DO $$ ... $$` block to insert roles with `tenant_id = NULL` and `is_system = true`, then insert their permission mappings. Use subqueries to resolve permission IDs by action name.

| Role Name | Description | Permissions |
|-----------|-------------|-------------|
| Viewer | Read-only access to all areas | All 14 `*.read` actions: `dashboard.read`, `devices.read`, `alerts.read`, `alerts.rules.read`, `integrations.read`, `users.read`, `reports.read`, `sites.read`, `subscriptions.read`, `maintenance.read`, `settings.read` PLUS `reports.export` (non-destructive read-like action). Actually strictly: only actions ending in `.read` from the seed list = 11 permissions. Let me be exact — include these: `dashboard.read`, `devices.read`, `alerts.read`, `alerts.rules.read`, `integrations.read`, `users.read`, `reports.read`, `sites.read`, `subscriptions.read`, `maintenance.read`, `settings.read` = 11 permissions |
| Device Manager | Viewer + device management | Viewer permissions + `devices.write`, `devices.create`, `devices.delete`, `devices.commands` |
| Alert Manager | Viewer + alert management | Viewer permissions + `alerts.acknowledge`, `alerts.close`, `alerts.rules.write`, `maintenance.write` |
| Integration Manager | Viewer + integration management | Viewer permissions + `integrations.write`, `integrations.routes` |
| Team Admin | Viewer + user management | Viewer permissions + `users.invite`, `users.edit`, `users.remove`, `users.roles` |
| Full Admin | All permissions | All 28 permissions |

**Implementation approach for seeding roles:**

```sql
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    -- Viewer
    INSERT INTO roles (id, tenant_id, name, description, is_system)
    VALUES (gen_random_uuid(), NULL, 'Viewer', 'Read-only access to all areas', true)
    ON CONFLICT (tenant_id, name) DO NOTHING
    RETURNING id INTO v_role_id;

    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
            'integrations.read', 'users.read', 'reports.read', 'sites.read',
            'subscriptions.read', 'maintenance.read', 'settings.read'
        );
    END IF;

    -- ... repeat for each role
END $$;
```

**Important:** The `UNIQUE(tenant_id, name)` constraint treats `NULL` tenant_id values as distinct in PostgreSQL. To make `ON CONFLICT` work for system roles (where `tenant_id IS NULL`), use: `ON CONFLICT DO NOTHING` and rely on the IF check pattern above instead, OR create a unique index with `COALESCE(tenant_id, '__system__')`:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name_unique
    ON roles (COALESCE(tenant_id, '__system__'), name);
```

Then use `ON CONFLICT (COALESCE(tenant_id, '__system__'), name) DO NOTHING` — but this won't work with standard ON CONFLICT syntax. Safer approach: just use the `RETURNING id INTO v_role_id` + `IF v_role_id IS NOT NULL` pattern shown above, which is idempotent enough since the migration runner won't re-run already-applied migrations.

### Grants

```sql
-- Grants for new tables (covered by ALTER DEFAULT PRIVILEGES in migration 017,
-- but add explicit grants for safety)
GRANT SELECT ON permissions TO pulse_app;
GRANT SELECT ON permissions TO pulse_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON roles TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON roles TO pulse_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON role_permissions TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON role_permissions TO pulse_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_role_assignments TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_role_assignments TO pulse_operator;
GRANT USAGE ON SEQUENCE permissions_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE permissions_id_seq TO pulse_operator;
```

## Verification

After running `python db/migrate.py`:
- `SELECT COUNT(*) FROM permissions;` → 28
- `SELECT COUNT(*) FROM roles WHERE is_system = true;` → 6
- `SELECT r.name, COUNT(rp.permission_id) FROM roles r JOIN role_permissions rp ON rp.role_id = r.id GROUP BY r.name ORDER BY r.name;` → Viewer=11, Device Manager=15, Alert Manager=15, Integration Manager=13, Team Admin=15, Full Admin=28
- `SELECT COUNT(*) FROM user_role_assignments;` → 0 (no assignments yet — auto-bootstrap happens at request time)
