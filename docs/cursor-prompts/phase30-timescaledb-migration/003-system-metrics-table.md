# Phase 30.3: Create System Metrics Hypertable

## Task

Create a hypertable for system/operator dashboard metrics (replaces the InfluxDB system_metrics database).

---

## Create Migration

**File:** `db/migrations/022_system_metrics_hypertable.sql`

```sql
-- System metrics hypertable for operator dashboard
-- Stores service health, throughput, capacity metrics

CREATE TABLE IF NOT EXISTS system_metrics (
    time        TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    service     TEXT,                    -- ingest, evaluator, dispatcher, delivery, postgres
    tags        JSONB DEFAULT '{}',      -- Additional dimensions
    value       DOUBLE PRECISION NOT NULL,

    CONSTRAINT system_metrics_not_null CHECK (metric_name IS NOT NULL)
);

-- Convert to hypertable with smaller chunks (1 hour for frequent writes)
SELECT create_hypertable(
    'system_metrics',
    'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Primary query pattern: specific metric over time
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time
    ON system_metrics (metric_name, time DESC);

-- Query by service
CREATE INDEX IF NOT EXISTS idx_system_metrics_service_time
    ON system_metrics (service, time DESC)
    WHERE service IS NOT NULL;

-- Composite for dashboard queries
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_service_time
    ON system_metrics (metric_name, service, time DESC);

-----------------------------------------------------------
-- No RLS needed - operators only access this table
-----------------------------------------------------------

-- Grant to operator role only
GRANT SELECT, INSERT ON system_metrics TO pulse_operator;
GRANT SELECT ON system_metrics TO pulse_app;  -- For dashboard API

-----------------------------------------------------------
-- Helper views for common queries
-----------------------------------------------------------

-- Latest value for each metric
CREATE OR REPLACE VIEW system_metrics_latest AS
SELECT DISTINCT ON (metric_name, service)
    time,
    metric_name,
    service,
    value,
    tags
FROM system_metrics
ORDER BY metric_name, service, time DESC;

-- Metrics from last 5 minutes grouped by service
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

-----------------------------------------------------------
-- Verify setup
-----------------------------------------------------------

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
```

---

## Apply Migration

```bash
cd /home/opsconductor/simcloud/compose
cat ../db/migrations/022_system_metrics_hypertable.sql | docker compose exec -T postgres psql -U iot -d iotcloud
```

---

## Verification

```bash
# Check hypertable
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT hypertable_name FROM timescaledb_information.hypertables
WHERE hypertable_name = 'system_metrics';
"

# Test insert
docker compose exec postgres psql -U iot -d iotcloud -c "
INSERT INTO system_metrics (time, metric_name, service, value)
VALUES
    (now(), 'messages_received', 'ingest', 12345),
    (now(), 'queue_depth', 'ingest', 0),
    (now(), 'connections', 'postgres', 15);

SELECT * FROM system_metrics_latest;

DELETE FROM system_metrics WHERE metric_name IN ('messages_received', 'queue_depth', 'connections');
"
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `db/migrations/022_system_metrics_hypertable.sql` |
