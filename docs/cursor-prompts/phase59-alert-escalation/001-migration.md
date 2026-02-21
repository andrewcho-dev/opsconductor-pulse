# Prompt 001 — Migration: Escalation Columns

Create `db/migrations/059_alert_escalation.sql`:

```sql
BEGIN;

-- Add escalation tracking to fleet_alert
ALTER TABLE fleet_alert
    ADD COLUMN IF NOT EXISTS escalation_level  INT          NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS escalated_at      TIMESTAMPTZ  NULL;

COMMENT ON COLUMN fleet_alert.escalation_level IS
    'Number of times this alert has been escalated (0 = not escalated).';
COMMENT ON COLUMN fleet_alert.escalated_at IS
    'Timestamp of the most recent escalation.';

-- Add escalation config to alert_rules
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS escalation_minutes INT NULL;

COMMENT ON COLUMN alert_rules.escalation_minutes IS
    'If set, OPEN alerts not acknowledged within this many minutes will be escalated once. NULL = no escalation.';

-- Index for efficient escalation queries
CREATE INDEX IF NOT EXISTS idx_fleet_alert_escalation
    ON fleet_alert(tenant_id, status, created_at)
    WHERE status = 'OPEN' AND escalation_level = 0;

COMMIT;
```

## Acceptance Criteria

- [ ] Migration file `db/migrations/059_alert_escalation.sql` exists
- [ ] `fleet_alert` gains `escalation_level INT DEFAULT 0` and `escalated_at TIMESTAMPTZ NULL`
- [ ] `alert_rules` gains `escalation_minutes INT NULL`
- [ ] Index `idx_fleet_alert_escalation` created
- [ ] `pytest -m unit -v` passes (FakeConn tests unaffected)
