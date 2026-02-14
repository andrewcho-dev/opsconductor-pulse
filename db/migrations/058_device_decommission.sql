BEGIN;

ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS decommissioned_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN device_registry.decommissioned_at IS
    'Set when device is decommissioned. NULL means active.';

COMMIT;
