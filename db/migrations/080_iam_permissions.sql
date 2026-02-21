-- Migration 080: IAM-Style Granular Permission System
-- Creates tables for atomic permissions, role bundles, role-permission mappings,
-- and user-role assignments. Seeds 28 permissions and 6 system roles.
-- Date: 2026-02-15

-- Table 1: permissions (global/read-only; no RLS)
-- RLS: EXEMPT - global IAM action catalog
CREATE TABLE IF NOT EXISTS permissions (
    id          SERIAL PRIMARY KEY,
    action      TEXT UNIQUE NOT NULL,     -- e.g. 'devices.read'
    category    TEXT NOT NULL,            -- e.g. 'devices'
    description TEXT
);

-- Table 2: roles (system + tenant-scoped custom)
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

-- Enforce uniqueness for system roles too (tenant_id NULL).
CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name_unique
    ON roles (COALESCE(tenant_id, '__system__'), name);

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;

-- Everyone can see system roles.
DROP POLICY IF EXISTS roles_system_visible ON roles;
CREATE POLICY roles_system_visible
    ON roles
    FOR SELECT
    USING (is_system = true);

-- Tenant isolation for tenant-scoped roles.
DROP POLICY IF EXISTS roles_tenant_isolation ON roles;
CREATE POLICY roles_tenant_isolation
    ON roles
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Table 3: role_permissions (no RLS; enforced via roles RLS in query patterns)
-- RLS: EXEMPT - global role-to-permission mapping
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Table 4: user_role_assignments (tenant-scoped)
CREATE TABLE IF NOT EXISTS user_role_assignments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL,
    user_id     TEXT NOT NULL,            -- Keycloak sub claim
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by TEXT,                     -- Keycloak sub of assigner
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, user_id, role_id)
);

ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_role_assignments FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_role_assignments_tenant_isolation ON user_role_assignments;
CREATE POLICY user_role_assignments_tenant_isolation
    ON user_role_assignments
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_user
    ON user_role_assignments (tenant_id, user_id);

CREATE INDEX IF NOT EXISTS idx_user_role_assignments_role
    ON user_role_assignments (role_id);

CREATE INDEX IF NOT EXISTS idx_roles_tenant
    ON roles (tenant_id) WHERE tenant_id IS NOT NULL;

-- Seed: 28 Permissions
INSERT INTO permissions (action, category, description) VALUES
    ('dashboard.read', 'dashboard', 'View dashboard'),
    ('devices.read', 'devices', 'View devices'),
    ('devices.write', 'devices', 'Edit device properties'),
    ('devices.create', 'devices', 'Register/provision devices'),
    ('devices.delete', 'devices', 'Decommission devices'),
    ('devices.commands', 'devices', 'Send commands'),
    ('alerts.read', 'alerts', 'View alerts'),
    ('alerts.acknowledge', 'alerts', 'Acknowledge alerts'),
    ('alerts.close', 'alerts', 'Close/resolve alerts'),
    ('alerts.rules.read', 'alerts', 'View alert rules'),
    ('alerts.rules.write', 'alerts', 'Create/edit/delete alert rules'),
    ('integrations.read', 'integrations', 'View integrations'),
    ('integrations.write', 'integrations', 'Manage integrations'),
    ('integrations.routes', 'integrations', 'Manage routing rules'),
    ('users.read', 'users', 'View team members'),
    ('users.invite', 'users', 'Invite new users'),
    ('users.edit', 'users', 'Edit user details'),
    ('users.remove', 'users', 'Remove users'),
    ('users.roles', 'users', 'Assign/change roles'),
    ('reports.read', 'reports', 'View reports'),
    ('reports.export', 'reports', 'Export data'),
    ('sites.read', 'sites', 'View sites'),
    ('sites.write', 'sites', 'Manage sites'),
    ('subscriptions.read', 'subscriptions', 'View subscription'),
    ('subscriptions.write', 'subscriptions', 'Manage subscription'),
    ('maintenance.read', 'maintenance', 'View maintenance windows'),
    ('maintenance.write', 'maintenance', 'Manage maintenance windows'),
    ('settings.read', 'settings', 'View settings')
ON CONFLICT (action) DO NOTHING;

-- Seed: 6 System Roles + their permission mappings
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    -- Viewer
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Viewer';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Viewer', 'Read-only access to all areas', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    WHERE p.action IN (
        'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
        'integrations.read', 'users.read', 'reports.read', 'sites.read',
        'subscriptions.read', 'maintenance.read', 'settings.read'
    )
    ON CONFLICT DO NOTHING;

    -- Device Manager
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Device Manager';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Device Manager', 'Viewer + device management', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    WHERE p.action IN (
        'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
        'integrations.read', 'users.read', 'reports.read', 'sites.read',
        'subscriptions.read', 'maintenance.read', 'settings.read',
        'devices.write', 'devices.create', 'devices.delete', 'devices.commands'
    )
    ON CONFLICT DO NOTHING;

    -- Alert Manager
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Alert Manager';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Alert Manager', 'Viewer + alert management', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    WHERE p.action IN (
        'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
        'integrations.read', 'users.read', 'reports.read', 'sites.read',
        'subscriptions.read', 'maintenance.read', 'settings.read',
        'alerts.acknowledge', 'alerts.close', 'alerts.rules.write', 'maintenance.write'
    )
    ON CONFLICT DO NOTHING;

    -- Integration Manager
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Integration Manager';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Integration Manager', 'Viewer + integration management', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    WHERE p.action IN (
        'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
        'integrations.read', 'users.read', 'reports.read', 'sites.read',
        'subscriptions.read', 'maintenance.read', 'settings.read',
        'integrations.write', 'integrations.routes'
    )
    ON CONFLICT DO NOTHING;

    -- Team Admin
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Team Admin';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Team Admin', 'Viewer + user management', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    WHERE p.action IN (
        'dashboard.read', 'devices.read', 'alerts.read', 'alerts.rules.read',
        'integrations.read', 'users.read', 'reports.read', 'sites.read',
        'subscriptions.read', 'maintenance.read', 'settings.read',
        'users.invite', 'users.edit', 'users.remove', 'users.roles'
    )
    ON CONFLICT DO NOTHING;

    -- Full Admin
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Full Admin';
    IF v_role_id IS NULL THEN
        INSERT INTO roles (id, tenant_id, name, description, is_system)
        VALUES (gen_random_uuid(), NULL, 'Full Admin', 'All permissions', true)
        RETURNING id INTO v_role_id;
    END IF;

    INSERT INTO role_permissions (role_id, permission_id)
    SELECT v_role_id, p.id FROM permissions p
    ON CONFLICT DO NOTHING;
END $$;

-- Grants
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

