# Prompt 004 — Final Phase 44 Verification (All Gates Must Pass)

## Your Task

Re-run all Phase 44 prompt 007 verification steps. All must now pass.

### Step 1: Unit tests
```bash
pytest -m unit -v 2>&1 | tail -5
```
Expected: 0 failures.

### Step 2: Migration check
```bash
docker compose exec db psql -U iot -d iotcloud -c "\d alert_rules" | grep -E "duration|operator"
```
Expected: `duration_seconds` column with default 0, `chk_alert_rules_operator` constraint.

### Step 3: API smoke test — POST with duration_seconds
```bash
curl -s -X POST http://localhost/api/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Phase 44b Verification Rule",
    "metric_name": "temp_c",
    "operator": "GT",
    "threshold": 40,
    "severity": 3,
    "duration_seconds": 60
  }' | jq '{status: "created", duration_seconds: .duration_seconds, rule_id: .rule_id}'
```
Expected: `duration_seconds: 60` in response.

### Step 4: Existing rules still return duration_seconds=0
```bash
curl -s http://localhost/api/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" | jq '[.rules[].duration_seconds]'
```
Expected: all values are `0` or `60` (the one just created).

### Step 5: Frontend build
```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: clean build.

### Step 6: Frontend tests
```bash
cd frontend && npm run test -- --run 2>&1 | tail -5
```
Expected: all pass.

### Step 7: Report final status

All six checks must be green before reporting back.

## Gate for Phase 45

Phase 45 is IaC for AWS deployment. Key constraint from architecture audit:

**AWS RDS does NOT natively support TimescaleDB.**

Phase 45 must make a decision on the DB hosting strategy before any Terraform is written:
- Option A: **Timescale Cloud** (managed, fully compatible, extra cost)
- Option B: **EC2 self-managed** (full control, ops burden)
- Option C: **Vanilla PostgreSQL on RDS** (no TimescaleDB — requires migrating away from hypertables, compression, and continuous aggregates)

Report this choice back to the architect when Phase 44b is done so Phase 45 prompts can be written correctly.
