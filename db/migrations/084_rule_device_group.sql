BEGIN;

-- Add single device group scoping column
-- This references device_groups(group_id) but we use a simple column
-- because the FK would need (tenant_id, group_id) composite key.
ALTER TABLE alert_rules
    ADD COLUMN IF NOT EXISTS device_group_id TEXT NULL;

COMMENT ON COLUMN alert_rules.device_group_id IS
    'If set, this rule only evaluates devices in this device group. NULL means evaluate all devices (or use group_ids array).';

-- Index for looking up rules by device_group_id
CREATE INDEX IF NOT EXISTS idx_alert_rules_device_group
    ON alert_rules (tenant_id, device_group_id)
    WHERE device_group_id IS NOT NULL;

COMMIT;

