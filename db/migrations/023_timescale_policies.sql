-- ============================================================
-- COMPRESSION POLICIES
-- Automatically compress old chunks to save storage (90%+)
-- ============================================================

-- Telemetry compression/retention is intentionally handled later in
-- `034_fix_telemetry_compression.sql` because `021_telemetry_hypertable.sql`
-- enables RLS on `telemetry`, and Timescale cannot enable columnstore
-- compression on an RLS-protected table.

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

-- Telemetry retention is also handled in `034_fix_telemetry_compression.sql`.

-- System metrics: keep for 7 days (dashboard only needs recent data)
SELECT add_retention_policy('system_metrics', INTERVAL '7 days');


-- ============================================================
-- CONTINUOUS AGGREGATES (Optional)
-- Pre-computed rollups for fast dashboard queries
-- ============================================================

-- Continuous aggregates based on telemetry are also created in
-- `034_fix_telemetry_compression.sql` after adjusting RLS.

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
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);


-- ============================================================
-- RLS ON CONTINUOUS AGGREGATES
-- ============================================================

-- Telemetry continuous aggregate setup moved to `034_fix_telemetry_compression.sql`.


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
