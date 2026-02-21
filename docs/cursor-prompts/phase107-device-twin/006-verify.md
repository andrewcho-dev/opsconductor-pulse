# Phase 107 — Verify Device Twin

## Step 1: Migration applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT column_name FROM information_schema.columns
   WHERE table_name = 'device_state'
   AND column_name IN ('desired_state','reported_state','desired_version','reported_version','shadow_updated_at')
   ORDER BY column_name;"
```

Expected: 5 rows returned.

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT indexname FROM pg_indexes
   WHERE tablename = 'device_state' AND indexname = 'idx_device_state_shadow_pending';"
```

Expected: 1 row.

---

## Step 2: shared/twin.py exists

```bash
python3 -c "from shared.twin import compute_delta, sync_status; print('OK')"
```

Expected: `OK`

```bash
python3 -c "
from shared.twin import compute_delta
d = {'a': 1, 'b': 2}
r = {'a': 1, 'b': 99, 'c': 3}
delta = compute_delta(d, r)
assert delta == {'b': 2}, f'Got: {delta}'
print('delta OK')
"
```

---

## Step 3: Operator API — GET twin

```bash
# Get a device_id from your DB
DEVICE_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT device_id FROM device_state LIMIT 1;")

curl -s \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/twin" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: JSON with `desired`, `reported`, `delta`, `desired_version`,
`reported_version`, `sync_status` fields.

---

## Step 4: Operator API — PATCH desired state

```bash
curl -s -X PATCH \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/twin/desired" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"desired": {"reporting_interval_s": 30, "alert_temp_threshold": 45}}' \
  | python3 -m json.tool
```

Expected: `desired_version` incremented (e.g. 1).

```bash
# Verify version advanced in DB
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT desired_version, desired_state FROM device_state WHERE device_id = '${DEVICE_ID}';"
```

---

## Step 5: MQTT retained message published

```bash
# Subscribe to the shadow topic and confirm retained message is present
docker exec iot-mosquitto mosquitto_sub \
  -t "tenant/+/device/${DEVICE_ID}/shadow/desired" \
  -C 1 -W 3 2>/dev/null || \
docker run --rm --network=compose_default eclipse-mosquitto \
  mosquitto_sub -h iot-mosquitto \
  -t "tenant/+/device/${DEVICE_ID}/shadow/desired" \
  -C 1 -W 3
```

Expected: JSON payload with `desired` and `version` fields.

---

## Step 6: Device HTTP pull

```bash
# Get a valid provision token for the device
PROV_TOKEN="tok-your-device-token"

curl -s \
  "http://localhost:<ingest_port>/device/v1/shadow" \
  -H "X-Provision-Token: ${PROV_TOKEN}" | python3 -m json.tool
```

Expected: `{"desired": {...}, "version": 1}`

---

## Step 7: Device HTTP report

```bash
curl -s -X POST \
  "http://localhost:<ingest_port>/device/v1/shadow/reported" \
  -H "X-Provision-Token: ${PROV_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"reported": {"reporting_interval_s": 30, "alert_temp_threshold": 45}, "version": 1}' \
  | python3 -m json.tool
```

Expected: `{"accepted": true, "version": 1}`

```bash
# Confirm sync_status is now "synced"
curl -s \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/twin" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['sync_status'], d['reported_version'])"
```

Expected: `synced 1`

---

## Step 8: Delta endpoint

```bash
# Patch desired to create a delta
curl -s -X PATCH \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/twin/desired" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"desired": {"reporting_interval_s": 60}}' | python3 -m json.tool

# Delta should now show reporting_interval_s
curl -s \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/twin/delta" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: `delta` contains `reporting_interval_s: 60`, `in_sync: false`.

---

## Step 9: Frontend build

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

---

## Step 10: Unit tests

```bash
pytest tests/unit/ -q --no-cov -k "twin" 2>&1 | tail -10
```

If no twin tests exist yet, add basic unit tests for `shared/twin.py`:

```python
# tests/unit/test_twin.py
from shared.twin import compute_delta, sync_status
from datetime import datetime, timezone, timedelta

def test_delta_returns_differing_keys():
    assert compute_delta({"a": 1, "b": 2}, {"a": 1, "b": 99}) == {"b": 2}

def test_delta_includes_missing_reported_keys():
    assert compute_delta({"a": 1}, {}) == {"a": 1}

def test_delta_excludes_reported_only_keys():
    assert compute_delta({}, {"a": 1}) == {}

def test_sync_status_synced():
    now = datetime.now(timezone.utc)
    assert sync_status(3, 3, now) == "synced"

def test_sync_status_pending():
    now = datetime.now(timezone.utc)
    assert sync_status(3, 2, now) == "pending"

def test_sync_status_stale_no_last_seen():
    assert sync_status(1, 1, None) == "stale"

def test_sync_status_stale_old_last_seen():
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    assert sync_status(1, 1, old) == "stale"
```

---

## Step 11: Commit

```bash
git add \
  db/migrations/076_device_shadow.sql \
  services/shared/twin.py \
  services/ui_iot/routes/devices.py \
  services/ingest_iot/ \
  frontend/src/features/devices/DeviceTwinPanel.tsx \
  frontend/src/features/devices/ \
  frontend/src/services/api/devices.ts \
  tests/unit/test_twin.py

git commit -m "feat: Device Twin — AWS IoT Shadow semantics

- Migration 076: desired_state, reported_state, desired/reported_version,
  shadow_updated_at on device_state; pending-sync index
- shared/twin.py: compute_delta(), sync_status() helpers
- Operator API (ui_iot): GET /devices/{id}/twin, PATCH /twin/desired,
  GET /twin/delta; desired_version increments on every write
- Device API (ingest_iot): GET /device/v1/shadow (HTTP pull),
  POST /device/v1/shadow/reported (HTTP ack)
- MQTT: desired state published as retained message on PATCH;
  ingest_iot subscribes to shadow/reported topics
- Frontend: DeviceTwinPanel with desired/reported/delta view,
  sync status badge, inline JSON editor for desired state
- Tests: 7 unit tests for compute_delta and sync_status"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 076 applied: 5 shadow columns + pending-sync index
- [ ] `shared/twin.py` with `compute_delta` and `sync_status`
- [ ] GET /devices/{id}/twin returns full shadow document
- [ ] PATCH /devices/{id}/twin/desired increments desired_version
- [ ] MQTT retained message present on shadow/desired topic after PATCH
- [ ] Device HTTP pull returns current desired state
- [ ] Device HTTP report updates reported_state and reported_version
- [ ] sync_status transitions: pending → synced after device reports
- [ ] Frontend twin panel renders with sync status badge
- [ ] Frontend build passes
- [ ] 7 unit tests pass for twin helpers
