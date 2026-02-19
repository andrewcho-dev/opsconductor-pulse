-- Migration 113: Device registry template FK + parent device hierarchy
-- Adds:
-- - template_id: FK to device_templates (device type definition)
-- - parent_device_id: gateway hierarchy (validated within tenant via trigger)

BEGIN;

-- Add template reference
ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS template_id INT REFERENCES device_templates(id) ON DELETE SET NULL;

-- Add parent device reference (for gateway → peripheral hierarchy)
ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS parent_device_id TEXT;

-- Parent validation trigger (parent must exist in same tenant)
CREATE OR REPLACE FUNCTION validate_parent_device()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_device_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM device_registry
            WHERE tenant_id = NEW.tenant_id
              AND device_id = NEW.parent_device_id
        ) THEN
            RAISE EXCEPTION 'parent_device_id % not found in tenant %', NEW.parent_device_id, NEW.tenant_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_parent_device ON device_registry;
CREATE TRIGGER trg_validate_parent_device
    BEFORE INSERT OR UPDATE OF parent_device_id ON device_registry
    FOR EACH ROW
    WHEN (NEW.parent_device_id IS NOT NULL)
    EXECUTE FUNCTION validate_parent_device();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_device_registry_template ON device_registry(template_id)
    WHERE template_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_device_registry_parent ON device_registry(tenant_id, parent_device_id)
    WHERE parent_device_id IS NOT NULL;

-- Comments
COMMENT ON COLUMN device_registry.template_id IS 'FK to device_templates defining this device type. NULL during migration period — new code should always set this.';
COMMENT ON COLUMN device_registry.parent_device_id IS 'Parent gateway device_id for peripheral/child devices. NULL for standalone devices and gateways.';

COMMIT;

