-- One-time migration: copy integrations -> notification_channels
-- Safe to run multiple times for channel rows.
-- Does NOT delete from integrations.

BEGIN;

INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'webhook',
    jsonb_build_object(
        'url', i.config_json->>'url',
        'method', COALESCE(i.config_json->>'method', 'POST'),
        'headers', COALESCE(i.config_json->'headers', '{}'::jsonb),
        'secret', i.config_json->>'secret',
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'webhook'
  AND NOT EXISTS (
      SELECT 1
      FROM notification_channels nc
      WHERE nc.tenant_id = i.tenant_id
        AND nc.config->>'migrated_from_integration_id' = i.integration_id::text
  );

INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'snmp',
    jsonb_build_object(
        'host', i.snmp_host,
        'port', COALESCE(i.snmp_port, 162),
        'oid_prefix', COALESCE(i.snmp_oid_prefix, '1.3.6.1.4.1.99999'),
        'snmp_config', COALESCE(i.snmp_config, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'snmp'
  AND NOT EXISTS (
      SELECT 1
      FROM notification_channels nc
      WHERE nc.tenant_id = i.tenant_id
        AND nc.config->>'migrated_from_integration_id' = i.integration_id::text
  );

INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'email',
    jsonb_build_object(
        'smtp', COALESCE(i.email_config, '{}'::jsonb),
        'recipients', COALESCE(i.email_recipients, '{}'::jsonb),
        'template', COALESCE(i.email_template, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'email'
  AND NOT EXISTS (
      SELECT 1
      FROM notification_channels nc
      WHERE nc.tenant_id = i.tenant_id
        AND nc.config->>'migrated_from_integration_id' = i.integration_id::text
  );

INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    i.tenant_id,
    i.name,
    'mqtt',
    jsonb_build_object(
        'topic', i.mqtt_topic,
        'qos', COALESCE(i.mqtt_qos, 1),
        'retain', COALESCE(i.mqtt_retain, false),
        'mqtt_config', COALESCE(i.mqtt_config, '{}'::jsonb),
        'migrated_from_integration_id', i.integration_id::text
    ),
    i.enabled,
    i.created_at
FROM integrations i
WHERE i.type = 'mqtt'
  AND NOT EXISTS (
      SELECT 1
      FROM notification_channels nc
      WHERE nc.tenant_id = i.tenant_id
        AND nc.config->>'migrated_from_integration_id' = i.integration_id::text
  );

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
WHERE NOT EXISTS (
    SELECT 1
    FROM notification_routing_rules rr
    WHERE rr.tenant_id = r.tenant_id
      AND rr.channel_id = nc.channel_id
      AND COALESCE(rr.alert_type, '') = COALESCE(CASE WHEN array_length(r.alert_types, 1) = 1 THEN r.alert_types[1] ELSE NULL END, '')
      AND COALESCE(rr.min_severity, -1) = COALESCE(r.min_severity, -1)
);

COMMIT;
