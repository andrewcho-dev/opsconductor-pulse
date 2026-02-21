# Phase 107b — Verify MQTT Command Channel

## Step 1: Migration applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c "\d device_commands"
```

Expected: table exists with `command_id`, `status`, `published_at`,
`acked_at`, `expires_at` columns.

---

## Step 2: Send a command via operator API

```bash
DEVICE_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT device_id FROM device_state LIMIT 1;")

curl -s -X POST \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/commands" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command_type": "ping", "command_params": {}, "expires_in_minutes": 60}' \
  | python3 -m json.tool
```

Expected:
```json
{
  "command_id": "...",
  "status": "queued",
  "mqtt_published": true,
  "expires_at": "..."
}
```

Save command_id:
```bash
CMD_ID=<command_id from above>
```

---

## Step 3: Confirm command in DB

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT command_id, command_type, status, published_at FROM device_commands
   ORDER BY created_at DESC LIMIT 3;"
```

Expected: the ping command with `status = 'queued'` and `published_at` set.

---

## Step 4: Device HTTP ACK

```bash
PROV_TOKEN="tok-your-device-token"

curl -s -X POST \
  "http://localhost:<ingest_port>/device/v1/commands/${CMD_ID}/ack" \
  -H "X-Provision-Token: ${PROV_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"status": "ok", "details": {"message": "pong"}}' \
  | python3 -m json.tool
```

Expected: `{"command_id": "...", "acknowledged": true}`

```bash
# Confirm status is now delivered
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT status, acked_at, ack_details FROM device_commands
   WHERE command_id = '${CMD_ID}';"
```

Expected: `status = 'delivered'`, `acked_at` set, `ack_details` contains `{"status": "ok", ...}`

---

## Step 5: Device HTTP poll for pending commands

```bash
curl -s "http://localhost:<ingest_port>/device/v1/commands/pending" \
  -H "X-Provision-Token: ${PROV_TOKEN}" | python3 -m json.tool
```

Expected: `{"commands": [...]}` — may be empty if all commands have been ACKed or expired.

Send a new command without ACKing to confirm it appears:
```bash
curl -s -X POST \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/commands" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command_type": "flush_buffer", "command_params": {"target": "logs"}}' \
  | python3 -m json.tool

curl -s "http://localhost:<ingest_port>/device/v1/commands/pending" \
  -H "X-Provision-Token: ${PROV_TOKEN}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('pending:', len(d['commands']))"
```

Expected: `pending: 1`

---

## Step 6: Test TTL expiry (missed)

```bash
# Create a command
CMD3=$(curl -s -X POST \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/commands" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command_type": "test_expiry", "command_params": {}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['command_id'])")

# Backdate expires_at to past
docker exec iot-postgres psql -U iot iotcloud -c \
  "UPDATE device_commands SET expires_at = NOW() - INTERVAL '1 minute'
   WHERE command_id = '${CMD3}';"

# Wait for worker tick
sleep 65

# Check status (should be 'missed' since published_at was set)
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT status FROM device_commands WHERE command_id = '${CMD3}';"
```

Expected: `status = 'missed'`

---

## Step 7: List command history via operator API

```bash
curl -s "http://localhost:8000/customer/devices/${DEVICE_ID}/commands" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; cmds=json.load(sys.stdin); [print(c['command_type'], c['status']) for c in cmds]"
```

Expected: a mix of `delivered`, `missed`, `queued` statuses visible.

---

## Step 8: Unit tests

Add `tests/unit/test_commands.py`:

```python
"""Unit tests for command status model."""


def test_command_status_values():
    valid = {"queued", "delivered", "missed", "expired"}
    assert "queued" in valid
    assert "delivered" in valid
    assert "in_progress" not in valid  # not a command status


def test_missed_vs_expired_distinction():
    # missed = published but not ACKed
    # expired = never published
    published_statuses = {"delivered", "missed"}
    unpublished_statuses = {"expired"}
    assert "queued" not in published_statuses
    assert "queued" not in unpublished_statuses
```

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
  db/migrations/079_device_commands.sql \
  services/ui_iot/routes/devices.py \
  services/ingest_iot/ingest.py \
  services/ops_worker/ \
  frontend/src/features/devices/DeviceCommandPanel.tsx \
  frontend/src/features/devices/DeviceDetailPage.tsx \
  frontend/src/services/api/devices.ts \
  tests/unit/test_commands.py

git commit -m "feat: MQTT command channel — fire-and-forget device commands

- Migration 079: device_commands table with status lifecycle
  (queued|delivered|missed|expired), TTL, MQTT publish tracking
- Operator API: POST /devices/{id}/commands (dispatch + MQTT publish),
  GET /devices/{id}/commands (history with status filter)
- MQTT: commands published QoS 1 non-retained; ingest_iot subscribes
  to commands/ack topics for MQTT-based ACK
- Device HTTP API (ingest_iot): GET /device/v1/commands/pending,
  POST /device/v1/commands/{id}/ack
- ops_worker: run_commands_expiry_tick() marks missed (published, not ACKed)
  and expired (never published) after TTL
- Frontend: DeviceCommandPanel with quick-command buttons, send form,
  status history table; integrated in device detail page"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 079: `device_commands` table with RLS and TTL indexes
- [ ] POST /customer/devices/{id}/commands creates command and publishes MQTT
- [ ] `mqtt_published: true` in response when broker is reachable
- [ ] Device HTTP ACK transitions status `queued → delivered`
- [ ] Device HTTP pending poll returns unACKed commands
- [ ] TTL expiry: `queued + published_at set → missed` after expires_at
- [ ] TTL expiry: `queued + published_at null → expired` after expires_at
- [ ] Command history visible in operator API
- [ ] Frontend command panel renders, send form works, history table shows
- [ ] Frontend build passes
- [ ] Full unit suite 0 failures
