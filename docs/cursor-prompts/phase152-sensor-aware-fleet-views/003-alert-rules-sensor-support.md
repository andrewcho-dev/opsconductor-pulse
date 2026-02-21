# Task 003 — Alert Rules Sensor Support

## Context

Alert rules currently target a `metric_name` globally. With sensors as entities, users should be able to create rules that target:
- A specific sensor on a specific device
- All sensors of a given type across the fleet
- A metric name across all devices (existing behavior)

This is additive — existing alert rule behavior stays the same.

## Files to Modify

### 1. Backend: Add sensor_id to alert_rules table

**File:** Create `db/migrations/105_alert_rules_sensor_support.sql`

```sql
-- Migration 105: Add sensor targeting to alert rules
ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS sensor_id INT
    REFERENCES sensors(sensor_id) ON DELETE SET NULL;

ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS sensor_type TEXT;

COMMENT ON COLUMN alert_rules.sensor_id IS
    'If set, this rule only applies to this specific sensor. NULL = applies to all sensors matching metric_name.';
COMMENT ON COLUMN alert_rules.sensor_type IS
    'If set, this rule applies to all sensors of this type (e.g., "temperature"). NULL = applies to metric_name matching.';

CREATE INDEX idx_alert_rules_sensor ON alert_rules(sensor_id)
    WHERE sensor_id IS NOT NULL;
CREATE INDEX idx_alert_rules_sensor_type ON alert_rules(tenant_id, sensor_type)
    WHERE sensor_type IS NOT NULL;
```

### 2. Backend: Update alert rule evaluation

**File:** `services/ui_iot/routes/alert_rules.py` (or wherever alert rule CRUD lives)

In the create/update endpoints, accept optional `sensor_id` and `sensor_type` fields. Validate that:
- If `sensor_id` is provided, it exists and belongs to the tenant
- If `sensor_type` is provided, it's a valid sensor type string
- Only one targeting mode is used: `sensor_id` OR `sensor_type` OR bare `metric_name`

### 3. Frontend: Update alert rule create/edit form

**File:** `frontend/src/features/alerts/` (find the alert rule creation form)

Add a targeting mode selector:
- **By metric name** (existing) — simple text input for metric_name
- **By specific sensor** — device selector → sensor selector (from Phase 152 task 001 pattern)
- **By sensor type** — dropdown of sensor types

When "By specific sensor" is chosen:
1. Show device picker
2. Show sensor picker (populated from `listDeviceSensors`)
3. Set `sensor_id` on the rule, auto-fill `metric_name` from the sensor

When "By sensor type" is chosen:
1. Show sensor type dropdown
2. Set `sensor_type` on the rule
3. The rule applies to ALL sensors of that type

### 4. Frontend: Update alert rule types

**File:** `frontend/src/services/api/types.ts`

Add to `AlertRule` interface:
```typescript
export interface AlertRule {
  // ... existing fields ...
  sensor_id?: number | null;
  sensor_type?: string | null;
}
```

## Notes

- The evaluator service that actually fires alerts based on incoming telemetry will need to be updated in a future phase to check `sensor_id` / `sensor_type` targeting. For now, the UI and database support is sufficient.
- Existing alert rules with just `metric_name` continue to work exactly as before.

## Verification

```bash
psql -d iot -f db/migrations/105_alert_rules_sensor_support.sql
cd frontend && npx tsc --noEmit && npm run build
```
