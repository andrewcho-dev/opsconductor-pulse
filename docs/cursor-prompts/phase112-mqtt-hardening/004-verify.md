# Phase 112 — Verify MQTT Hardening

## Step 1: Anonymous connections rejected on all ports

```bash
# Port 1883 — should reject anonymous
docker exec iot-mqtt mosquitto_pub \
  -h localhost -p 1883 \
  -t "test/topic" -m "hello" \
  2>&1 | grep -i "not authorised\|Connection Refused\|error"
```

Expected: `Connection Refused` or `not authorised`

```bash
# Direct test without credentials
docker run --rm --network=compose_iot-network eclipse-mosquitto:2.0.18 \
  mosquitto_pub -h iot-mqtt -p 1883 -t "test" -m "anon" 2>&1
```

Expected: connection refused.

## Step 2: Service account credentials work

```bash
source compose/.env

docker run --rm --network=compose_iot-network eclipse-mosquitto:2.0.18 \
  mosquitto_pub -h iot-mqtt -p 1883 \
  -u "service:pulse" -P "${MQTT_ADMIN_PASSWORD}" \
  -t "test/service" -m "authenticated" \
  && echo "AUTH OK" || echo "AUTH FAILED"
```

Expected: `AUTH OK`

## Step 3: ingest_iot connects successfully

```bash
docker logs iot-ingest --tail=20 | grep -i "mqtt\|connect\|error"
```

Expected: MQTT connected log, no auth errors.

## Step 4: ui_iot publishes successfully

Send a command via the operator API (Phase 107b) and verify it publishes
without auth errors:

```bash
DEVICE_ID=$(docker exec iot-postgres psql -U iot iotcloud -tAc \
  "SELECT device_id FROM device_state LIMIT 1;")

curl -s -X POST \
  "http://localhost:8000/customer/devices/${DEVICE_ID}/commands" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command_type": "ping", "command_params": {}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('mqtt_published:', d['mqtt_published'])"
```

Expected: `mqtt_published: True`

## Step 5: TLS port reachable (if certs generated)

```bash
# Test TLS connection with CA cert verification
docker run --rm --network=compose_iot-network \
  -v $(pwd)/compose/mosquitto/certs:/certs:ro \
  eclipse-mosquitto:2.0.18 \
  mosquitto_sub -h iot-mqtt -p 8883 \
  --cafile /certs/ca.crt \
  -u "service:pulse" -P "${MQTT_ADMIN_PASSWORD}" \
  -t "test/#" -C 0 -W 3 2>&1 | head -5
```

Expected: connects without SSL errors (may timeout waiting for messages — that's fine).

## Step 6: Commit

```bash
git add \
  compose/mosquitto/mosquitto.conf \
  compose/mosquitto/acl.conf \
  compose/mosquitto/certs/ca.crt \
  compose/mosquitto/certs/server.crt \
  compose/mosquitto/passwd.example \
  compose/.env.example \
  compose/docker-compose.yml \
  services/ingest_iot/ingest.py \
  services/ui_iot/services/mqtt_sender.py \
  services/provision_api/

# Confirm private keys are NOT staged
git diff --cached --name-only | grep -E "\.key$|passwd$"
# Expected: no output

git commit -m "feat: MQTT authentication + TLS hardening

- mosquitto.conf: allow_anonymous false; password_file auth on all listeners;
  TLS on port 8883 (external), plaintext 1883 internal Docker network only;
  ACL restricts topic access by username
- Generated self-signed TLS certs (ca.crt, server.crt) — private keys gitignored
- passwd file in named Docker volume (shared with provision_api for device onboarding)
- ingest_iot: MQTT_USERNAME/MQTT_PASSWORD credentials on connect
- mqtt_sender.py: username_pw_set() before connect
- compose: MQTT_ADMIN_PASSWORD env var; mosquitto-passwd named volume;
  port 1883 no longer exposed to host; 8883 and 9001 exposed"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Anonymous MQTT connections rejected on all listeners
- [ ] `service:pulse` credentials authenticate successfully
- [ ] `ingest_iot` connects with credentials, no auth errors in logs
- [ ] `mqtt_published: true` on command dispatch (ui_iot auth works)
- [ ] TLS port 8883 accepts connections with CA cert verification
- [ ] Port 1883 NOT exposed on host (internal only)
- [ ] No private keys or passwd file committed to git
