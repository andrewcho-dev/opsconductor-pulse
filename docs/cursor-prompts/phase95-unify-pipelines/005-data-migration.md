# Phase 95 — Data Migration Script: integrations → notification_channels

## Goal

Migrate existing tenant `integrations` records to `notification_channels` so customers can
manage everything from the new unified API. This is a one-time, non-destructive operation.
The old `integrations` records are NOT deleted — they continue to function.

## File to create

`db/scripts/migrate_integrations_to_channels.sql`

## Content

```sql
-- One-time migration: copy integrations → notification_channels
-- Safe to run multiple times (ON CONFLICT DO NOTHING).
-- Does NOT delete from integrations.

BEGIN;

-- ── Webhook integrations ──────────────────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'webhook',
    jsonb_build_object(
        'url',     i.config_json->>'url',
        'method',  COALESCE(i.config_json->>'method', 'POST'),
        'headers', COALESCE(i.config_json->'headers', '{}'::jsonb),
        'secret',  i.config_json->>'secret',
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'webhook'
ON CONFLICT DO NOTHING;

-- ── SNMP integrations ────────────────────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'snmp',
    jsonb_build_object(
        'host',              i.snmp_host,
        'port',              COALESCE(i.snmp_port, 162),
        'oid_prefix',        COALESCE(i.snmp_oid_prefix, '1.3.6.1.4.1.99999'),
        'snmp_config',       COALESCE(i.snmp_config, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'snmp'
ON CONFLICT DO NOTHING;

-- ── Email integrations ───────────────────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'email',
    jsonb_build_object(
        'smtp',       COALESCE(i.email_config, '{}'::jsonb),
        'recipients', COALESCE(i.email_recipients, '{}'::jsonb),
        'template',   COALESCE(i.email_template, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'email'
ON CONFLICT DO NOTHING;

-- ── MQTT integrations ────────────────────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'mqtt',
    jsonb_build_object(
        'topic',      i.mqtt_topic,
        'qos',        COALESCE(i.mqtt_qos, 1),
        'retain',     COALESCE(i.mqtt_retain, false),
        'mqtt_config', COALESCE(i.mqtt_config, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'mqtt'
ON CONFLICT DO NOTHING;

-- ── Migrate integration_routes → notification_routing_rules ──────────────
-- For each migrated channel, create corresponding routing rules.
-- We join on the migrated_from_integration_id stored in config JSONB.

INSERT INTO notification_routing_rules (
    tenant_id, channel_id, min_severity, alert_type,
    site_ids, device_prefixes, deliver_on, priority, is_enabled
)
SELECT
    r.tenant_id,
    nc.channel_id,
    r.min_severity,
    CASE WHEN array_length(r.alert_types, 1) = 1 THEN r.alert_types[1] ELSE NULL END,
    r.site_ids,
    r.device_prefixes,
    r.deliver_on,
    r.priority,
    r.enabled
FROM integration_routes r
JOIN notification_channels nc
    ON nc.tenant_id = r.tenant_id
    AND nc.config->>'migrated_from_integration_id' = r.integration_id::text
ON CONFLICT DO NOTHING;

COMMIT;

-- ── Verification query ────────────────────────────────────────────────────
SELECT
    'integrations' AS source,
    type AS channel_type,
    COUNT(*) AS count
FROM integrations
WHERE enabled = TRUE
GROUP BY type
UNION ALL
SELECT
    'notification_channels' AS source,
    channel_type,
    COUNT(*) AS count
FROM notification_channels
WHERE is_enabled = TRUE
  AND config ? 'migrated_from_integration_id'
GROUP BY channel_type
ORDER BY source, channel_type;
```

## How to run

```bash
docker exec -i $(docker ps -qf name=timescaledb) \
  psql -U pulse_user -d pulse_db \
  < db/scripts/migrate_integrations_to_channels.sql
```

## Expected output

The verification query at the end should show matching counts for each channel type between
`integrations` (old) and `notification_channels` (new, migrated).

## After migration: notify tenants (optional)

If you want to notify tenants that their integrations have been migrated:
1. Add a one-time in-app banner in the frontend: "Your notification integrations have been upgraded
   to the new Notification Channels system. Please review your settings."
2. Banner dismissable per tenant (store dismissed state in localStorage or a new user_preferences column).
