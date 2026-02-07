# Phase 30.2: Create Telemetry Hypertable

## Task

Create the telemetry hypertable with proper indexes and RLS policies.

---

## Create Migration

**File:** `db/migrations/021_telemetry_hypertable.sql`

```sql
-- Telemetry hypertable for time-series IoT data
-- Replaces InfluxDB telemetry storage

CREATE TABLE IF NOT EXISTS telemetry (
    time        TIMESTAMPTZ NOT NULL,
    tenant_id   TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    site_id     TEXT,
    msg_type    TEXT NOT NULL DEFAULT 'telemetry',
    seq         BIGINT DEFAULT 0,
    metrics     JSONB NOT NULL DEFAULT '{}',

    -- No traditional PK - TimescaleDB uses time-based chunks
    CONSTRAINT telemetry_not_null CHECK (tenant_id IS NOT NULL AND device_id IS NOT NULL)
);

-- Convert to hypertable
-- chunk_time_interval: 1 day = good balance for 20K msg/sec
-- Chunks are automatically created and can be dropped/compressed independently
SELECT create_hypertable(
    'telemetry',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Primary access pattern: recent data for a specific device
CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_device_time
    ON telemetry (tenant_id, device_id, time DESC);

-- Secondary: all devices for a tenant (dashboard overview)
CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_time
    ON telemetry (tenant_id, time DESC);

-- For site-based filtering
CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_site_time
    ON telemetry (tenant_id, site_id, time DESC)
    WHERE site_id IS NOT NULL;

-- Message type filtering (telemetry vs heartbeat vs event)
CREATE INDEX IF NOT EXISTS idx_telemetry_msgtype
    ON telemetry (tenant_id, msg_type, time DESC);

-----------------------------------------------------------
-- Row Level Security (same pattern as other tables)
-----------------------------------------------------------

ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

-- Tenant users can only see their own data
CREATE POLICY tenant_isolation ON telemetry
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Operators can see all data (read-only)
CREATE POLICY operator_read ON telemetry
    FOR SELECT
    USING (current_setting('app.role', true) IN ('operator', 'operator_admin'));

-- Grant permissions
GRANT SELECT, INSERT ON telemetry TO pulse_app;
GRANT SELECT ON telemetry TO pulse_operator;

-----------------------------------------------------------
-- Helper function for batch inserts
-----------------------------------------------------------

CREATE OR REPLACE FUNCTION insert_telemetry_batch(
    p_rows JSONB
) RETURNS INTEGER AS $$
DECLARE
    inserted_count INTEGER;
BEGIN
    INSERT INTO telemetry (time, tenant_id, device_id, site_id, msg_type, seq, metrics)
    SELECT
        (r->>'time')::TIMESTAMPTZ,
        r->>'tenant_id',
        r->>'device_id',
        r->>'site_id',
        COALESCE(r->>'msg_type', 'telemetry'),
        COALESCE((r->>'seq')::BIGINT, 0),
        COALESCE(r->'metrics', '{}'::JSONB)
    FROM jsonb_array_elements(p_rows) AS r;

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

-----------------------------------------------------------
-- Verify setup
-----------------------------------------------------------

DO $$
DECLARE
    hypertable_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'telemetry'
    ) INTO hypertable_exists;

    IF NOT hypertable_exists THEN
        RAISE EXCEPTION 'Telemetry hypertable was not created';
    END IF;

    RAISE NOTICE 'Telemetry hypertable created successfully';
END $$;
```

---

## Apply Migration

```bash
cd /home/opsconductor/simcloud/compose
docker compose exec postgres psql -U iot -d iotcloud -f /docker-entrypoint-initdb.d/migrations/021_telemetry_hypertable.sql
```

Or if migrations aren't mounted:
```bash
cat ../db/migrations/021_telemetry_hypertable.sql | docker compose exec -T postgres psql -U iot -d iotcloud
```

---

## Verification

```bash
# Check hypertable exists
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT hypertable_name, num_dimensions
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'telemetry';
"

# Check indexes
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT indexname FROM pg_indexes WHERE tablename = 'telemetry';
"

# Check RLS policies
docker compose exec postgres psql -U iot -d iotcloud -c "
SELECT policyname, cmd, qual FROM pg_policies WHERE tablename = 'telemetry';
"

# Test insert
docker compose exec postgres psql -U iot -d iotcloud -c "
INSERT INTO telemetry (time, tenant_id, device_id, site_id, metrics)
VALUES (now(), 'test-tenant', 'test-device', 'site-1', '{\"temp\": 25.5}');

SELECT * FROM telemetry WHERE tenant_id = 'test-tenant';

DELETE FROM telemetry WHERE tenant_id = 'test-tenant';
"
```

---

## Files

| Action | File |
|--------|------|
| CREATE | `db/migrations/021_telemetry_hypertable.sql` |
