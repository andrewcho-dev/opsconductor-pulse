-- Migration 087: User preferences (timezone, display name, notification prefs)
-- Date: 2026-02-16

BEGIN;

CREATE TABLE IF NOT EXISTS user_preferences (
    tenant_id           TEXT NOT NULL,
    user_id             TEXT NOT NULL,       -- Keycloak sub claim
    display_name        VARCHAR(100),
    timezone            VARCHAR(50) NOT NULL DEFAULT 'UTC',
    notification_prefs  JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, user_id)
);

-- Enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy (same pattern as user_role_assignments)
DROP POLICY IF EXISTS user_preferences_tenant_isolation ON user_preferences;
CREATE POLICY user_preferences_tenant_isolation
    ON user_preferences
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Index for fast lookup by user
CREATE INDEX IF NOT EXISTS idx_user_preferences_user
    ON user_preferences (tenant_id, user_id);

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO pulse_operator;

COMMIT;

