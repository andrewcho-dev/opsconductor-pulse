# Phase 98 — Verify Worker Extraction

## Step 1: Confirm ops_worker runs both new ticks

```bash
docker compose -f compose/docker-compose.yml logs ops_worker --tail=50 | grep -i "escalation\|report\|tick\|worker"
```
Expected: log lines showing escalation and report ticks firing.

## Step 2: Confirm ui_iot has no worker references

```bash
docker compose -f compose/docker-compose.yml logs ui --tail=30 | grep -i "escalation\|report_tick"
# Expected: no output — these no longer run in ui
```

## Step 3: Trigger an escalation to confirm it still works end-to-end

Create or find an open alert with an escalation policy attached.
Wait up to 60 seconds and check if escalation_level advances:
```bash
docker exec iot-postgres psql -U iot -d iotcloud -c "
SELECT alert_id, escalation_level, next_escalation_at, updated_at
FROM fleet_alert
WHERE status = 'OPEN' AND escalation_level IS NOT NULL
ORDER BY updated_at DESC LIMIT 5;"
```

## Step 4: Confirm report_worker still generates SLA reports daily

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c "
SELECT report_id, tenant_id, status, created_at
FROM report_runs ORDER BY created_at DESC LIMIT 5;"
```
Expected: rows present (may need to wait for the 24h tick, or trigger manually via a test).

## Step 5: API smoke test

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/alerts
# Expected: 401 (auth required, not 500)

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/notification-channels
# Expected: 401
```

## Step 6: Commit

```bash
git add \
  services/ops_worker/ \
  services/ui_iot/app.py

git commit -m "refactor: move escalation_worker + report_worker from ui_iot into ops_worker

- ops_worker: added run_escalation_tick (60s) and run_report_tick (86400s)
- ui_iot/app.py: removed both background task registrations
- ui_iot process now only handles API requests, WebSocket, batch writes, audit
- Workers run independently in ops_worker and can be restarted without API downtime"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] ops_worker logs show escalation and report ticks running
- [ ] ui_iot logs show NO escalation_worker or report_worker references
- [ ] Escalation still fires for OPEN alerts (end-to-end works)
- [ ] API endpoints still respond correctly
- [ ] ops_worker and ui_iot can be restarted independently without affecting each other
