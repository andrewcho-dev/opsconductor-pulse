# Phase 91 — Migration: notification_channels + routing_rules

## File
`db/migrations/068_notification_channels.sql`

## SQL

```sql
-- Migration 068: outbound notification channels and routing rules

CREATE TABLE IF NOT EXISTS notification_channels (
    channel_id      SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    channel_type    TEXT NOT NULL,
        -- 'slack' | 'pagerduty' | 'teams' | 'webhook'
    config          JSONB NOT NULL DEFAULT '{}',
        -- slack:      {"webhook_url": "https://hooks.slack.com/..."}
        -- pagerduty:  {"integration_key": "abc123"}
        -- teams:      {"webhook_url": "https://outlook.office.com/webhook/..."}
        -- webhook:    {"url": "https://...", "method": "POST",
        --              "headers": {"X-My-Key": "val"}, "secret": "hmac_secret"}
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_routing_rules (
    rule_id         SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    channel_id      INTEGER NOT NULL REFERENCES notification_channels(channel_id) ON DELETE CASCADE,
    -- Filters (NULL = match all)
    min_severity    INTEGER,          -- e.g. 3 = MEDIUM and above
    alert_type      TEXT,             -- exact match or NULL for any
    device_tag_key  TEXT,             -- route if device has this tag key
    device_tag_val  TEXT,             -- optional: also match tag value
    -- Throttle: don't re-notify for same alert_id within N minutes
    throttle_minutes INTEGER NOT NULL DEFAULT 0,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Track sent notifications to enforce throttle
CREATE TABLE IF NOT EXISTS notification_log (
    log_id          BIGSERIAL PRIMARY KEY,
    channel_id      INTEGER NOT NULL,
    alert_id        INTEGER NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_channels_tenant
    ON notification_channels (tenant_id);
CREATE INDEX IF NOT EXISTS idx_routing_rules_tenant
    ON notification_routing_rules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_alert
    ON notification_log (channel_id, alert_id, sent_at DESC);
```

## Apply
```bash
psql "$DATABASE_URL" -f db/migrations/068_notification_channels.sql
```
