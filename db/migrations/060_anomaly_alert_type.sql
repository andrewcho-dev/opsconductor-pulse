BEGIN;

DO $$
DECLARE
    fleet_constraint_exists boolean;
    rules_constraint_exists boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_fleet_alert_type'
          AND conrelid = 'fleet_alert'::regclass
    )
    INTO fleet_constraint_exists;

    IF fleet_constraint_exists THEN
        ALTER TABLE fleet_alert
            DROP CONSTRAINT chk_fleet_alert_type;

        ALTER TABLE fleet_alert
            ADD CONSTRAINT chk_fleet_alert_type
            CHECK (alert_type IN ('NO_HEARTBEAT', 'THRESHOLD', 'SYSTEM_HEALTH', 'ANOMALY'));
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_alert_rules_rule_type'
          AND conrelid = 'alert_rules'::regclass
    )
    INTO rules_constraint_exists;

    IF rules_constraint_exists THEN
        ALTER TABLE alert_rules
            DROP CONSTRAINT chk_alert_rules_rule_type;

        ALTER TABLE alert_rules
            ADD CONSTRAINT chk_alert_rules_rule_type
            CHECK (rule_type IN ('threshold', 'anomaly'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_alert_rules_anomaly
    ON alert_rules(tenant_id, rule_type)
    WHERE rule_type = 'anomaly' AND enabled = true;

COMMIT;
