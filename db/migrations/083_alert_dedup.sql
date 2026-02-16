BEGIN;

-- Track how many times an alert has been re-triggered while still open/acknowledged
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS trigger_count INTEGER NOT NULL DEFAULT 1;

-- Track when the alert was last re-triggered
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS last_triggered_at TIMESTAMPTZ NULL;

-- Link alert to the rule that created it (nullable for legacy/heartbeat alerts)
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS rule_id UUID NULL;

-- Backfill last_triggered_at from created_at for existing rows
UPDATE fleet_alert
SET last_triggered_at = created_at
WHERE last_triggered_at IS NULL;

-- Set default for new rows
ALTER TABLE fleet_alert
    ALTER COLUMN last_triggered_at SET DEFAULT now();

-- Index for the dedup lookup query
CREATE INDEX IF NOT EXISTS idx_fleet_alert_dedup
    ON fleet_alert (device_id, rule_id, status)
    WHERE status IN ('OPEN', 'ACKNOWLEDGED');

-- Note: We do NOT add a foreign key to alert_rules because:
-- 1. alert_rules uses (tenant_id, rule_id) as logical key but rule_id is UUID, not the PK
-- 2. Heartbeat/system alerts have no rule_id
-- 3. If a rule is deleted, we still want to keep the alert history

COMMENT ON COLUMN fleet_alert.trigger_count IS 'Number of times this alert has been triggered while open. Starts at 1.';
COMMENT ON COLUMN fleet_alert.last_triggered_at IS 'Timestamp of the most recent trigger (may differ from created_at if re-triggered).';
COMMENT ON COLUMN fleet_alert.rule_id IS 'The rule_id from alert_rules that created this alert. NULL for heartbeat/system alerts.';

COMMIT;

