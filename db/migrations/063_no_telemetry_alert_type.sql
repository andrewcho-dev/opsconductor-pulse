BEGIN;

DO $$
DECLARE
    fleet_constraint_exists boolean;
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
            CHECK (alert_type IN (
                'NO_HEARTBEAT', 'THRESHOLD', 'SYSTEM_HEALTH', 'ANOMALY', 'NO_TELEMETRY'
            ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_telemetry_device_metric_time
    ON telemetry(tenant_id, device_id, time DESC)
    WHERE msg_type = 'telemetry';

COMMIT;
