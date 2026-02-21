# Prompt 006 — Verify: JSON Log Output + Key Events

## Step 1: Unit tests
```bash
pytest -m unit -v 2>&1 | tail -5
```
Expected: 0 failures.

## Step 2: Confirm no print() calls remain in worker services
```bash
grep -rn "print(" services/evaluator_iot/ services/dispatcher/ \
  services/delivery_worker/ services/ingest_iot/ services/ops_worker/ \
  services/provision_api/ --include="*.py"
```
Expected: 0 results (or only in test files / comments).

## Step 3: Restart services and check log format
```bash
docker compose build evaluator dispatcher delivery_worker ingest ui ops_worker
docker compose up evaluator dispatcher delivery_worker ingest ui ops_worker -d
sleep 3

# Check evaluator logs — should be JSON
docker compose logs evaluator --tail=10
```

Expected output format (one JSON object per line):
```
{"ts": "2026-02-13T...", "level": "INFO", "service": "evaluator", "msg": "listen channel active", "channel": "new_telemetry"}
{"ts": "2026-02-13T...", "level": "INFO", "service": "evaluator", "msg": "evaluation cycle complete", "device_count": 12, "rule_count": 6}
```

## Step 4: Confirm request_id in ui_iot logs
```bash
docker compose logs ui --tail=20 | python3 -c "
import sys, json
for line in sys.stdin:
    line = line.strip()
    # Extract JSON part after docker timestamp
    if '{' in line:
        j = line[line.index('{'):]
        try:
            d = json.loads(j)
            if 'request_id' in d:
                print('FOUND request_id:', d['request_id'], 'path:', d.get('path'))
        except: pass
"
```

## Step 5: Confirm X-Request-ID header in responses
```bash
curl -si http://localhost/api/v2/health | grep -i x-request-id
```
Expected: `X-Request-ID: <8-char-id>`

## Step 6: Confirm key business event logging

Send a telemetry payload and verify the alert creation is logged with context:
```bash
# Send telemetry (adjust values)
curl -s -X POST "http://localhost/ingest/v1/tenant/acme-industrial/device/SENSOR-001/telemetry" ...

# Check evaluator logs for alert created event
sleep 2
docker compose logs evaluator --tail=5 | grep "alert created"
```

Expected: JSON line with `alert_id`, `tenant_id`, `device_id`, `alert_type` fields.

## Step 7: Confirm JSON is valid (parse all lines)
```bash
docker compose logs evaluator --tail=50 | \
  grep '{' | \
  python3 -c "
import sys, json
errors = 0
for line in sys.stdin:
    line = line.strip()
    if '{' in line:
        j = line[line.index('{'):]
        try:
            json.loads(j)
        except json.JSONDecodeError as e:
            print('INVALID JSON:', repr(line[:80]), e)
            errors += 1
print(f'Parse errors: {errors}')
"
```
Expected: `Parse errors: 0`

## Report

- [ ] `pytest -m unit -v` — 0 failures
- [ ] Zero `print()` calls in worker services
- [ ] Log lines are valid single-line JSON
- [ ] `ts`, `level`, `service`, `msg` present on every line
- [ ] `request_id` present on ui_iot request log lines
- [ ] `X-Request-ID` header in HTTP responses
- [ ] Key events (alert created, delivery sent) have context fields

## Gate for Phase 49

Phase 49 options (your choice when ready):
- **Keycloak resilience** — JWKS cache hardening, graceful degradation if Keycloak is down
- **PostgreSQL connection pooling** — add PgBouncer to reduce connection pressure from 10+ polling services
- **Alert acknowledgement UX** — customers can acknowledge/silence alerts from the UI
- **Device provisioning UX** — streamlined onboarding flow for new devices
