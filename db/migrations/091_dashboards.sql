-- Migration 091: Customizable Dashboards
-- Creates dashboards and dashboard_widgets tables with RLS policies.
-- Date: 2026-02-16

BEGIN;

-- ============================================================
-- DASHBOARDS
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboards (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    user_id         VARCHAR(255),        -- NULL = shared dashboard, non-NULL = personal
    name            VARCHAR(100) NOT NULL,
    description     TEXT DEFAULT '',
    is_default      BOOLEAN NOT NULL DEFAULT false,
    layout          JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboards_tenant ON dashboards(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_tenant_user ON dashboards(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_default ON dashboards(tenant_id, is_default) WHERE is_default = true;

ALTER TABLE dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboards FORCE ROW LEVEL SECURITY;

-- Tenant isolation: tenant users can see their own + shared dashboards
DROP POLICY IF EXISTS dashboards_tenant_isolation ON dashboards;
CREATE POLICY dashboards_tenant_isolation
    ON dashboards
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- ============================================================
-- DASHBOARD WIDGETS
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboard_widgets (
    -- RLS: EXEMPT - no tenant_id column; access constrained through dashboard_id parent policies
    id              SERIAL PRIMARY KEY,
    dashboard_id    INT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    widget_type     VARCHAR(50) NOT NULL,
    title           VARCHAR(100) NOT NULL DEFAULT '',
    config          JSONB NOT NULL DEFAULT '{}',
    position        JSONB NOT NULL DEFAULT '{"x": 0, "y": 0, "w": 2, "h": 2}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard ON dashboard_widgets(dashboard_id);

-- RLS: widgets inherit access from their parent dashboard via join
ALTER TABLE dashboard_widgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_widgets FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dashboard_widgets_tenant_isolation ON dashboard_widgets;
CREATE POLICY dashboard_widgets_tenant_isolation
    ON dashboard_widgets
    FOR ALL
    TO pulse_app
    USING (
        EXISTS (
            SELECT 1 FROM dashboards d
            WHERE d.id = dashboard_widgets.dashboard_id
            AND d.tenant_id = current_setting('app.tenant_id', true)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM dashboards d
            WHERE d.id = dashboard_widgets.dashboard_id
            AND d.tenant_id = current_setting('app.tenant_id', true)
        )
    );

-- ============================================================
-- GRANTS
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboards TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboards TO pulse_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard_widgets TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard_widgets TO pulse_operator;
GRANT USAGE ON SEQUENCE dashboards_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dashboards_id_seq TO pulse_operator;
GRANT USAGE ON SEQUENCE dashboard_widgets_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dashboard_widgets_id_seq TO pulse_operator;

-- Add dashboard permissions to the permissions table (from migration 080)
INSERT INTO permissions (action, category, description) VALUES
    ('dashboard.write', 'dashboard', 'Create, edit, delete dashboards'),
    ('dashboard.share', 'dashboard', 'Share dashboards with team')
ON CONFLICT (action) DO NOTHING;

-- Grant dashboard.write to roles that already have dashboard.read
INSERT INTO role_permissions (role_id, permission_id)
SELECT rp.role_id, p.id
FROM role_permissions rp
JOIN permissions existing ON existing.id = rp.permission_id AND existing.action = 'dashboard.read'
JOIN permissions p ON p.action = 'dashboard.write'
ON CONFLICT DO NOTHING;

COMMIT;

