-- Migration: 024_device_extended_attributes.sql
-- Purpose: Extend device attributes and add device tags
-- Date: 2026-02-09

-- ============================================
-- 1. Extend device_registry attributes
-- ============================================

ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS location_source TEXT DEFAULT 'auto'
        CHECK (location_source IN ('auto', 'manual')),
    ADD COLUMN IF NOT EXISTS mac_address TEXT,
    ADD COLUMN IF NOT EXISTS imei TEXT,
    ADD COLUMN IF NOT EXISTS iccid TEXT,
    ADD COLUMN IF NOT EXISTS serial_number TEXT,
    ADD COLUMN IF NOT EXISTS model TEXT,
    ADD COLUMN IF NOT EXISTS manufacturer TEXT,
    ADD COLUMN IF NOT EXISTS hw_revision TEXT,
    ADD COLUMN IF NOT EXISTS fw_version TEXT,
    ADD COLUMN IF NOT EXISTS notes TEXT;

-- ============================================
-- 2. Tags table
-- ============================================

CREATE TABLE IF NOT EXISTS device_tags (
    tenant_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (tenant_id, device_id, tag),
    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry (tenant_id, device_id)
        ON DELETE CASCADE
);

-- ============================================
-- 3. RLS for device_tags
-- ============================================

ALTER TABLE device_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_tags FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON device_tags
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON POLICY tenant_isolation_policy ON device_tags
    IS 'Restrict access to rows matching app.tenant_id session variable';

-- ============================================
-- 4. Grants
-- ============================================

GRANT SELECT, INSERT, UPDATE, DELETE ON device_tags TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON device_tags TO pulse_operator;
