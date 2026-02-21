# Phase 104 — Verify Time-Window Rules

## Step 1: Migration applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "\d alert_rules" | grep duration_minutes
```

Expected: `duration_minutes | integer | | | `

## Step 2: API accepts duration_minutes

```bash
# Create an alert rule with 5-minute window (replace TOKEN and tenant_id)
curl -s -X POST \
  http://localhost:8000/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"High Temp 5min","metric_name":"temp_c","operator":">","threshold":40,"severity":"warning","duration_minutes":5}' \
  | python3 -m json.tool | grep duration_minutes
```

Expected: `"duration_minutes": 5`

## Step 3: Evaluator does not fire rule on single spike

Inject a single above-threshold telemetry row for a device linked to this rule.
Wait for the evaluator tick. Confirm no alert is created.

```bash
# Check alerts table — should be empty for this rule
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT count(*) FROM alerts WHERE rule_id = '<rule_id>';"
```

## Step 4: Evaluator fires rule after sustained window

Inject 5+ minutes of above-threshold telemetry (or backfill rows with
past timestamps spanning 5 minutes). Trigger an evaluator tick.

```bash
# Expect one alert row
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT count(*) FROM alerts WHERE rule_id = '<rule_id>';"
```

Expected: `count = 1`

## Step 5: Instant rules (duration_minutes = NULL) unchanged

Create a rule with no duration_minutes. Inject one above-threshold row.
Confirm alert fires after one tick.

## Step 6: Frontend builds cleanly

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

## Step 7: Commit

```bash
git add \
  db/migrations/074_alert_rule_duration.sql \
  services/evaluator/evaluator.py \
  services/ui_iot/routes/alerts.py \
  frontend/src/

git commit -m "feat: time-window alert rules — duration_minutes

- Migration 074: alert_rules.duration_minutes (nullable int, >0)
- Evaluator: _condition_holds_for_window() queries telemetry window;
  instant-fire rules (duration_minutes NULL) unchanged
- API: AlertRuleCreate/Update accept duration_minutes; INSERT/UPDATE pass through
- Frontend: duration field in alert rule modal, display in rules table"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 074 applied: `alert_rules.duration_minutes` column exists
- [ ] API returns `duration_minutes` in alert rule objects
- [ ] Single-sample spike does NOT fire a 5-minute window rule
- [ ] Sustained 5 minutes of violations DOES fire the rule
- [ ] Instant rules (NULL duration) still fire on first sample
- [ ] Frontend build passes with duration field visible
