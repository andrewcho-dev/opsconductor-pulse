# Prompt 007 — Verify: End-to-End Latency Smoke Test

## Step 1: Unit tests
```bash
pytest -m unit -v 2>&1 | tail -5
```
Expected: 0 failures.

## Step 2: Apply migration
```bash
docker compose exec db psql -U iot -d iotcloud \
  -f /migrations/056_listen_notify_triggers.sql

# Verify triggers
docker compose exec db psql -U iot -d iotcloud \
  -c "SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE tgname LIKE 'trg_notify%';"
```
Expected: 4 rows (telemetry, fleet_alert, delivery_jobs, device_state).

## Step 3: Restart services
```bash
docker compose build evaluator ingest dispatcher delivery_worker ui
docker compose up evaluator ingest dispatcher delivery_worker ui -d
sleep 5
docker compose logs evaluator --tail=5
docker compose logs dispatcher --tail=5
docker compose logs delivery_worker --tail=5
```

Look for `LISTEN on ... channel active` in each service's logs. If you see `WARNING: LISTEN setup failed`, the trigger migration may not have been applied yet.

## Step 4: Latency smoke test

Send a test telemetry payload and watch the alert pipeline fire. Use the device simulator or curl:

```bash
# Send telemetry that breaches a threshold (adjust values to match an existing rule)
curl -s -X POST "http://localhost/ingest/v1/tenant/acme-industrial/device/SENSOR-001/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1",
    "ts": '"$(date +%s)"',
    "site_id": "acme-hq",
    "seq": 1,
    "metrics": {"temperature": 99},
    "provision_token": "YOUR_PROVISION_TOKEN"
  }'
```

Then watch the pipeline:

```bash
# Watch evaluator log for evaluation triggered
docker compose logs evaluator -f &

# Watch dispatcher log for dispatch triggered
docker compose logs dispatcher -f &

# Check for alert in DB (run ~2s after sending telemetry)
docker compose exec db psql -U iot -d iotcloud \
  -c "SELECT id, created_at, alert_type, status, summary FROM fleet_alert ORDER BY created_at DESC LIMIT 3;"
```

## Step 5: Measure latency

Record time from telemetry send to alert row created_at. Expected: <3 seconds. Previous: ~13 seconds.

## Step 6: Verify WebSocket push

Open the browser, navigate to the device list page. Send another telemetry payload. Confirm the device status updates in the UI within ~2 seconds without a manual page refresh.

## Step 7: Verify graceful degradation

Temporarily stop the listener connection test:
```bash
# Check that services still work even if they fall back to poll-only
# (The fallback poll fires every 30s — services remain functional)
docker compose logs evaluator --tail=20 | grep -E "LISTEN|fallback|error"
```

## Report

- [ ] 4 triggers present in DB
- [ ] All 3 services log `LISTEN on ... channel active`
- [ ] Alert created within <3s of telemetry send
- [ ] UI updates within ~2s of telemetry send (WebSocket push)
- [ ] `pytest -m unit -v` — 0 failures

## Gate for Phase 48

Phase 48 is **Observability** — structured logging standard across all services, replacing ad-hoc `print()` calls with structured JSON logs that can be aggregated and searched.
