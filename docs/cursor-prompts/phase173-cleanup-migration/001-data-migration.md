# Task 1: Data Migration — Map Existing Devices to Templates (Migration 114)

## Create file: `db/migrations/114_migrate_existing_devices.sql`

This migration maps existing devices to templates and ensures all data is in the new tables.

### Step 1: Auto-assign template_id for known devices

For devices with manufacturer+model combos matching system templates, set `template_id`:

```sql
-- Map known Lifeline devices to system templates
UPDATE device_registry dr
SET template_id = dt.id
FROM device_templates dt
WHERE dr.template_id IS NULL
  AND dt.tenant_id IS NULL  -- System templates only
  AND dt.manufacturer IS NOT NULL
  AND dr.manufacturer IS NOT NULL
  AND LOWER(dr.manufacturer) = LOWER(dt.manufacturer)
  AND dr.model IS NOT NULL
  AND LOWER(dr.model) = LOWER(dt.model);
```

Also try mapping by `device_type`:

```sql
-- Map by device_type → category for devices without manufacturer/model match
UPDATE device_registry dr
SET template_id = (
    SELECT dt.id FROM device_templates dt
    WHERE dt.tenant_id IS NULL
    AND dt.category = CASE dr.device_type
        WHEN 'gateway' THEN 'gateway'
        WHEN 'edge_device' THEN 'edge_device'
        WHEN 'standalone_sensor' THEN 'standalone_sensor'
        WHEN 'controller' THEN 'controller'
        ELSE NULL
    END
    LIMIT 1
)
WHERE dr.template_id IS NULL
  AND dr.device_type IN ('gateway', 'edge_device', 'standalone_sensor', 'controller');
```

### Step 2: Ensure all sensors are in device_sensors

Migration 112 already copied sensors → device_sensors, but run it again to catch any sensors created after that migration:

```sql
INSERT INTO device_sensors (tenant_id, device_id, metric_key, display_name, unit, min_range, max_range, precision_digits, status, source, last_value, last_seen_at, created_at, updated_at)
SELECT
    s.tenant_id,
    s.device_id,
    s.metric_name,
    COALESCE(s.label, s.metric_name),
    s.unit,
    s.min_range,
    s.max_range,
    COALESCE(s.precision_digits, 2),
    CASE s.status
        WHEN 'disabled' THEN 'inactive'
        WHEN 'stale' THEN 'inactive'
        ELSE s.status
    END,
    'unmodeled',
    s.last_value,
    s.last_seen_at,
    s.created_at,
    s.updated_at
FROM sensors s
WHERE NOT EXISTS (
    SELECT 1 FROM device_sensors ds
    WHERE ds.tenant_id = s.tenant_id AND ds.device_id = s.device_id AND ds.metric_key = s.metric_name
)
ON CONFLICT (tenant_id, device_id, metric_key) DO NOTHING;
```

### Step 3: Ensure all connections are in device_transports

Same catch-up for connections created after migration 112:

```sql
INSERT INTO device_transports (
    tenant_id, device_id, ingestion_protocol, physical_connectivity,
    protocol_config, connectivity_config, carrier_integration_id,
    is_primary, status, last_connected_at, created_at, updated_at
)
SELECT
    dc.tenant_id,
    dc.device_id,
    'mqtt_direct',
    dc.connection_type,
    '{}'::jsonb,
    jsonb_strip_nulls(jsonb_build_object(
        'carrier_name', dc.carrier_name,
        'carrier_account_id', dc.carrier_account_id,
        'plan_name', dc.plan_name,
        'apn', dc.apn,
        'sim_iccid', dc.sim_iccid,
        'sim_status', dc.sim_status,
        'data_limit_mb', dc.data_limit_mb,
        'data_used_mb', dc.data_used_mb,
        'ip_address', dc.ip_address::text,
        'msisdn', dc.msisdn,
        'network_status', dc.network_status,
        'carrier_device_id', dc.carrier_device_id
    )),
    dc.carrier_integration_id,
    true,
    CASE dc.network_status
        WHEN 'connected' THEN 'active'
        WHEN 'disconnected' THEN 'inactive'
        WHEN 'suspended' THEN 'inactive'
        ELSE 'active'
    END,
    dc.last_network_attach,
    dc.created_at,
    dc.updated_at
FROM device_connections dc
WHERE NOT EXISTS (
    SELECT 1 FROM device_transports dt
    WHERE dt.tenant_id = dc.tenant_id AND dt.device_id = dc.device_id AND dt.ingestion_protocol = 'mqtt_direct'
)
ON CONFLICT (tenant_id, device_id, ingestion_protocol) DO NOTHING;
```

### Step 4: Create required sensors for devices with templates

For devices that now have `template_id` set, create any missing required sensors:

```sql
INSERT INTO device_sensors (tenant_id, device_id, metric_key, display_name, template_metric_id, unit, min_range, max_range, precision_digits, source)
SELECT
    dr.tenant_id,
    dr.device_id,
    tm.metric_key,
    tm.display_name,
    tm.id,
    tm.unit,
    tm.min_value,
    tm.max_value,
    tm.precision_digits,
    'required'
FROM device_registry dr
JOIN template_metrics tm ON tm.template_id = dr.template_id AND tm.is_required = true
WHERE dr.template_id IS NOT NULL
ON CONFLICT (tenant_id, device_id, metric_key) DO NOTHING;
```

## Verification

```sql
-- Devices with template_id set
SELECT count(*) AS with_template, (SELECT count(*) FROM device_registry) AS total
FROM device_registry WHERE template_id IS NOT NULL;

-- All sensors migrated
SELECT
    (SELECT count(*) FROM sensors) AS legacy_sensors,
    (SELECT count(*) FROM device_sensors) AS new_sensors;

-- All connections migrated
SELECT
    (SELECT count(*) FROM device_connections) AS legacy_connections,
    (SELECT count(*) FROM device_transports) AS new_transports;

-- Required sensors created
SELECT count(*) FROM device_sensors WHERE source = 'required';
```
