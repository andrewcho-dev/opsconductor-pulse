-- Migration 088: Firmware Versions Registry
-- Stores metadata about firmware binaries available for OTA deployment.

BEGIN;

CREATE TABLE IF NOT EXISTS firmware_versions (
    id              SERIAL       PRIMARY KEY,
    tenant_id       TEXT         NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    version         VARCHAR(50)  NOT NULL,
    description     TEXT,
    file_url        TEXT         NOT NULL,
    file_size_bytes BIGINT,
    checksum_sha256 VARCHAR(64),
    device_type     VARCHAR(50),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by      TEXT,

    CONSTRAINT uq_firmware_tenant_version UNIQUE (tenant_id, version, device_type)
);

CREATE INDEX IF NOT EXISTS idx_firmware_versions_tenant
    ON firmware_versions (tenant_id);

CREATE INDEX IF NOT EXISTS idx_firmware_versions_device_type
    ON firmware_versions (tenant_id, device_type);

ALTER TABLE firmware_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS firmware_versions_tenant_isolation ON firmware_versions;
CREATE POLICY firmware_versions_tenant_isolation ON firmware_versions
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;

