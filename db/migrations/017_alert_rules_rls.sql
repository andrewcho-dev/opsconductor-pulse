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
