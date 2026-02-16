-- Migration 093: Message routing rules for telemetry fan-out
-- Customers define rules that match MQTT topics and optionally filter
-- by payload content, then route matched messages to external destinations.
-- Phase 130
-- Date: 2026-02-16

BEGIN;

CREATE TABLE IF NOT EXISTS message_routes (
    id               SERIAL PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    name             VARCHAR(100) NOT NULL,
    topic_filter     VARCHAR(200) NOT NULL,
    destination_type VARCHAR(20) NOT NULL
                     CHECK (destination_type IN ('webhook', 'mqtt_republish', 'postgresql')),
    destination_config JSONB NOT NULL DEFAULT '{}',
    payload_filter   JSONB,
    is_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_message_routes_tenant
    ON message_routes (tenant_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_message_routes_tenant_topic
    ON message_routes (tenant_id) WHERE is_enabled = TRUE;

-- RLS
ALTER TABLE message_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_routes FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON message_routes;
CREATE POLICY tenant_isolation_policy ON message_routes
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON message_routes TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON message_routes TO pulse_operator;
GRANT USAGE ON SEQUENCE message_routes_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE message_routes_id_seq TO pulse_operator;

COMMENT ON TABLE message_routes IS 'Tenant-scoped message routing rules for telemetry fan-out to external destinations';
COMMENT ON COLUMN message_routes.topic_filter IS 'MQTT topic pattern with + (single-level) and # (multi-level) wildcards';
COMMENT ON COLUMN message_routes.payload_filter IS 'Optional JSONPath-like filter expressions, e.g. {\"temperature\": {\"$gt\": 80}}';
COMMENT ON COLUMN message_routes.destination_type IS 'Delivery target: webhook (HTTP POST), mqtt_republish (forward to MQTT topic), postgresql (default write)';

COMMIT;

