# Prompt 007 — Verify Full Suite + Smoke Test

## Your Task

### Step 1: Run full unit suite

```bash
pytest -m unit -v 2>&1 | tail -5
```

Expected: 0 failures. Fix any regressions before continuing.

### Step 2: Run migration against the live DB

```bash
docker compose exec db psql -U iot -d iotcloud -f /migrations/054_alert_rules_duration_seconds.sql
```

Or however migrations are applied in this project. Confirm `duration_seconds` column exists:

```bash
docker compose exec db psql -U iot -d iotcloud -c "\d alert_rules" | grep duration
```

### Step 3: Smoke test — create a rule with duration_seconds via API

```bash
# Replace TOKEN with a valid customer JWT
curl -s -X POST http://localhost/api/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sustained High Temp Test",
    "metric_name": "temp_c",
    "operator": "GT",
    "threshold": 40,
    "severity": 3,
    "duration_seconds": 60
  }' | jq .
```

Confirm response includes `"duration_seconds": 60`.

### Step 4: Smoke test — existing rules unchanged

```bash
curl -s http://localhost/api/customer/alert-rules \
  -H "Authorization: Bearer $TOKEN" | jq '.rules[].duration_seconds'
```

All existing rules should return `0` (the default).

### Step 5: Frontend build check

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: clean build, no TypeScript errors.

### Step 6: Report results

Document:
- Unit test count: X passed, 0 failed
- Migration applied: yes/no
- `duration_seconds` column exists in DB: yes/no
- API accepts duration_seconds: yes/no
- Existing rules return duration_seconds=0: yes/no
- Frontend build clean: yes/no

## Gate for Phase 45

Phase 45 (IaC for AWS) must NOT start until all checks above pass.

Phase 45 plan: Terraform for AWS ECS + RDS (Timescale Cloud) + ALB + S3/CloudFront.
Note from architecture audit: AWS RDS does NOT natively support TimescaleDB.
Options for Phase 45: EC2 self-managed, Timescale Cloud (managed), or migrate to vanilla PostgreSQL with partitioning.
