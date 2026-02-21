# Task 005 — Add `sensor_limit` to Device Tiers

## Migration File

Create `db/migrations/103_sensor_limit_on_tiers.sql`

## Context

Each device tier (basic, standard, premium) should define a default maximum number of sensors per device. When a device is assigned to a tier, it inherits that tier's sensor limit unless explicitly overridden on the device itself.

Current tiers (from migration 097):
- `basic` (tier_id=1): telemetry + alerts + dashboards
- `standard` (tier_id=2): + OTA, analytics, streaming export
- `premium` (tier_id=3): full features including x509, message routing

## SQL

```sql
-- Migration 103: Add default sensor_limit to device tiers
-- Each tier defines how many sensors a device of that tier can have.
-- Individual devices can override via device_registry.sensor_limit.

ALTER TABLE device_tiers ADD COLUMN IF NOT EXISTS default_sensor_limit INT NOT NULL DEFAULT 10;

COMMENT ON COLUMN device_tiers.default_sensor_limit IS
    'Default maximum sensors per device for this tier. Devices inherit this unless overridden.';

-- Set tier-specific defaults
UPDATE device_tiers SET default_sensor_limit = 5  WHERE name = 'basic';
UPDATE device_tiers SET default_sensor_limit = 15 WHERE name = 'standard';
UPDATE device_tiers SET default_sensor_limit = 30 WHERE name = 'premium';

-- Also update subscription_plans.limits JSONB to document sensor limits per plan
UPDATE subscription_plans
SET limits = limits || '{"default_sensor_limit_per_device": 5}'::JSONB
WHERE plan_id = 'starter';

UPDATE subscription_plans
SET limits = limits || '{"default_sensor_limit_per_device": 15}'::JSONB
WHERE plan_id = 'pro';

UPDATE subscription_plans
SET limits = limits || '{"default_sensor_limit_per_device": 30}'::JSONB
WHERE plan_id = 'enterprise';
```

## Sensor Limit Resolution Logic (for Phase 150 backend implementation)

When checking if a device can accept a new sensor, the resolution order is:

1. **Device-level override** — `device_registry.sensor_limit` (if explicitly set and non-NULL)
2. **Tier default** — `device_tiers.default_sensor_limit` (via device's tier_id)
3. **System fallback** — 20 (the column default on device_registry)

```python
# Pseudocode for Phase 150:
effective_limit = device.sensor_limit or tier.default_sensor_limit or 20
current_count = SELECT COUNT(*) FROM sensors WHERE tenant_id = ? AND device_id = ?
if current_count >= effective_limit:
    # Reject or warn
```

## Verification

```bash
psql -d iot -f db/migrations/103_sensor_limit_on_tiers.sql
psql -d iot -c "SELECT name, default_sensor_limit FROM device_tiers ORDER BY sort_order;"
# Expected:
# basic    | 5
# standard | 15
# premium  | 30
psql -d iot -c "SELECT plan_id, limits->>'default_sensor_limit_per_device' FROM subscription_plans;"
```
