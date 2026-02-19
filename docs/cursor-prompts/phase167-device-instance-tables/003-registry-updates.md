# Task 3: Device Registry FK Additions (Migration 113)

## Create file: `db/migrations/113_device_registry_template_fk.sql`

Add `template_id` and `parent_device_id` columns to `device_registry`.

```sql
-- Add template reference
ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS template_id INT REFERENCES device_templates(id) ON DELETE SET NULL;

-- Add parent device reference (for gateway → peripheral hierarchy)
ALTER TABLE device_registry
    ADD COLUMN IF NOT EXISTS parent_device_id TEXT;

-- Can't use a simple FK for parent_device_id because device_registry has a composite PK (tenant_id, device_id).
-- The parent must be in the same tenant, so add a composite FK:
-- But first we need to ensure parent_device_id is only valid within the same tenant.
-- Use a trigger or application-layer validation instead, since the FK would need
-- to reference (tenant_id, parent_device_id) but parent_device_id alone doesn't carry tenant_id.
--
-- Solution: Add a check via trigger that validates parent exists in same tenant.

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

CREATE TRIGGER trg_validate_parent_device
    BEFORE INSERT OR UPDATE OF parent_device_id ON device_registry
    FOR EACH ROW
    WHEN (NEW.parent_device_id IS NOT NULL)
    EXECUTE FUNCTION validate_parent_device();
```

### Indexes

```sql
CREATE INDEX idx_device_registry_template ON device_registry(template_id)
    WHERE template_id IS NOT NULL;

CREATE INDEX idx_device_registry_parent ON device_registry(tenant_id, parent_device_id)
    WHERE parent_device_id IS NOT NULL;
```

### Comments

```sql
COMMENT ON COLUMN device_registry.template_id IS 'FK to device_templates defining this device type. NULL during migration period — new code should always set this.';
COMMENT ON COLUMN device_registry.parent_device_id IS 'Parent gateway device_id for peripheral/child devices. NULL for standalone devices and gateways.';
```

### Note on backward compatibility

The existing `device_type` TEXT column is kept for backward compatibility. New code should read `template_id` and fall back to `device_type` during the migration period. Phase 173 will handle the final cleanup.

## Verification

```sql
-- Columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'device_registry'
AND column_name IN ('template_id', 'parent_device_id');

-- Trigger exists
SELECT tgname FROM pg_trigger WHERE tgrelid = 'device_registry'::regclass AND tgname = 'trg_validate_parent_device';

-- Indexes exist
SELECT indexname FROM pg_indexes WHERE tablename = 'device_registry' AND indexname LIKE '%template%' OR indexname LIKE '%parent%';
```
