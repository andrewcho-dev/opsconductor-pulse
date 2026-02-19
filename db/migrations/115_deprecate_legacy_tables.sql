-- Migration 115: Deprecate legacy tables in favor of the template model
-- - Renames legacy tables with a _deprecated_ prefix for rollback safety
-- - Creates backward-compat views for sensors and device_connections

BEGIN;

-- ============================================================
-- Fully replaced tables
-- ============================================================

ALTER TABLE IF EXISTS normalized_metrics RENAME TO _deprecated_normalized_metrics;
ALTER TABLE IF EXISTS metric_mappings RENAME TO _deprecated_metric_mappings;

COMMENT ON TABLE _deprecated_normalized_metrics IS
    'DEPRECATED in Phase 173. Replaced by template_metrics. Data preserved for rollback. Safe to drop after 2026-04-01.';
COMMENT ON TABLE _deprecated_metric_mappings IS
    'DEPRECATED in Phase 173. Replaced by template_metrics + device_modules.metric_key_map. Data preserved for rollback. Safe to drop after 2026-04-01.';

-- ============================================================
-- Sensors: keep compatibility view
-- ============================================================

DO $$
BEGIN
    -- Only rename if 'sensors' is still a table (idempotent reruns after view creation).
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'sensors'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE sensors RENAME TO _deprecated_sensors;
    END IF;
END $$;

CREATE OR REPLACE VIEW sensors AS
SELECT
    id AS sensor_id,
    tenant_id,
    device_id,
    metric_key AS metric_name,
    'unknown' AS sensor_type,
    display_name AS label,
    unit,
    min_range,
    max_range,
    precision_digits,
    status,
    (source = 'unmodeled') AS auto_discovered,
    last_value,
    last_seen_at,
    '{}'::jsonb AS metadata,
    created_at,
    updated_at
FROM device_sensors;

GRANT SELECT ON sensors TO pulse_app;

COMMENT ON TABLE _deprecated_sensors IS
    'DEPRECATED in Phase 173. Replaced by device_sensors. Backward-compat view "sensors" created. Data preserved for rollback. Safe to drop after 2026-04-01.';

-- ============================================================
-- Device connections: keep compatibility view
-- ============================================================

DO $$
BEGIN
    -- Only rename if 'device_connections' is still a table (idempotent reruns after view creation).
    IF EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = 'device_connections'
          AND c.relkind = 'r'
    ) THEN
        ALTER TABLE device_connections RENAME TO _deprecated_device_connections;
    END IF;
END $$;

CREATE OR REPLACE VIEW device_connections AS
SELECT
    id,
    tenant_id,
    device_id,
    physical_connectivity AS connection_type,
    (connectivity_config->>'carrier_name')::text AS carrier_name,
    (connectivity_config->>'carrier_account_id')::text AS carrier_account_id,
    (connectivity_config->>'plan_name')::text AS plan_name,
    (connectivity_config->>'apn')::text AS apn,
    (connectivity_config->>'sim_iccid')::text AS sim_iccid,
    (connectivity_config->>'sim_status')::text AS sim_status,
    (connectivity_config->>'data_limit_mb')::int AS data_limit_mb,
    1 AS billing_cycle_start,
    (connectivity_config->>'data_used_mb')::numeric AS data_used_mb,
    NULL::timestamptz AS data_used_updated_at,
    (connectivity_config->>'ip_address')::inet AS ip_address,
    (connectivity_config->>'msisdn')::text AS msisdn,
    (connectivity_config->>'network_status')::text AS network_status,
    last_connected_at AS last_network_attach,
    NULL::timestamptz AS last_network_detach,
    '{}'::jsonb AS metadata,
    created_at,
    updated_at,
    (connectivity_config->>'carrier_device_id')::text AS carrier_device_id,
    carrier_integration_id
FROM device_transports;

GRANT SELECT ON device_connections TO pulse_app;

COMMENT ON TABLE _deprecated_device_connections IS
    'DEPRECATED in Phase 173. Replaced by device_transports. Backward-compat view "device_connections" created. Data preserved for rollback. Safe to drop after 2026-04-01.';

-- ============================================================
-- metric_catalog: keep table for reference (MetricsPage is deprecated)
-- ============================================================

COMMENT ON TABLE metric_catalog IS
    'DEPRECATED in Phase 173. Replaced by template_metrics. Still accessible for reference. Will be renamed to _deprecated_metric_catalog in a future phase.';

COMMIT;

