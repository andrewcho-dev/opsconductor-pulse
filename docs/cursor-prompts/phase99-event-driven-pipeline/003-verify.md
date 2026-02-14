# Phase 99 — Verify Event-Driven Evaluator

## Step 1: Confirm evaluator is LISTENing

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c "
SELECT pid, query, state
FROM pg_stat_activity
WHERE query LIKE '%LISTEN%';"
# Expected: at least one row showing evaluator's listener connection
```

## Step 2: Confirm NOTIFY fires on ingest

In one terminal, watch for notifications:
```bash
docker exec -it iot-postgres psql -U iot -d iotcloud -c "
LISTEN telemetry_inserted; SELECT pg_sleep(30);"
```

In another terminal, send a test message (via simulator or direct MQTT publish).
Expected: `Asynchronous notification "telemetry_inserted"` appears within 1 second of message receipt.

## Step 3: Measure alert generation latency

Send a telemetry message that will trigger a threshold rule.
Record the timestamp of the MQTT publish and the timestamp of the resulting `fleet_alert` row:

```bash
# After sending a threshold-triggering message:
docker exec iot-postgres psql -U iot -d iotcloud -c "
SELECT alert_id, triggered_at, created_at, NOW() - created_at AS age
FROM fleet_alert
ORDER BY created_at DESC LIMIT 3;"
```

Expected: alert created within **2–3 seconds** of message publish (was up to 8 seconds before).

## Step 4: Verify fallback poll still works

Stop the ingest service temporarily to prevent any NOTIFYs:
```bash
docker compose -f compose/docker-compose.yml stop ingest
sleep 10
docker compose -f compose/docker-compose.yml logs evaluator --tail=10
# Expected: evaluator still runs evaluation cycles every ~5s via fallback timeout
docker compose -f compose/docker-compose.yml start ingest
```

## Step 5: Verify listener reconnects after DB restart

```bash
docker compose -f compose/docker-compose.yml restart postgres
sleep 10
docker compose -f compose/docker-compose.yml logs evaluator --tail=20
# Expected: evaluator reconnects and resumes LISTENing (no crash, no stuck state)
```

## Step 6: Commit

```bash
git add \
  services/ingest_iot/ingest.py \
  services/shared/ingest_core.py \
  services/evaluator/evaluator.py

git commit -m "perf: event-driven evaluator via PostgreSQL LISTEN/NOTIFY

- ingest: emit pg_notify('telemetry_inserted') after each batch flush
- evaluator: LISTEN on telemetry_inserted channel, wake immediately on NOTIFY
- evaluator: keep 5s poll as fallback for missed NOTIFYs
- evaluator: auto-reconnect listener connection on drop
- Alert generation latency reduced from ~8s to ~3s end-to-end"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] evaluator has an active LISTEN connection visible in pg_stat_activity
- [ ] NOTIFY fires on ingest batch flush
- [ ] Alert generated within 3 seconds of threshold-triggering telemetry
- [ ] Fallback poll still works when no NOTIFY received
- [ ] Listener reconnects after DB restart
