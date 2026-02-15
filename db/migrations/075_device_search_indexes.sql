-- Migration 075: Indexes for fleet search
-- Enables fast server-side filtering on the device list.

-- Device tag filtering (used by customer/devices tags filters).
CREATE INDEX IF NOT EXISTS idx_device_tags_tenant_tag
  ON device_tags (tenant_id, tag);

-- Full-text search on device registry identity fields.
ALTER TABLE device_registry
  ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
      to_tsvector(
        'english',
        coalesce(device_id, '') || ' ' || coalesce(model, '') || ' ' || coalesce(serial_number, '')
      )
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_device_registry_search_vector
  ON device_registry USING GIN (search_vector);

-- Equality filters used by list_devices.
CREATE INDEX IF NOT EXISTS idx_device_registry_tenant_site_id
  ON device_registry (tenant_id, site_id)
  WHERE decommissioned_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_device_state_tenant_status
  ON device_state (tenant_id, status);

-- Verify
SELECT indexname FROM pg_indexes
WHERE tablename IN ('device_registry', 'device_tags', 'device_state')
ORDER BY indexname;
