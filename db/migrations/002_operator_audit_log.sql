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
