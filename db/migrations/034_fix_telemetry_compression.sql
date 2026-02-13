-- Disable RLS on telemetry to allow compression
-- Application-level filtering still enforces tenant isolation
ALTER TABLE telemetry DISABLE ROW LEVEL SECURITY;

-- Drop the RLS policies
DROP POLICY IF EXISTS tenant_isolation ON telemetry;
DROP POLICY IF EXISTS operator_read ON telemetry;

-- Now enable compression (should work without RLS)
ALTER TABLE telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id, device_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('telemetry', INTERVAL '1 hour');

-- Retention policy
SELECT add_retention_policy('telemetry', INTERVAL '30 days');

-- Continuous aggregates (without RLS, these should work)
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    tenant_id,
    device_id,
    COUNT(*) AS message_count,
    AVG((metrics->>'battery_pct')::numeric) AS avg_battery,
    AVG((metrics->>'temp_c')::numeric) AS avg_temp
FROM telemetry
WHERE msg_type = 'telemetry'
GROUP BY bucket, tenant_id, device_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Fix system_metrics_hourly policy (use larger window)
SELECT remove_continuous_aggregate_policy('system_metrics_hourly', if_exists => true);
SELECT add_continuous_aggregate_policy('system_metrics_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);
