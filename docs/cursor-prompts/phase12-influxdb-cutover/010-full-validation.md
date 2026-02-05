# Task 010: Full Validation

> **CURSOR: EXECUTE THIS TASK**
>
> This is the final validation task for Phases 11 and 12.
> Run every step below. Do not skip any.
> Report the exact results for each check.
> If anything fails, go back and fix it before marking complete.

---

## Context

Phases 11 and 12 migrated telemetry from PostgreSQL to InfluxDB 3 Core. This task validates the complete system end-to-end.

**Prerequisite**: All previous tasks (001-009) must be complete.

---

## Validation Checklist

Run each step and record the result.

### Step 1: All containers healthy

```bash
cd compose && docker compose up -d
docker compose ps
```

**Expected**: All services (mqtt, postgres, influxdb, ingest, evaluator, dispatcher, delivery_worker, device_sim, ui, api, webhook_receiver, keycloak) are running/healthy.

Record the status of each service.

### Step 2: InfluxDB health check

```bash
curl -sf http://localhost:8181/health && echo "OK"
```

**Expected**: Returns 200 OK.

### Step 3: Tenant database exists

```bash
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT 1 AS ok"}'
```

**Expected**: Returns data (not an error about missing database).

### Step 4: InfluxDB receiving telemetry

```bash
# Wait 60 seconds for data, then:
curl -s -X POST http://localhost:8181/api/v3/query_sql \
  -H "Authorization: Bearer influx-dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"db":"telemetry_enabled","q":"SELECT COUNT(*) AS cnt FROM telemetry"}' | python3 -m json.tool
```

**Expected**: count > 0.

### Step 5: No new raw_events rows

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM _deprecated_raw_events WHERE ingested_at > now() - interval '5 minutes'"
```

**Expected**: 0 (no new rows being written).

### Step 6: device_state shows ONLINE devices

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT device_id, status, last_heartbeat_at FROM device_state WHERE status = 'ONLINE' ORDER BY device_id LIMIT 5"
```

**Expected**: Multiple ONLINE devices with recent heartbeat timestamps.

### Step 7: STALE detection works

```bash
# Stop simulator
cd compose && docker compose stop device_sim
sleep 60

# Check for STALE devices
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM device_state WHERE status = 'STALE'"

# Check for open alerts
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN' AND alert_type = 'NO_HEARTBEAT'"
```

**Expected**: Devices go STALE, NO_HEARTBEAT alerts opened.

### Step 8: Recovery works

```bash
# Restart simulator
cd compose && docker compose start device_sim
sleep 30

# Check devices go back ONLINE
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM device_state WHERE status = 'ONLINE'"

# Check alerts closed
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM fleet_alert WHERE status = 'OPEN' AND alert_type = 'NO_HEARTBEAT'"
```

**Expected**: Devices go ONLINE, alerts closed (or closing).

### Step 9: UI works

```bash
source compose/.env

# Customer device detail (sparkline data)
curl -sf "http://${HOST_IP}:8080/customer/devices/dev-0001?format=json" \
  -H "Authorization: Bearer test" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('telemetry rows:', len(d.get('telemetry', [])))
print('event rows:', len(d.get('events', [])))
"
```

**Expected**: telemetry rows > 0, event rows > 0.

### Step 10: Unit tests pass

```bash
cd /home/opsconductor/simcloud
python -m pytest tests/unit/ -v
```

**Expected**: All tests pass. Report exact count.

### Step 11: Integration tests pass

```bash
python -m pytest tests/integration/ -v
```

**Expected**: All tests pass. Report exact count.

### Step 12: No raw_events code references

```bash
grep -rn "raw_events" services/ --include="*.py" | grep -v "__pycache__" | grep -v ".pyc"
```

**Expected**: 0 matches (no Python code references raw_events).

### Step 13: Quarantine still works

```bash
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM quarantine_events"
docker exec iot-postgres psql -U iot -d iotcloud -c \
  "SELECT COUNT(*) FROM quarantine_counters_minute"
```

**Expected**: Both tables still exist and may have data.

### Step 14: Ingest stats show InfluxDB writes

```bash
docker logs iot-ingest --tail 5
```

**Expected**: Stats line shows `influx_ok=N` where N > 0 and `influx_err=0`.

---

## After All Checks Pass

1. Update `docs/cursor-prompts/README.md` to ensure all Phase 11 and Phase 12 tasks are marked `[x]`
2. Verify both phases show **Status: COMPLETE**

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `docs/cursor-prompts/README.md` (verify all [x]) |

---

## Commit

```
Complete Phase 12 validation - InfluxDB migration verified

- All 14 validation checks passed
- InfluxDB is sole telemetry store
- PostgreSQL raw_events deprecated
- STALE detection and alert pipeline working
- UI sparkline charts rendering from InfluxDB
- All tests passing

Part of Phase 12: InfluxDB Cutover
```
