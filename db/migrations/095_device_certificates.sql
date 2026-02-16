-- Migration 095: Device certificate identity infrastructure
-- Phase 131 - X.509 Certificate Device Identity
-- Date: 2026-02-16

BEGIN;

CREATE TABLE IF NOT EXISTS device_certificates (
    id                 SERIAL PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    device_id           TEXT NOT NULL,
    cert_pem            TEXT NOT NULL,
    fingerprint_sha256  VARCHAR(64) NOT NULL UNIQUE,
    common_name         VARCHAR(200) NOT NULL,
    issuer              VARCHAR(200) NOT NULL,
    serial_number       VARCHAR(100) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                        CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
    not_before          TIMESTAMPTZ NOT NULL,
    not_after           TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ,
    revoked_reason      VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Foreign key to device_registry
ALTER TABLE device_certificates
    DROP CONSTRAINT IF EXISTS fk_device_certificates_device;
ALTER TABLE device_certificates
    ADD CONSTRAINT fk_device_certificates_device
    FOREIGN KEY (tenant_id, device_id)
    REFERENCES device_registry(tenant_id, device_id)
    ON DELETE CASCADE;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_certificates_tenant_device
    ON device_certificates(tenant_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_certificates_fingerprint
    ON device_certificates(fingerprint_sha256);
CREATE INDEX IF NOT EXISTS idx_device_certificates_status_expiry
    ON device_certificates(status, not_after);
CREATE INDEX IF NOT EXISTS idx_device_certificates_tenant
    ON device_certificates(tenant_id);

-- RLS
ALTER TABLE device_certificates ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_certificates_tenant_isolation ON device_certificates;
CREATE POLICY device_certificates_tenant_isolation
    ON device_certificates
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Operator bypass (read-only for fleet overview)
DROP POLICY IF EXISTS device_certificates_operator_read ON device_certificates;
CREATE POLICY device_certificates_operator_read
    ON device_certificates
    FOR SELECT
    TO pulse_operator
    USING (true);

COMMIT;

