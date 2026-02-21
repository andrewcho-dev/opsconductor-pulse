# Phase 109 — Verify Rules DSL v1

## Step 1: Migration applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "\d alert_rules" | grep match_mode
```

Expected: `match_mode | text | not null | 'all'`

```bash
# Confirm existing rules were backfilled
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT rule_id, metric_name, match_mode,
          jsonb_array_length(conditions) AS condition_count
   FROM alert_rules
   WHERE metric_name IS NOT NULL
   LIMIT 5;"
```

Expected: `condition_count = 1` for all existing single-condition rules.

---

## Step 2: Create a two-condition AND rule via API

```bash
curl -s -X POST "http://localhost:8000/customer/alert-rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hot AND humid",
    "severity": 2,
    "match_mode": "all",
    "conditions": [
      {"metric_name": "temp_c", "operator": "GT", "threshold": 40},
      {"metric_name": "humidity_pct", "operator": "GT", "threshold": 80}
    ]
  }' | python3 -m json.tool
```

Expected: response contains `"match_mode": "all"`, `"conditions"` array with 2 items.

Save the rule_id:
```bash
AND_RULE_ID=<rule_id from above>
```

---

## Step 3: Create a two-condition OR rule

```bash
curl -s -X POST "http://localhost:8000/customer/alert-rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High temp OR low battery",
    "severity": 3,
    "match_mode": "any",
    "conditions": [
      {"metric_name": "temp_c", "operator": "GT", "threshold": 45},
      {"metric_name": "battery_v", "operator": "LT", "threshold": 3.2}
    ]
  }' | python3 -m json.tool
```

Expected: `"match_mode": "any"`, `"conditions"` array with 2 items.

---

## Step 4: Evaluator — AND rule does NOT fire on partial match

Insert telemetry where only ONE of the two conditions is true:
- `temp_c = 50` (above threshold) but `humidity_pct = 40` (below threshold)

```bash
DEVICE_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT device_id FROM device_state LIMIT 1;")

docker exec iot-postgres psql -U iot iotcloud -c "
  INSERT INTO telemetry (tenant_id, device_id, metric_name, value, ts)
  VALUES
    ('your-tenant-id', '${DEVICE_ID}', 'temp_c', 50, NOW()),
    ('your-tenant-id', '${DEVICE_ID}', 'humidity_pct', 40, NOW());
"
```

Wait for evaluator tick (up to 10s), then confirm no alert fired for the AND rule:

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT count(*) FROM fleet_alerts
   WHERE rule_id = '${AND_RULE_ID}' AND status = 'open';"
```

Expected: `count = 0`

---

## Step 5: Evaluator — AND rule DOES fire when both conditions are true

```bash
docker exec iot-postgres psql -U iot iotcloud -c "
  INSERT INTO telemetry (tenant_id, device_id, metric_name, value, ts)
  VALUES
    ('your-tenant-id', '${DEVICE_ID}', 'temp_c', 50, NOW()),
    ('your-tenant-id', '${DEVICE_ID}', 'humidity_pct', 85, NOW());
"
```

Wait for evaluator tick, then confirm alert fired:

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT count(*) FROM fleet_alerts
   WHERE rule_id = '${AND_RULE_ID}' AND status = 'open';"
```

Expected: `count = 1`

---

## Step 6: Existing single-condition rules still work

Pick an existing rule from before this phase. Confirm it still evaluates
correctly by injecting a matching telemetry value and verifying an alert fires.

```bash
OLD_RULE=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT rule_id FROM alert_rules WHERE metric_name IS NOT NULL LIMIT 1;")

echo "Testing rule: ${OLD_RULE}"
```

Inject a value that triggers the rule, wait for tick, confirm alert.
This is the backwards-compatibility smoke test.

---

## Step 7: Unit tests

```bash
pytest tests/unit/ -q --no-cov -k "evaluator or condition" 2>&1 | tail -15
```

Add `tests/unit/test_rules_dsl.py`:

```python
"""Unit tests for multi-condition rule evaluation helpers."""
from evaluator_iot.evaluator import (
    _evaluate_single_condition,
    OPERATOR_SQL,
)


def test_gt_operator():
    assert _evaluate_single_condition(50.0, "GT", 40.0) is True
    assert _evaluate_single_condition(40.0, "GT", 40.0) is False

def test_gte_operator():
    assert _evaluate_single_condition(40.0, "GTE", 40.0) is True
    assert _evaluate_single_condition(39.9, "GTE", 40.0) is False

def test_lt_operator():
    assert _evaluate_single_condition(30.0, "LT", 40.0) is True
    assert _evaluate_single_condition(40.0, "LT", 40.0) is False

def test_lte_operator():
    assert _evaluate_single_condition(40.0, "LTE", 40.0) is True
    assert _evaluate_single_condition(40.1, "LTE", 40.0) is False

def test_none_value_returns_false():
    assert _evaluate_single_condition(None, "GT", 40.0) is False

def test_unknown_operator_returns_false():
    assert _evaluate_single_condition(50.0, "EQ", 40.0) is False

def test_operator_sql_map_complete():
    assert set(OPERATOR_SQL.keys()) == {"GT", "GTE", "LT", "LTE"}
```

---

## Step 8: Full unit suite

```bash
pytest tests/unit/ -q --no-cov 2>&1 | tail -5
```

Expected: 0 failures.

---

## Step 9: Frontend build

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

---

## Step 10: Commit

```bash
git add \
  db/migrations/078_alert_rule_match_mode.sql \
  services/evaluator_iot/evaluator.py \
  services/ui_iot/routes/alerts.py \
  frontend/src/features/alerts/ \
  frontend/src/services/api/types.ts \
  tests/unit/test_rules_dsl.py

git commit -m "feat: Rules DSL v1 — multi-condition AND/OR alert rules

- Migration 078: alert_rules.match_mode ('all'|'any', default 'all');
  backfill conditions JSONB array from existing single-condition rules;
  GIN index on conditions
- Evaluator: _evaluate_rule_conditions() applies match_mode AND/OR across
  conditions; per-condition duration_minutes supported;
  legacy single-condition path preserved for backwards compat
- API: AlertRuleCreate/Update accept conditions[] + match_mode;
  legacy metric_name/operator/threshold still accepted
- Frontend: ConditionRow component, condition builder in alert rule modal,
  AND/OR toggle visible when 2+ conditions, multi-condition summary in table
- Tests: 7 unit tests for _evaluate_single_condition + OPERATOR_SQL"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 078 applied: `match_mode` column, existing rules backfilled to `conditions` array
- [ ] Two-condition AND rule: fires only when BOTH conditions true
- [ ] Two-condition OR rule: fires when EITHER condition true
- [ ] Existing single-condition rules unchanged (backwards compat)
- [ ] API returns `conditions` and `match_mode` on all rule responses
- [ ] Frontend condition builder renders, AND/OR toggle works
- [ ] Frontend build passes
- [ ] 7 unit tests pass for condition evaluation
- [ ] Full unit suite 0 failures
