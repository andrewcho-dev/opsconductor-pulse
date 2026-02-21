# Phase 107b — Migration 079: device_commands table

## File to create
`db/migrations/079_device_commands.sql`

```sql
-- Migration 079: MQTT Command Channel
-- Stores fire-and-forget commands sent to devices.
-- Commands are published QoS 1 over MQTT and optionally ACKed by the device.
-- The ops_worker marks queued commands as missed/expired after TTL.

CREATE TABLE IF NOT EXISTS device_commands (
    command_id      TEXT        NOT NULL DEFAULT gen_random_uuid()::text,
    tenant_id       TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    device_id       TEXT        NOT NULL,

    -- Command payload
    command_type    TEXT        NOT NULL,            -- e.g. "reboot", "flush_buffer", "ping"
    command_params  JSONB       NOT NULL DEFAULT '{}',

    -- Lifecycle
    status          TEXT        NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'delivered', 'missed', 'expired')),

    -- Delivery tracking
    published_at    TIMESTAMPTZ,                     -- when MQTT publish succeeded
    acked_at        TIMESTAMPTZ,                     -- when device ACKed (optional)
    ack_details     JSONB,                           -- device-supplied ACK payload

    -- TTL
    expires_at      TIMESTAMPTZ NOT NULL
                    DEFAULT (NOW() + INTERVAL '1 hour'),

    -- Audit
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (tenant_id, command_id)
);

-- Index: fast lookup of queued/undelivered commands per device
CREATE INDEX IF NOT EXISTS idx_device_commands_device_queued
    ON device_commands (tenant_id, device_id, status)
    WHERE status = 'queued';

-- Index: TTL expiry worker scan
CREATE INDEX IF NOT EXISTS idx_device_commands_expires
    ON device_commands (expires_at)
    WHERE status = 'queued';

-- Index: history lookup per device
CREATE INDEX IF NOT EXISTS idx_device_commands_device_history
    ON device_commands (tenant_id, device_id, created_at DESC);

ALTER TABLE device_commands ENABLE ROW LEVEL SECURITY;
CREATE POLICY device_commands_tenant_isolation ON device_commands
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Verify
SELECT table_name FROM information_schema.tables
WHERE table_name = 'device_commands';
```

## Apply

```bash
docker exec -i iot-postgres psql -U iot iotcloud \
  < db/migrations/079_device_commands.sql
```
