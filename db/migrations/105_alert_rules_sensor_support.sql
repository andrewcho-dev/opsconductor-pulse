-- Migration 105: Add sensor targeting to alert rules

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS sensor_id INT
        REFERENCES sensors(sensor_id) ON DELETE SET NULL;

ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS sensor_type TEXT;

COMMENT ON COLUMN alert_rules.sensor_id IS
    'If set, this rule only applies to this specific sensor. NULL = applies to all sensors matching metric_name.';

COMMENT ON COLUMN alert_rules.sensor_type IS
    'If set, this rule applies to all sensors of this type (e.g., "temperature"). NULL = applies to metric_name matching.';

CREATE INDEX IF NOT EXISTS idx_alert_rules_sensor ON alert_rules(sensor_id)
    WHERE sensor_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alert_rules_sensor_type ON alert_rules(tenant_id, sensor_type)
    WHERE sensor_type IS NOT NULL;

