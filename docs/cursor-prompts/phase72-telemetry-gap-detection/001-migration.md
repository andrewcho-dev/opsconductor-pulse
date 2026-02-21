# Prompt 001 — Migration: NO_TELEMETRY Alert Type

Create `db/migrations/063_no_telemetry_alert_type.sql`:

```sql
BEGIN;

-- Add NO_TELEMETRY to fleet_alert alert_type constraint (if CHECK exists)
-- First check migration 060 — it already handled ANOMALY.
-- Follow the same pattern: DROP IF EXISTS, recreate with new value.

ALTER TABLE fleet_alert
    DROP CONSTRAINT IF EXISTS chk_fleet_alert_type;

ALTER TABLE fleet_alert
    ADD CONSTRAINT chk_fleet_alert_type
    CHECK (alert_type IN (
        'NO_HEARTBEAT', 'THRESHOLD', 'SYSTEM_HEALTH', 'ANOMALY', 'NO_TELEMETRY'
    ));

-- Index for evaluator gap detection queries
CREATE INDEX IF NOT EXISTS idx_telemetry_device_metric_time
    ON telemetry(tenant_id, device_id, time DESC)
    WHERE msg_type = 'telemetry';

COMMIT;
```

Note: If the `chk_fleet_alert_type` constraint was already expanded in migration 060 to include ANOMALY, this migration adds `NO_TELEMETRY` to it. Cursor must read the current state of the constraint before writing — check migrations 000 and 060.

## Acceptance Criteria

- [ ] `063_no_telemetry_alert_type.sql` exists
- [ ] `NO_TELEMETRY` allowed in `fleet_alert.alert_type`
- [ ] `idx_telemetry_device_metric_time` index created
- [ ] `pytest -m unit -v` passes
