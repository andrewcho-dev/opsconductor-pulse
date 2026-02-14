BEGIN;

ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS silenced_until TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS acknowledged_by TEXT NULL,
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN fleet_alert.silenced_until IS
    'If set and > now(), evaluator skips re-alerting for this fingerprint.';
COMMENT ON COLUMN fleet_alert.acknowledged_by IS
    'User sub or email of the user who acknowledged this alert.';
COMMENT ON COLUMN fleet_alert.acknowledged_at IS
    'When the alert was acknowledged.';

CREATE INDEX IF NOT EXISTS idx_fleet_alert_silenced
    ON fleet_alert(tenant_id, silenced_until)
    WHERE silenced_until IS NOT NULL;

DROP INDEX IF EXISTS fleet_alert_open_uq;
DROP INDEX IF EXISTS idx_fleet_alert_open_uq;
CREATE UNIQUE INDEX idx_fleet_alert_open_uq
    ON fleet_alert(tenant_id, fingerprint)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');

COMMIT;
