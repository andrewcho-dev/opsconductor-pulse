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

