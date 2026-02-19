# Task 2: Deprecate Legacy Tables (Migration 115)

## Create file: `db/migrations/115_deprecate_legacy_tables.sql`

Rename legacy tables that are fully replaced by the new template model. This makes them invisible to the application while preserving the data for rollback safety.

### Rename deprecated tables

```sql
-- normalized_metrics and metric_mappings are fully replaced by template_metrics
ALTER TABLE IF EXISTS normalized_metrics RENAME TO _deprecated_normalized_metrics;
ALTER TABLE IF EXISTS metric_mappings RENAME TO _deprecated_metric_mappings;

-- Add comments explaining deprecation
COMMENT ON TABLE _deprecated_normalized_metrics IS 'DEPRECATED in Phase 173. Replaced by template_metrics. Data preserved for rollback. Safe to drop after 2026-04-01.';
COMMENT ON TABLE _deprecated_metric_mappings IS 'DEPRECATED in Phase 173. Replaced by template_metrics + device_modules.metric_key_map. Data preserved for rollback. Safe to drop after 2026-04-01.';
```

### Keep sensors and device_connections temporarily

These tables may still be referenced by some code paths. Rename them but keep the original names as views for backward compatibility:

```sql
-- Rename the original tables
ALTER TABLE IF EXISTS sensors RENAME TO _deprecated_sensors;
ALTER TABLE IF EXISTS device_connections RENAME TO _deprecated_device_connections;

-- Create views that point to the new tables (backward compatibility)
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
    '{}' ::jsonb AS metadata,
    created_at,
    updated_at
FROM device_sensors;

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
    '{}' ::jsonb AS metadata,
    created_at,
    updated_at,
    (connectivity_config->>'carrier_device_id')::text AS carrier_device_id,
    carrier_integration_id
FROM device_transports;

-- Grant read access on views
GRANT SELECT ON sensors TO pulse_app;
GRANT SELECT ON device_connections TO pulse_app;
```

### Add comments on deprecated tables

```sql
COMMENT ON TABLE _deprecated_sensors IS 'DEPRECATED in Phase 173. Replaced by device_sensors. Backward-compat view "sensors" created. Data preserved for rollback. Safe to drop after 2026-04-01.';
COMMENT ON TABLE _deprecated_device_connections IS 'DEPRECATED in Phase 173. Replaced by device_transports. Backward-compat view "device_connections" created. Data preserved for rollback. Safe to drop after 2026-04-01.';
```

### Handle metric_catalog

Keep `metric_catalog` for now — it may be referenced by the (now deprecated) MetricsPage. Add a deprecation comment:

```sql
COMMENT ON TABLE metric_catalog IS 'DEPRECATED in Phase 173. Replaced by template_metrics. Still accessible for reference. Will be renamed to _deprecated_metric_catalog in a future phase.';
```

## Verification

```sql
-- Deprecated tables renamed
SELECT tablename FROM pg_tables WHERE tablename LIKE '_deprecated_%';
-- Should show: _deprecated_normalized_metrics, _deprecated_metric_mappings, _deprecated_sensors, _deprecated_device_connections

-- Backward-compat views work
SELECT count(*) FROM sensors;  -- Should work via view
SELECT count(*) FROM device_connections;  -- Should work via view

-- New tables still accessible
SELECT count(*) FROM device_sensors;
SELECT count(*) FROM device_transports;
```
