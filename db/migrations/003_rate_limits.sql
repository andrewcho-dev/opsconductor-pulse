-- Migration: 003_rate_limits.sql
-- Purpose: Rate limiting table for test delivery and other endpoints
-- Date: 2026-02-02

CREATE TABLE IF NOT EXISTS rate_limits (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS rate_limits_lookup_idx
    ON rate_limits(tenant_id, action, created_at DESC);

COMMENT ON TABLE rate_limits IS 'Rate limiting entries for tenant-scoped actions';
