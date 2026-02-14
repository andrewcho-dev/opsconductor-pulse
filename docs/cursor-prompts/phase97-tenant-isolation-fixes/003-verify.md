# Phase 97 — Verify Tenant Isolation Fixes

## Step 1: Verify migration 072 applied

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c "
SELECT policyname, cmd FROM pg_policies
WHERE tablename = 'telemetry'
ORDER BY policyname;"
# operator_read must NOT appear
```

## Step 2: Verify ingest still processes messages

```bash
docker compose -f compose/docker-compose.yml logs ingest --tail=30
# Expected: no errors, no role-related failures
```

Send a test MQTT message through the simulator if available:
```bash
docker compose -f compose/docker-compose.yml logs simulator --tail=10 2>/dev/null || true
```

## Step 3: Verify operator telemetry access still works

Operator reads bypass RLS via pulse_operator BYPASSRLS — must still work after policy drop:
```bash
curl -s "http://localhost:8000/api/v2/telemetry" \
  -H "Authorization: Bearer $OPERATOR_TOKEN" | python3 -m json.tool | head -20
# Expected: data returned, no 403 or 500
```

## Step 4: Verify tenant_connection still sets context correctly

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c "
-- Simulate what tenant_connection does and verify RLS fires correctly
BEGIN;
SET LOCAL ROLE pulse_app;
SELECT set_config('app.tenant_id', 'test-tenant-123', true);
SELECT current_setting('app.tenant_id');  -- should return 'test-tenant-123'
ROLLBACK;"
```

## Step 5: Code audit checklist

Review the ingest_iot changes manually and confirm:
- [ ] Every DB write path has `SET LOCAL ROLE pulse_app` inside a transaction
- [ ] Every DB write path has `set_config('app.tenant_id', tenant_id, true)`
- [ ] `tenant_id` used is extracted from the validated MQTT topic/HTTP path, not user input
- [ ] Batch writer has a comment documenting its security model (if it uses bulk COPY)
- [ ] No new imports or dependencies added unnecessarily

## Step 6: Commit

```bash
git add \
  db/migrations/072_drop_dead_operator_read_policy.sql \
  services/ingest_iot/ingest.py

git commit -m "fix: enforce tenant RLS context in ingest writes + remove dead operator_read policy

- ingest_iot: add SET LOCAL ROLE pulse_app + set_config(app.tenant_id) to all
  telemetry write paths — enforces DB-level tenant isolation on ingest
- migration 072: drop dead operator_read policy on telemetry (app.role was never
  set; operator access correctly controlled via pulse_operator BYPASSRLS privilege)"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 072 applied — `operator_read` policy gone from telemetry
- [ ] `ingest_iot/ingest.py` sets tenant RLS context on all write paths
- [ ] Ingest service starts and processes messages without errors
- [ ] Operator telemetry queries still return data
- [ ] Customer telemetry queries only return that tenant's data
