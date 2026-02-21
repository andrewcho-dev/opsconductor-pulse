# Phase 104 — Migration 074: duration_minutes

## File to create
`db/migrations/074_alert_rule_duration.sql`

```sql
-- Migration 074: Add duration_minutes to alert_rules
-- NULL = instant fire (existing behaviour preserved)
-- integer > 0 = condition must hold for N continuous minutes

ALTER TABLE alert_rules
  ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT NULL
    CHECK (duration_minutes IS NULL OR duration_minutes > 0);

COMMENT ON COLUMN alert_rules.duration_minutes IS
  'If set, alert fires only when condition holds for this many consecutive minutes. NULL = fire on first sample.';

-- Verify
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'alert_rules' AND column_name = 'duration_minutes';
```

## Apply

```bash
docker exec iot-postgres psql -U iot iotcloud \
  -f /migrations/074_alert_rule_duration.sql
```

Or run via the migration runner if one exists in the project.
