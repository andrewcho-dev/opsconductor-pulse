-- Migration 068: outbound notification channels and routing rules

CREATE TABLE IF NOT EXISTS notification_channels (
    channel_id      SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    channel_type    TEXT NOT NULL,
    config          JSONB NOT NULL DEFAULT '{}',
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_routing_rules (
    rule_id          SERIAL PRIMARY KEY,
    tenant_id        TEXT NOT NULL,
    channel_id       INTEGER NOT NULL REFERENCES notification_channels(channel_id) ON DELETE CASCADE,
    min_severity     INTEGER,
    alert_type       TEXT,
    device_tag_key   TEXT,
    device_tag_val   TEXT,
    throttle_minutes INTEGER NOT NULL DEFAULT 0,
    is_enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: EXEMPT - global delivery event log keyed by channel/alert IDs
CREATE TABLE IF NOT EXISTS notification_log (
    log_id      BIGSERIAL PRIMARY KEY,
    channel_id  INTEGER NOT NULL,
    alert_id    INTEGER NOT NULL,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_channels_tenant
    ON notification_channels (tenant_id);
CREATE INDEX IF NOT EXISTS idx_routing_rules_tenant
    ON notification_routing_rules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_alert
    ON notification_log (channel_id, alert_id, sent_at DESC);
