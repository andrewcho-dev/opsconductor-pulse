BEGIN;

CREATE TABLE IF NOT EXISTS device_connection_events (
    id          BIGSERIAL,
    tenant_id   TEXT         NOT NULL,
    device_id   TEXT         NOT NULL,
    event_type  VARCHAR(20)  NOT NULL,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    details     JSONB        NOT NULL DEFAULT '{}',
    PRIMARY KEY (id)
);

-- Constrain event_type values
ALTER TABLE device_connection_events
    ADD CONSTRAINT chk_connection_event_type
    CHECK (event_type IN ('CONNECTED', 'DISCONNECTED', 'CONNECTION_LOST'));

-- Primary query pattern: device event timeline, newest first
CREATE INDEX IF NOT EXISTS idx_device_conn_events_lookup
    ON device_connection_events (tenant_id, device_id, timestamp DESC);

-- RLS
ALTER TABLE device_connection_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_connection_events_tenant_isolation ON device_connection_events;
CREATE POLICY device_connection_events_tenant_isolation ON device_connection_events
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON TABLE device_connection_events IS
    'Append-only log of device connectivity state changes (CONNECTED/DISCONNECTED/CONNECTION_LOST).';

COMMIT;

