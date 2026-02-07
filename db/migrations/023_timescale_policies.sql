-- ============================================================
-- COMPRESSION POLICIES
-- Automatically compress old chunks to save storage (90%+)
-- ============================================================

-- Telemetry: compress chunks older than 1 hour
-- This keeps recent data uncompressed for fast queries
ALTER TABLE telemetry SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tenant_id, device_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('telemetry', INTERVAL '1 hour');

-- System metrics: compress chunks older than 1 hour
ALTER TABLE system_metrics SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'metric_name, service',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('system_metrics', INTERVAL '1 hour');


-- ============================================================
-- RETENTION POLICIES
-- Automatically drop old data to prevent unbounded growth
-- ============================================================

-- Telemetry: keep raw data for 30 days
-- Adjust based on your needs (storage vs history trade-off)
SELECT add_retention_policy('telemetry', INTERVAL '30 days');

-- System metrics: keep for 7 days (dashboard only needs recent data)
SELECT add_retention_policy('system_metrics', INTERVAL '7 days');


-- ============================================================
-- CONTINUOUS AGGREGATES (Optional)
-- Pre-computed rollups for fast dashboard queries
-- ============================================================

-- Hourly telemetry summary per device
CREATE MATERIALIZED VIEW telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    tenant_id,
    device_id,
    COUNT(*) AS message_count,
    AVG((metrics->>'battery_pct')::numeric) AS avg_battery,
    AVG((metrics->>'temp_c')::numeric) AS avg_temp,
    AVG((metrics->>'signal_dbm')::numeric) AS avg_signal,
    MIN((metrics->>'battery_pct')::numeric) AS min_battery,
    MAX((metrics->>'temp_c')::numeric) AS max_temp
FROM telemetry
WHERE msg_type = 'telemetry'
GROUP BY bucket, tenant_id, device_id
WITH NO DATA;

-- Refresh policy: update hourly aggregates every hour
SELECT add_continuous_aggregate_policy('telemetry_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- Daily telemetry summary per tenant (for billing/reporting)
CREATE MATERIALIZED VIEW telemetry_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    tenant_id,
    COUNT(*) AS message_count,
    COUNT(DISTINCT device_id) AS device_count,
    AVG((metrics->>'battery_pct')::numeric) AS avg_battery
FROM telemetry
WHERE msg_type = 'telemetry'
GROUP BY bucket, tenant_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('telemetry_daily',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- System metrics hourly (for historical trends)
CREATE MATERIALIZED VIEW system_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    metric_name,
    service,
    AVG(value) AS avg_value,
    MAX(value) AS max_value,
    MIN(value) AS min_value
FROM system_metrics
GROUP BY bucket, metric_name, service
WITH NO DATA;

SELECT add_continuous_aggregate_policy('system_metrics_hourly',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);


-- ============================================================
-- RLS ON CONTINUOUS AGGREGATES
-- ============================================================

-- Enable RLS on the hourly view (uses same tenant_id column)
ALTER MATERIALIZED VIEW telemetry_hourly OWNER TO iot;
-- Note: RLS policies on continuous aggregates require the base table's policies


-- ============================================================
-- VERIFY POLICIES
-- ============================================================

-- Show compression settings
SELECT hypertable_name, compression_enabled
FROM timescaledb_information.hypertables;

-- Show all policies
SELECT * FROM timescaledb_information.jobs
WHERE proc_name LIKE '%policy%';

-- Show continuous aggregates
SELECT view_name, materialization_hypertable_name
FROM timescaledb_information.continuous_aggregates;
