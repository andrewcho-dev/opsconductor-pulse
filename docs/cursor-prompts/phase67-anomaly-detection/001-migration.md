# Prompt 001 — Migration: ANOMALY Alert Type

Read existing migrations to check if there is a CHECK constraint on `fleet_alert.alert_type` or `alert_rules.rule_type`.

Create `db/migrations/060_anomaly_alert_type.sql`:

```sql
BEGIN;

-- Add ANOMALY to fleet_alert alert_type if a CHECK constraint exists
-- Check migration 000 or others for chk_fleet_alert_type constraint
-- If it exists, drop and recreate to include ANOMALY:
ALTER TABLE fleet_alert
    DROP CONSTRAINT IF EXISTS chk_fleet_alert_type;

ALTER TABLE fleet_alert
    ADD CONSTRAINT chk_fleet_alert_type
    CHECK (alert_type IN ('NO_HEARTBEAT', 'THRESHOLD', 'SYSTEM_HEALTH', 'ANOMALY'));

-- Add ANOMALY rule_type to alert_rules if a CHECK constraint exists
ALTER TABLE alert_rules
    DROP CONSTRAINT IF EXISTS chk_alert_rules_rule_type;

-- No constraint to add if rule_type has no check — confirm first.
-- Only add if a CHECK existed before.

-- Index for efficient anomaly rule queries
CREATE INDEX IF NOT EXISTS idx_alert_rules_anomaly
    ON alert_rules(tenant_id, rule_type)
    WHERE rule_type = 'anomaly' AND enabled = true;

COMMIT;
```

Note: Before writing the migration, check if `chk_fleet_alert_type` exists. If no CHECK constraint exists on `alert_type`, skip the ALTER and just add the index. Do NOT break existing data.

## Acceptance Criteria

- [ ] `db/migrations/060_anomaly_alert_type.sql` exists
- [ ] `ANOMALY` allowed in `fleet_alert.alert_type`
- [ ] Index `idx_alert_rules_anomaly` created
- [ ] `pytest -m unit -v` passes
