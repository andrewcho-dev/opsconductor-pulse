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

    CONSTRAINT telemetry_not_null CHECK (tenant_id IS NOT NULL AND device_id IS NOT NULL)
);

-- Convert to hypertable (1 day chunks)
SELECT create_hypertable(
    'telemetry',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_device_time
    ON telemetry (tenant_id, device_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_time
    ON telemetry (tenant_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_telemetry_tenant_site_time
    ON telemetry (tenant_id, site_id, time DESC)
    WHERE site_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_telemetry_msgtype
    ON telemetry (tenant_id, msg_type, time DESC);

ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON telemetry
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY operator_read ON telemetry
    FOR SELECT
    USING (current_setting('app.role', true) IN ('operator', 'operator_admin'));

GRANT SELECT, INSERT ON telemetry TO pulse_app;
GRANT SELECT ON telemetry TO pulse_operator;

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
