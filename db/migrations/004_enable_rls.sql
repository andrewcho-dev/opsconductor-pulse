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
