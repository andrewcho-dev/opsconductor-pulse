BEGIN;

ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS escalation_level INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN fleet_alert.escalation_level IS
    'Number of times this alert has been escalated (0 = not escalated).';
COMMENT ON COLUMN fleet_alert.escalated_at IS
    'Timestamp of the most recent escalation.';

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS escalation_minutes INT NULL;

COMMENT ON COLUMN alert_rules.escalation_minutes IS
    'If set, OPEN alerts not acknowledged within this many minutes will be escalated once. NULL = no escalation.';

CREATE INDEX IF NOT EXISTS idx_fleet_alert_escalation
    ON fleet_alert(tenant_id, status, created_at)
    WHERE status = 'OPEN' AND escalation_level = 0;

COMMIT;
