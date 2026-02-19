-- Migration 101: Create device_health_telemetry hypertable
-- Platform-collected device diagnostics. Separate from customer sensor telemetry.
-- Always collected, not optional, not a sensor, not billed.

CREATE TABLE IF NOT EXISTS device_health_telemetry (
    time                TIMESTAMPTZ NOT NULL,
    tenant_id           TEXT NOT NULL,
    device_id           TEXT NOT NULL,

    -- Radio / Signal
    rssi                SMALLINT,               -- Received Signal Strength Indicator (dBm, typically -120 to 0)
    rsrp                SMALLINT,               -- Reference Signal Received Power (dBm, LTE)
    rsrq                SMALLINT,               -- Reference Signal Received Quality (dB, LTE)
    sinr                SMALLINT,               -- Signal-to-Interference-plus-Noise Ratio (dB)
    signal_quality      SMALLINT,               -- Normalized 0-100 signal quality score
    network_type        TEXT,                    -- "2G", "3G", "4G", "5G", "LTE-M", "NB-IoT"
    cell_id             TEXT,                    -- Serving cell ID
    mcc_mnc             TEXT,                    -- Mobile Country Code + Mobile Network Code

    -- Power
    battery_pct         SMALLINT,               -- Battery level 0-100 (NULL if line-powered)
    battery_voltage     NUMERIC(4,2),           -- Battery voltage in V
    power_source        TEXT,                    -- "battery", "line", "solar", "poe"
    charging            BOOLEAN,                -- Currently charging?

    -- Device internals
    cpu_temp_c          NUMERIC(5,1),           -- Internal CPU/SoC temperature (°C)
    memory_used_pct     SMALLINT,               -- RAM usage 0-100
    storage_used_pct    SMALLINT,               -- Flash/disk usage 0-100
    uptime_seconds      INT,                    -- Seconds since last reboot
    reboot_count        INT,                    -- Total reboot counter (monotonic)
    error_count         INT,                    -- Error/fault counter since last report

    -- Network / Data
    data_tx_bytes       BIGINT,                 -- Bytes transmitted since last report
    data_rx_bytes       BIGINT,                 -- Bytes received since last report
    data_session_bytes  BIGINT,                 -- Total bytes in current data session

    -- Location (device-reported GPS)
    gps_lat             DOUBLE PRECISION,
    gps_lon             DOUBLE PRECISION,
    gps_accuracy_m      NUMERIC(6,1),           -- GPS accuracy in meters
    gps_fix             BOOLEAN,                -- Has GPS fix?

    -- Extensible
    extra               JSONB DEFAULT '{}',     -- Additional platform metrics not yet in fixed columns

    CONSTRAINT device_health_telemetry_nn
        CHECK (tenant_id IS NOT NULL AND device_id IS NOT NULL)
);

-- Convert to TimescaleDB hypertable with 1-day chunks (matches telemetry table)
SELECT create_hypertable(
    'device_health_telemetry',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_dht_tenant_device_time
    ON device_health_telemetry(tenant_id, device_id, time DESC);

CREATE INDEX idx_dht_tenant_time
    ON device_health_telemetry(tenant_id, time DESC);

CREATE INDEX idx_dht_battery_low
    ON device_health_telemetry(tenant_id, battery_pct, time DESC)
    WHERE battery_pct IS NOT NULL AND battery_pct < 20;

CREATE INDEX idx_dht_signal_poor
    ON device_health_telemetry(tenant_id, signal_quality, time DESC)
    WHERE signal_quality IS NOT NULL AND signal_quality < 30;

-- RLS
ALTER TABLE device_health_telemetry ENABLE ROW LEVEL SECURITY;

CREATE POLICY dht_tenant_isolation ON device_health_telemetry
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY dht_operator_read ON device_health_telemetry
    FOR SELECT
    USING (current_setting('app.role', true) = 'operator');

CREATE POLICY dht_service ON device_health_telemetry
    USING (current_setting('app.role', true) = 'iot_service')
    WITH CHECK (current_setting('app.role', true) = 'iot_service');

-- Batch insert function (mirrors telemetry batch insert pattern)
CREATE OR REPLACE FUNCTION insert_device_health_batch(p_rows JSONB)
RETURNS INTEGER AS $$
DECLARE
    row_count INTEGER := 0;
    row_data  JSONB;
BEGIN
    FOR row_data IN SELECT * FROM jsonb_array_elements(p_rows)
    LOOP
        INSERT INTO device_health_telemetry (
            time, tenant_id, device_id,
            rssi, rsrp, rsrq, sinr, signal_quality, network_type, cell_id, mcc_mnc,
            battery_pct, battery_voltage, power_source, charging,
            cpu_temp_c, memory_used_pct, storage_used_pct, uptime_seconds, reboot_count, error_count,
            data_tx_bytes, data_rx_bytes, data_session_bytes,
            gps_lat, gps_lon, gps_accuracy_m, gps_fix,
            extra
        ) VALUES (
            COALESCE((row_data->>'time')::TIMESTAMPTZ, now()),
            row_data->>'tenant_id',
            row_data->>'device_id',
            (row_data->>'rssi')::SMALLINT,
            (row_data->>'rsrp')::SMALLINT,
            (row_data->>'rsrq')::SMALLINT,
            (row_data->>'sinr')::SMALLINT,
            (row_data->>'signal_quality')::SMALLINT,
            row_data->>'network_type',
            row_data->>'cell_id',
            row_data->>'mcc_mnc',
            (row_data->>'battery_pct')::SMALLINT,
            (row_data->>'battery_voltage')::NUMERIC,
            row_data->>'power_source',
            (row_data->>'charging')::BOOLEAN,
            (row_data->>'cpu_temp_c')::NUMERIC,
            (row_data->>'memory_used_pct')::SMALLINT,
            (row_data->>'storage_used_pct')::SMALLINT,
            (row_data->>'uptime_seconds')::INT,
            (row_data->>'reboot_count')::INT,
            (row_data->>'error_count')::INT,
            (row_data->>'data_tx_bytes')::BIGINT,
            (row_data->>'data_rx_bytes')::BIGINT,
            (row_data->>'data_session_bytes')::BIGINT,
            (row_data->>'gps_lat')::DOUBLE PRECISION,
            (row_data->>'gps_lon')::DOUBLE PRECISION,
            (row_data->>'gps_accuracy_m')::NUMERIC,
            (row_data->>'gps_fix')::BOOLEAN,
            COALESCE(row_data->'extra', '{}')
        );
        row_count := row_count + 1;
    END LOOP;
    RETURN row_count;
END;
$$ LANGUAGE plpgsql;

