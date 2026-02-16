-- Migration 094: Dead letter queue for failed message route deliveries
-- When a route delivery fails (webhook timeout, connection error, MQTT publish failure),
-- the original message is stored here for later inspection, replay, or discard.
-- Phase 130
-- Date: 2026-02-16

BEGIN;

CREATE TABLE IF NOT EXISTS dead_letter_messages (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    route_id            INTEGER REFERENCES message_routes(id) ON DELETE SET NULL,
    original_topic      VARCHAR(200) NOT NULL,
    payload             JSONB NOT NULL,
    destination_type    VARCHAR(20) NOT NULL,
    destination_config  JSONB NOT NULL DEFAULT '{}',
    error_message       TEXT,
    attempts            INTEGER NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'FAILED'
                        CHECK (status IN ('FAILED', 'REPLAYED', 'DISCARDED')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    replayed_at         TIMESTAMPTZ
);

-- Primary query pattern: list by tenant + status, newest first
CREATE INDEX IF NOT EXISTS idx_dlq_tenant_status_created
    ON dead_letter_messages (tenant_id, status, created_at DESC);

-- For purge queries: find old FAILED entries
CREATE INDEX IF NOT EXISTS idx_dlq_status_created
    ON dead_letter_messages (status, created_at)
    WHERE status = 'FAILED';

-- For replay: look up by route
CREATE INDEX IF NOT EXISTS idx_dlq_route
    ON dead_letter_messages (route_id)
    WHERE route_id IS NOT NULL;

-- RLS
ALTER TABLE dead_letter_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE dead_letter_messages FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON dead_letter_messages;
CREATE POLICY tenant_isolation_policy ON dead_letter_messages
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON dead_letter_messages TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dead_letter_messages TO pulse_operator;
GRANT USAGE ON SEQUENCE dead_letter_messages_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dead_letter_messages_id_seq TO pulse_operator;

COMMENT ON TABLE dead_letter_messages IS 'Failed message route deliveries held for inspection, replay, or discard';
COMMENT ON COLUMN dead_letter_messages.status IS 'FAILED = pending action, REPLAYED = successfully re-delivered, DISCARDED = manually dismissed';

COMMIT;

