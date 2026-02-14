# Phase 95 — Verify: Unified Notification Pipeline

## Step 1: Run migration 070

```bash
docker exec -i $(docker ps -qf name=timescaledb) \
  psql -U pulse_user -d pulse_db \
  < db/migrations/070_unify_notification_pipeline.sql

# Verify schema
docker exec -it $(docker ps -qf name=timescaledb) psql -U pulse_user -d pulse_db -c "
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
  AND table_name IN ('notification_jobs','notification_channels','notification_routing_rules','notification_log')
ORDER BY table_name;
"
# Expected: 4 rows
```

## Step 2: Run data migration script

```bash
docker exec -i $(docker ps -qf name=timescaledb) \
  psql -U pulse_user -d pulse_db \
  < db/scripts/migrate_integrations_to_channels.sql
```

Check the verification output — counts should match between old and new systems.

## Step 3: Rebuild and restart services

```bash
docker compose build ui delivery_worker
docker compose up -d ui delivery_worker
docker compose logs ui --tail=30 | grep -E "error|Error|ERROR" | head -20
docker compose logs delivery_worker --tail=30 | grep -E "error|Error|ERROR" | head -20
```

Expected: no startup errors, no import errors.

## Step 4: Check Dockerfile COPY for notifications package

```bash
grep "notifications" services/ui_iot/Dockerfile
```
Expected: `COPY notifications /app/notifications`

## Step 5: Test new channel creation via API

```bash
# Get a customer JWT first (login via Keycloak or use an existing token)
TOKEN="<customer_jwt>"

# Create a webhook channel
curl -s -X POST http://localhost:8000/customer/notification-channels \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Webhook",
    "channel_type": "webhook",
    "config": {"url": "https://httpbin.org/post", "method": "POST"},
    "is_enabled": true
  }' | python3 -m json.tool

# Expected: channel_id returned, channel_type = "webhook"
```

## Step 6: Test routing rule with new fields

```bash
CHANNEL_ID=<from_step_5>

curl -s -X POST http://localhost:8000/customer/notification-routing-rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"channel_id\": $CHANNEL_ID,
    \"min_severity\": 2,
    \"deliver_on\": [\"OPEN\", \"CLOSED\"],
    \"priority\": 50,
    \"is_enabled\": true
  }" | python3 -m json.tool

# Expected: rule_id returned with site_ids=null, device_prefixes=null, deliver_on=["OPEN","CLOSED"]
```

## Step 7: Verify notification_jobs are created on alert

Trigger an alert (or fire the test endpoint):

```bash
curl -s -X POST http://localhost:8000/customer/notification-channels/$CHANNEL_ID/test \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Check notification_jobs:
```bash
docker exec -it $(docker ps -qf name=timescaledb) psql -U pulse_user -d pulse_db -c "
SELECT job_id, channel_id, status, attempts, deliver_on_event, created_at
FROM notification_jobs ORDER BY created_at DESC LIMIT 5;
"
```

Wait a few seconds, then check again:
```bash
docker exec -it $(docker ps -qf name=timescaledb) psql -U pulse_user -d pulse_db -c "
SELECT job_id, channel_id, status, attempts, last_error FROM notification_jobs ORDER BY created_at DESC LIMIT 5;
"
```
Expected: `status = 'COMPLETED'` within 30 seconds.

## Step 8: Verify old integrations API still works with deprecation header

```bash
curl -s -I http://localhost:8000/customer/integrations \
  -H "Authorization: Bearer $TOKEN" | grep -i deprecated

# Expected: X-Deprecated: true; Use /customer/notification-channels instead...
```

## Step 9: Verify frontend redirect

Open browser: navigate to `/customer/integrations`
Expected: redirected to `/customer/notification-channels`

## Step 10: Confirm delivery_worker processes notification_jobs

```bash
docker compose logs delivery_worker --tail=50 | grep -i "notification_job"
# Expected: log lines for each notification_job processed
```

## Step 11: Check operator migration status endpoint

```bash
# Get an operator JWT
OPERATOR_TOKEN="<operator_jwt>"

curl -s http://localhost:8000/operator/migration/integration-status \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | python3 -m json.tool

# Expected:
# {
#   "tenants_on_old_system": N,   (should be 0 after migration)
#   "tenants_on_new_system": M,
#   "total_old_integrations": N,
#   "total_new_channels": M,
#   "migration_complete": true/false
# }
```

## Step 12: Commit

```bash
git add \
  db/migrations/070_unify_notification_pipeline.sql \
  db/scripts/migrate_integrations_to_channels.sql \
  services/ui_iot/notifications/dispatcher.py \
  services/ui_iot/routes/notifications.py \
  services/ui_iot/routes/customer.py \
  services/ui_iot/routes/operator.py \
  services/delivery_worker/worker.py \
  src/  # frontend changes

git commit -m "feat: unify notification pipelines — notification_channels absorbs integrations system

- Migration 070: notification_jobs table + extend notification_routing_rules + drop channel_type constraint
- dispatcher.py: queue notification_jobs instead of direct-send (adds retry/backoff)
- delivery_worker: poll and process notification_jobs for all 7 channel types
- notifications.py: extend API for snmp/email/mqtt channel types + new routing fields
- customer.py: add X-Deprecated header to all /integrations endpoints
- Data migration: integrations → notification_channels (non-destructive)
- Frontend: unify to single Notification Channels UI, redirect /integrations → /notification-channels"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] `notification_jobs` table exists in DB
- [ ] `notification_routing_rules` has `site_ids`, `device_prefixes`, `deliver_on`, `priority` columns
- [ ] `dispatch_alert()` inserts rows to `notification_jobs`, does not call senders directly
- [ ] `delivery_worker` processes `notification_jobs` with retry/backoff
- [ ] All 7 channel types (slack, pagerduty, teams, webhook, email, snmp, mqtt) can be created via API
- [ ] Old tables `integrations`, `integration_routes`, `delivery_jobs`, `delivery_attempts` are GONE
- [ ] Old `/customer/integrations` endpoints return 404
- [ ] Old integrations data migrated to `notification_channels`
- [ ] Frontend has ONE "Notification Channels" navigation entry — no "Integrations" entry
- [ ] Old Integrations page components deleted from src/
- [ ] `delivery_worker` logs show no references to old `integrations` table
- [ ] No regressions in alert generation → notification delivery end-to-end
