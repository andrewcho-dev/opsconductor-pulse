# Phase 95 — Data Migration + Drop Old Tables

## Goal

1. Migrate all existing `integrations` + `integration_routes` data → `notification_channels` + `notification_routing_rules`
2. Drop the old tables entirely: `delivery_attempts`, `delivery_jobs`, `integration_routes`, `integrations`

This runs AFTER the new system is verified working (steps 001–004 complete and smoke-tested).

---

## File to create

`db/migrations/071_drop_old_delivery_pipeline.sql`

## Content

```sql
-- Migration 071: Migrate integrations → notification_channels, then drop old tables
-- Run AFTER migration 070 is applied and the new pipeline is verified working.

BEGIN;

-- ── Step 1: Migrate webhook integrations ─────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    tenant_id,
    name,
    'webhook',
    jsonb_build_object(
        'url',     config_json->>'url',
        'method',  COALESCE(config_json->>'method', 'POST'),
        'headers', COALESCE(config_json->'headers', '{}'::jsonb),
        'secret',  config_json->>'secret'
    ),
    enabled,
    created_at
FROM integrations
WHERE type = 'webhook'
ON CONFLICT DO NOTHING;

-- ── Step 2: Migrate SNMP integrations ────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    tenant_id,
    name,
    'snmp',
    jsonb_build_object(
        'host',       snmp_host,
        'port',       COALESCE(snmp_port, 162),
        'oid_prefix', COALESCE(snmp_oid_prefix, '1.3.6.1.4.1.99999'),
        'snmp_config', COALESCE(snmp_config, '{}'::jsonb)
    ),
    enabled,
    created_at
FROM integrations
WHERE type = 'snmp'
ON CONFLICT DO NOTHING;

-- ── Step 3: Migrate email integrations ───────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    tenant_id,
    name,
    'email',
    jsonb_build_object(
        'smtp',       COALESCE(email_config, '{}'::jsonb),
        'recipients', COALESCE(email_recipients, '{}'::jsonb),
        'template',   COALESCE(email_template, '{}'::jsonb)
    ),
    enabled,
    created_at
FROM integrations
WHERE type = 'email'
ON CONFLICT DO NOTHING;

-- ── Step 4: Migrate MQTT integrations ────────────────────────────────────
INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled, created_at)
SELECT
    tenant_id,
    name,
    'mqtt',
    jsonb_build_object(
        'topic',       mqtt_topic,
        'qos',         COALESCE(mqtt_qos, 1),
        'retain',      COALESCE(mqtt_retain, false),
        'mqtt_config', COALESCE(mqtt_config, '{}'::jsonb)
    ),
    enabled,
    created_at
FROM integrations
WHERE type = 'mqtt'
ON CONFLICT DO NOTHING;

-- ── Step 5: Migrate integration_routes → notification_routing_rules ───────
-- Join migrated channels by matching tenant + channel_type + name
-- (since we don't have a direct FK after the copy)
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
JOIN integrations i ON (i.tenant_id = r.tenant_id AND i.integration_id = r.integration_id)
JOIN notification_channels nc ON (
    nc.tenant_id = i.tenant_id
    AND nc.name = i.name
    AND nc.channel_type = i.type
)
ON CONFLICT DO NOTHING;

-- ── Step 6: Verify migration counts before dropping ──────────────────────
DO $$
DECLARE
    old_count INT;
    new_count INT;
BEGIN
    SELECT COUNT(*) INTO old_count FROM integrations;
    SELECT COUNT(*) INTO new_count FROM notification_channels
        WHERE channel_type IN ('webhook','snmp','email','mqtt');

    IF new_count < old_count THEN
        RAISE EXCEPTION 'Migration incomplete: % integrations exist but only % channels migrated',
            old_count, new_count;
    END IF;

    RAISE NOTICE 'Migration verified: % integrations → % notification_channels', old_count, new_count;
END$$;

-- ── Step 7: Drop old tables (cascade handles FK dependencies) ─────────────
DROP TABLE IF EXISTS delivery_attempts CASCADE;
DROP TABLE IF EXISTS delivery_jobs CASCADE;
DROP TABLE IF EXISTS integration_routes CASCADE;
DROP TABLE IF EXISTS integrations CASCADE;

-- ── Step 8: Drop old sequences if any remain ─────────────────────────────
-- (delivery_jobs_job_id_seq may remain as orphan after table drop)
DROP SEQUENCE IF EXISTS delivery_jobs_job_id_seq CASCADE;

COMMIT;

-- ── Final verification ────────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('integrations','integration_routes','delivery_jobs','delivery_attempts')
ORDER BY table_name;
-- Expected: 0 rows (all old tables gone)

SELECT channel_type, COUNT(*) FROM notification_channels GROUP BY channel_type ORDER BY channel_type;
-- Shows all channel types now in one table
```

## How to run

```bash
docker exec -i $(docker ps -qf name=timescaledb) \
  psql -U pulse_user -d pulse_db \
  < db/migrations/071_drop_old_delivery_pipeline.sql
```

## Expected output

```
NOTICE:  Migration verified: N integrations → N notification_channels
 table_name
------------
(0 rows)       ← old tables are gone

 channel_type | count
--------------+-------
 email        |     2
 mqtt         |     1
 slack        |     3
 snmp         |     1
 webhook      |     4
(5 rows)
```

If the verification `DO $$` block raises an exception, **the transaction rolls back** — no data is lost
and the old tables remain intact. Fix the discrepancy before re-running.

---

## Also: Remove delivery_worker service from docker-compose.yml

Since the old pipeline is gone, the standalone `delivery_worker` container is replaced by the
new logic inside `delivery_worker` (which now only processes `notification_jobs`).

### File to modify
`docker-compose.yml`

Find the `delivery_worker` service definition. It currently runs the old worker.
Update its command/entrypoint to run the new notification_jobs worker instead of the old one.

OR — if the delivery_worker service has been fully replaced as per step 003-delivery-worker.md —
simply verify the service still starts cleanly and processes `notification_jobs`.

```bash
docker compose restart delivery_worker
docker compose logs delivery_worker --tail=20
# Expected: no references to 'integrations' table, no errors
```
