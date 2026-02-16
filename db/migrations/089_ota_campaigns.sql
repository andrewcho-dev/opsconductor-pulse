-- Migration 089: OTA Campaigns
-- An OTA campaign targets a device group with a specific firmware version.
-- Supports linear and canary rollout strategies with automatic abort on failure threshold.

BEGIN;

CREATE TABLE IF NOT EXISTS ota_campaigns (
    id                  SERIAL        PRIMARY KEY,
    tenant_id           TEXT          NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name                VARCHAR(100)  NOT NULL,
    firmware_version_id INT           NOT NULL REFERENCES firmware_versions(id) ON DELETE RESTRICT,
    target_group_id     TEXT          NOT NULL,
    rollout_strategy    VARCHAR(20)   NOT NULL DEFAULT 'linear'
                        CHECK (rollout_strategy IN ('linear', 'canary')),
    rollout_rate        INT           NOT NULL DEFAULT 10,
    abort_threshold     FLOAT         NOT NULL DEFAULT 0.1,
    status              VARCHAR(20)   NOT NULL DEFAULT 'CREATED'
                        CHECK (status IN ('CREATED', 'RUNNING', 'PAUSED', 'COMPLETED', 'ABORTED')),
    total_devices       INT           NOT NULL DEFAULT 0,
    succeeded           INT           NOT NULL DEFAULT 0,
    failed              INT           NOT NULL DEFAULT 0,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by          TEXT
);

CREATE INDEX IF NOT EXISTS idx_ota_campaigns_tenant
    ON ota_campaigns (tenant_id);

CREATE INDEX IF NOT EXISTS idx_ota_campaigns_status
    ON ota_campaigns (tenant_id, status);

ALTER TABLE ota_campaigns ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ota_campaigns_tenant_isolation ON ota_campaigns;
CREATE POLICY ota_campaigns_tenant_isolation ON ota_campaigns
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;

