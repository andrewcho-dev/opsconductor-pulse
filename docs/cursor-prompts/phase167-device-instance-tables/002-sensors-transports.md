# Task 2: Device Sensors + Device Transports (Migration 112)

## Create file: `db/migrations/112_device_sensors_transports.sql`

This migration creates two new tables and copies data from the legacy tables.

---

## Table 1: `device_sensors`

Restructured sensor model that links to templates and modules.

```sql
CREATE TABLE IF NOT EXISTS device_sensors (
    id                  SERIAL PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    device_id           TEXT NOT NULL,
    metric_key          TEXT NOT NULL,
    display_name        TEXT NOT NULL,
    template_metric_id  INT REFERENCES template_metrics(id) ON DELETE SET NULL,
    device_module_id    INT REFERENCES device_modules(id) ON DELETE SET NULL,
    unit                TEXT,
    min_range           NUMERIC,
    max_range           NUMERIC,
    precision_digits    INT NOT NULL DEFAULT 2,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'error')),
    source              TEXT NOT NULL DEFAULT 'required'
                        CHECK (source IN ('required', 'optional', 'unmodeled')),
    last_value          NUMERIC,
    last_value_text     TEXT,
    last_seen_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, device_id, metric_key),

    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry(tenant_id, device_id)
        ON DELETE CASCADE
);
```

### Indexes

```sql
CREATE INDEX idx_device_sensors_tenant_device ON device_sensors(tenant_id, device_id);
CREATE INDEX idx_device_sensors_template_metric ON device_sensors(template_metric_id);
CREATE INDEX idx_device_sensors_module ON device_sensors(device_module_id);
CREATE INDEX idx_device_sensors_status ON device_sensors(tenant_id, status);
CREATE INDEX idx_device_sensors_source ON device_sensors(tenant_id, source);
```

### RLS

```sql
ALTER TABLE device_sensors ENABLE ROW LEVEL SECURITY;

CREATE POLICY device_sensors_tenant_isolation ON device_sensors
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY device_sensors_operator_read ON device_sensors
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

CREATE POLICY device_sensors_service ON device_sensors
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants & trigger

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON device_sensors TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE device_sensors_id_seq TO pulse_app;

CREATE TRIGGER trg_device_sensors_updated_at
    BEFORE UPDATE ON device_sensors
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();
```

### Data migration from `sensors` → `device_sensors`

```sql
INSERT INTO device_sensors (tenant_id, device_id, metric_key, display_name, unit, min_range, max_range, precision_digits, status, source, last_value, last_seen_at, created_at, updated_at)
SELECT
    s.tenant_id,
    s.device_id,
    s.metric_name,                                    -- metric_name → metric_key
    COALESCE(s.label, s.metric_name),                 -- label → display_name (fallback to metric_name)
    s.unit,
    s.min_range,
    s.max_range,
    COALESCE(s.precision_digits, 2),
    CASE s.status
        WHEN 'disabled' THEN 'inactive'
        WHEN 'stale' THEN 'inactive'
        ELSE s.status                                  -- active, error map directly
    END,
    'unmodeled',                                       -- All migrated sensors are unmodeled
    s.last_value,
    s.last_seen_at,
    s.created_at,
    s.updated_at
FROM sensors s
ON CONFLICT (tenant_id, device_id, metric_key) DO NOTHING;
```

---

## Table 2: `device_transports`

Separates ingestion protocol from physical connectivity.

```sql
CREATE TABLE IF NOT EXISTS device_transports (
    id                      SERIAL PRIMARY KEY,
    tenant_id               TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    device_id               TEXT NOT NULL,
    ingestion_protocol      TEXT NOT NULL
                            CHECK (ingestion_protocol IN (
                                'mqtt_direct', 'http_api', 'lorawan', 'gateway_proxy', 'modbus_rtu'
                            )),
    physical_connectivity   TEXT
                            CHECK (physical_connectivity IN (
                                'cellular', 'ethernet', 'wifi', 'satellite', 'lora', 'other'
                            )),
    protocol_config         JSONB NOT NULL DEFAULT '{}',
    connectivity_config     JSONB NOT NULL DEFAULT '{}',
    carrier_integration_id  INT REFERENCES carrier_integrations(id) ON DELETE SET NULL,
    is_primary              BOOLEAN NOT NULL DEFAULT true,
    status                  TEXT NOT NULL DEFAULT 'active'
                            CHECK (status IN ('active', 'inactive', 'failover')),
    last_connected_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (tenant_id, device_id, ingestion_protocol),

    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry(tenant_id, device_id)
        ON DELETE CASCADE
);
```

### Indexes

```sql
CREATE INDEX idx_device_transports_tenant_device ON device_transports(tenant_id, device_id);
CREATE INDEX idx_device_transports_protocol ON device_transports(tenant_id, ingestion_protocol);
CREATE INDEX idx_device_transports_carrier ON device_transports(carrier_integration_id)
    WHERE carrier_integration_id IS NOT NULL;
```

### RLS

```sql
ALTER TABLE device_transports ENABLE ROW LEVEL SECURITY;

CREATE POLICY device_transports_tenant_isolation ON device_transports
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY device_transports_operator_read ON device_transports
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

CREATE POLICY device_transports_service ON device_transports
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');
```

### Grants & trigger

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON device_transports TO pulse_app;
GRANT USAGE, SELECT ON SEQUENCE device_transports_id_seq TO pulse_app;

CREATE TRIGGER trg_device_transports_updated_at
    BEFORE UPDATE ON device_transports
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();
```

### Data migration from `device_connections` → `device_transports`

```sql
INSERT INTO device_transports (
    tenant_id, device_id, ingestion_protocol, physical_connectivity,
    protocol_config, connectivity_config, carrier_integration_id,
    is_primary, status, last_connected_at, created_at, updated_at
)
SELECT
    dc.tenant_id,
    dc.device_id,
    'mqtt_direct',                                     -- Default: all existing devices use MQTT
    dc.connection_type,                                -- connection_type → physical_connectivity
    '{}'::jsonb,                                       -- protocol_config: empty for now
    jsonb_strip_nulls(jsonb_build_object(
        'carrier_name',      dc.carrier_name,
        'carrier_account_id', dc.carrier_account_id,
        'plan_name',         dc.plan_name,
        'apn',               dc.apn,
        'sim_iccid',         dc.sim_iccid,
        'sim_status',        dc.sim_status,
        'data_limit_mb',     dc.data_limit_mb,
        'data_used_mb',      dc.data_used_mb,
        'ip_address',        dc.ip_address::text,
        'msisdn',            dc.msisdn,
        'network_status',    dc.network_status,
        'carrier_device_id', dc.carrier_device_id
    )),
    dc.carrier_integration_id,
    true,                                               -- All existing connections are primary
    CASE dc.network_status
        WHEN 'connected' THEN 'active'
        WHEN 'disconnected' THEN 'inactive'
        WHEN 'suspended' THEN 'inactive'
        ELSE 'active'
    END,
    dc.last_network_attach,                            -- last_network_attach → last_connected_at
    dc.created_at,
    dc.updated_at
FROM device_connections dc
ON CONFLICT (tenant_id, device_id, ingestion_protocol) DO NOTHING;
```

### Comments

```sql
COMMENT ON TABLE device_sensors IS 'Active measurement points on a device — linked to template metrics and modules';
COMMENT ON COLUMN device_sensors.source IS 'required = auto-created from template, optional = manually added from template, unmodeled = discovered or migrated';
COMMENT ON COLUMN device_sensors.last_value_text IS 'For string/enum metric types where numeric last_value is insufficient';

COMMENT ON TABLE device_transports IS 'Ingestion protocol and physical connectivity configuration per device';
COMMENT ON COLUMN device_transports.ingestion_protocol IS 'How data reaches the platform: mqtt_direct, http_api, lorawan, gateway_proxy, modbus_rtu';
COMMENT ON COLUMN device_transports.physical_connectivity IS 'Physical link type: cellular, ethernet, wifi, satellite, lora, other';
COMMENT ON COLUMN device_transports.protocol_config IS 'Protocol-specific config: MQTT {client_id, topic_prefix}; HTTP {api_key}; LoRaWAN {dev_eui, app_key}';
COMMENT ON COLUMN device_transports.connectivity_config IS 'Connectivity-specific config: Cellular {carrier, apn, iccid, imei}; WiFi {ssid}';
```

## Verification

```sql
-- Tables exist
SELECT tablename FROM pg_tables WHERE tablename IN ('device_sensors', 'device_transports');

-- Data migrated
SELECT 'sensors' AS source, count(*) FROM sensors
UNION ALL
SELECT 'device_sensors', count(*) FROM device_sensors;

SELECT 'device_connections' AS source, count(*) FROM device_connections
UNION ALL
SELECT 'device_transports', count(*) FROM device_transports;
```
