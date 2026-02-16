-- Migration 090: OTA Per-Device Status
-- Tracks individual device progress within an OTA campaign.

BEGIN;

CREATE TABLE IF NOT EXISTS ota_device_status (
    id              BIGSERIAL     PRIMARY KEY,
    tenant_id       TEXT          NOT NULL,
    campaign_id     INT           NOT NULL REFERENCES ota_campaigns(id) ON DELETE CASCADE,
    device_id       VARCHAR       NOT NULL,
    status          VARCHAR(20)   NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'DOWNLOADING', 'INSTALLING', 'SUCCESS', 'FAILED', 'SKIPPED')),
    progress_pct    INT           NOT NULL DEFAULT 0
                    CHECK (progress_pct >= 0 AND progress_pct <= 100),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ota_device_campaign UNIQUE (tenant_id, campaign_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_ota_device_status_campaign
    ON ota_device_status (tenant_id, campaign_id);

CREATE INDEX IF NOT EXISTS idx_ota_device_status_pending
    ON ota_device_status (tenant_id, campaign_id, status)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_ota_device_status_device
    ON ota_device_status (tenant_id, device_id);

ALTER TABLE ota_device_status ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ota_device_status_tenant_isolation ON ota_device_status;
CREATE POLICY ota_device_status_tenant_isolation ON ota_device_status
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;

