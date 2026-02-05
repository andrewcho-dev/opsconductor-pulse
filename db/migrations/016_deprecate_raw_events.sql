-- Phase 12: Deprecate raw_events (telemetry moved to InfluxDB 3 Core)
-- Rename table instead of dropping for safety. Can be dropped after validation period.

ALTER TABLE IF EXISTS raw_events RENAME TO _deprecated_raw_events;

-- Drop indexes (they reference the old table name and are no longer needed)
DROP INDEX IF EXISTS raw_events_accepted_idx;
DROP INDEX IF EXISTS raw_events_device_idx;
DROP INDEX IF EXISTS raw_events_ingested_at_idx;
DROP INDEX IF EXISTS raw_events_payload_gin_idx;
DROP INDEX IF EXISTS raw_events_tenant_idx;
