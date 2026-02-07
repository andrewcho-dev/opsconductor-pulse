-- System metrics hypertable for operator dashboard
-- Stores service health, throughput, capacity metrics

CREATE TABLE IF NOT EXISTS system_metrics (
    time        TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    service     TEXT,
    tags        JSONB DEFAULT '{}',
    value       DOUBLE PRECISION NOT NULL,

    CONSTRAINT system_metrics_not_null CHECK (metric_name IS NOT NULL)
);

SELECT create_hypertable(
    'system_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time
    ON system_metrics (metric_name, time DESC);

CREATE INDEX IF NOT EXISTS idx_system_metrics_service_time
    ON system_metrics (service, time DESC)
    WHERE service IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_system_metrics_name_service_time
    ON system_metrics (metric_name, service, time DESC);

GRANT SELECT, INSERT ON system_metrics TO pulse_operator;
GRANT SELECT ON system_metrics TO pulse_app;

CREATE OR REPLACE VIEW system_metrics_latest AS
SELECT DISTINCT ON (metric_name, service)
    time,
    metric_name,
    service,
    value,
    tags
FROM system_metrics
ORDER BY metric_name, service, time DESC;

CREATE OR REPLACE VIEW system_metrics_recent AS
SELECT
    metric_name,
    service,
    AVG(value) as avg_value,
    MAX(value) as max_value,
    MIN(value) as min_value,
    COUNT(*) as sample_count
FROM system_metrics
WHERE time > now() - INTERVAL '5 minutes'
GROUP BY metric_name, service;

DO $$
DECLARE
    hypertable_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'system_metrics'
    ) INTO hypertable_exists;

    IF NOT hypertable_exists THEN
        RAISE EXCEPTION 'system_metrics hypertable was not created';
    END IF;

    RAISE NOTICE 'system_metrics hypertable created successfully';
END $$;
