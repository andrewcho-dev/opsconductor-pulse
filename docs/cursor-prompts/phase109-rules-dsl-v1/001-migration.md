# Phase 109 — Migration 078: match_mode + conditions backfill

## File to create
`db/migrations/078_alert_rule_match_mode.sql`

```sql
-- Migration 078: Rules DSL v1 — multi-condition AND/OR
--
-- The alert_rules table already has a conditions JSONB column (default '{}').
-- This migration:
--   1. Adds match_mode column ('all' = AND, 'any' = OR).
--   2. Backfills conditions array from existing single-condition fields
--      for all rules that have metric_name set and conditions = '{}'.
--   3. Adds a GIN index on conditions for future query patterns.

-- Step 1: add match_mode
ALTER TABLE alert_rules
  ADD COLUMN IF NOT EXISTS match_mode TEXT NOT NULL DEFAULT 'all'
    CHECK (match_mode IN ('all', 'any'));

COMMENT ON COLUMN alert_rules.match_mode IS
  '"all" = all conditions must be true (AND). "any" = any condition true (OR).';

-- Step 2: backfill conditions from legacy single-condition fields
-- Only affects rows where conditions is empty AND metric_name is set.
-- Preserves duration_minutes if set on the rule.
UPDATE alert_rules
SET conditions = jsonb_build_array(
    jsonb_build_object(
        'metric_name',     metric_name,
        'operator',        operator,
        'threshold',       threshold,
        'duration_minutes', duration_minutes  -- may be NULL, that's fine
    )
)
WHERE metric_name IS NOT NULL
  AND conditions = '{}'::jsonb;

-- Step 3: GIN index on conditions for future query use
CREATE INDEX IF NOT EXISTS idx_alert_rules_conditions_gin
  ON alert_rules USING GIN (conditions);

-- Verify
SELECT
    COUNT(*) FILTER (WHERE conditions != '[]' AND conditions != '{}') AS rules_with_conditions,
    COUNT(*) FILTER (WHERE match_mode = 'all') AS and_rules,
    COUNT(*) FILTER (WHERE match_mode = 'any') AS or_rules
FROM alert_rules;
```

## Apply

```bash
docker exec -i iot-postgres psql -U iot iotcloud \
  < db/migrations/078_alert_rule_match_mode.sql
```

## Verify backfill

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT rule_id, metric_name, conditions, match_mode
   FROM alert_rules
   WHERE metric_name IS NOT NULL
   LIMIT 3;"
```

Expected: `conditions` is now a JSON array like
`[{"operator": "GT", "threshold": 40, "metric_name": "temp_c", "duration_minutes": null}]`
for each existing rule that previously used single-condition fields.
