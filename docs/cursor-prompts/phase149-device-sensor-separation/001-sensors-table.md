# Task 001 — Create `sensors` Table

## Migration File

Create `db/migrations/099_sensors_table.sql`

## SQL

```sql
-- Migration 099: Create sensors table
-- Sensors are measurement points associated with a device/gateway.
-- They are auto-discovered from telemetry metric keys and track
-- metadata about each measurement the device reports.

CREATE TABLE IF NOT EXISTS sensors (
    sensor_id       SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    device_id       TEXT NOT NULL,
    metric_name     TEXT NOT NULL,          -- Key in telemetry JSONB (e.g., "temperature", "humidity")
    sensor_type     TEXT NOT NULL DEFAULT 'unknown',  -- temperature, humidity, pressure, vibration, flow, level, power, digital, analog, etc.
    label           TEXT,                   -- User-friendly display name (e.g., "Server Room Temp Sensor")
    unit            TEXT,                   -- Measurement unit (e.g., "°C", "%", "hPa", "m/s²")
    min_range       NUMERIC,               -- Expected minimum value
    max_range       NUMERIC,               -- Expected maximum value
    precision_digits INT DEFAULT 1,        -- Decimal places for display
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'disabled', 'stale', 'error')),
    auto_discovered BOOLEAN NOT NULL DEFAULT true,  -- true if created by ingestor, false if manually added
    last_value      NUMERIC,               -- Cache of most recent reading
    last_seen_at    TIMESTAMPTZ,           -- When the last reading arrived
    metadata        JSONB NOT NULL DEFAULT '{}',  -- Extensible attributes
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A device can only have one sensor per metric_name
    UNIQUE (tenant_id, device_id, metric_name),

    -- FK to device_registry (composite key)
    FOREIGN KEY (tenant_id, device_id)
        REFERENCES device_registry(tenant_id, device_id)
        ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_sensors_tenant_device ON sensors(tenant_id, device_id);
CREATE INDEX idx_sensors_tenant_type ON sensors(tenant_id, sensor_type);
CREATE INDEX idx_sensors_tenant_status ON sensors(tenant_id, status);
CREATE INDEX idx_sensors_device_metric ON sensors(tenant_id, device_id, metric_name);

-- RLS
ALTER TABLE sensors ENABLE ROW LEVEL SECURITY;

CREATE POLICY sensors_tenant_isolation ON sensors
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY sensors_operator_read ON sensors
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

CREATE POLICY sensors_service ON sensors
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_sensors_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sensors_updated_at
    BEFORE UPDATE ON sensors
    FOR EACH ROW
    EXECUTE FUNCTION update_sensors_timestamp();
```

## Notes

- `metric_name` maps to the keys in the telemetry JSONB `metrics` column (e.g., `{"temperature": 22.5}` → metric_name = `"temperature"`)
- `sensor_type` is a classification (temperature, humidity, etc.) — separate from `metric_name` because a device might have `temp_inlet` and `temp_outlet` both of type `temperature`
- `last_value` and `last_seen_at` are denormalized caches updated by the ingestor for quick display without querying telemetry
- `auto_discovered` distinguishes sensors created by the ingestor from those manually declared by the user
- The UNIQUE constraint on `(tenant_id, device_id, metric_name)` ensures one sensor record per metric per device
- RLS follows the same pattern as `device_registry`

## Verification

```bash
cd db && python3 migrations/run_migrations.py
# OR manually:
psql -d iot -f db/migrations/099_sensors_table.sql
# Then verify:
psql -d iot -c "\d sensors"
```
