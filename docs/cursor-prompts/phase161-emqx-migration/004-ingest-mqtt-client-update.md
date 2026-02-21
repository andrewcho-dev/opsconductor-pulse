# Task 4: Update Ingest MQTT Client for EMQX Compatibility

## File to Modify

- `services/ingest_iot/ingest.py`

## What to Do

The ingest service connects to the broker as `service_pulse` on port 1883. EMQX is protocol-compatible, so the MQTT client code mostly works as-is. However, a few adjustments are needed.

### Step 1: Check paho-mqtt version compatibility

EMQX 5.x supports MQTT 3.1.1 and 5.0. The ingest service uses `paho-mqtt` v1.6.1 which speaks MQTT 3.1.1 — this is fully compatible.

If upgrading to `paho-mqtt` v2.x, the API changes (`Client()` constructor, callback signatures). For now, keep v1.6.1 unless there's a reason to upgrade.

### Step 2: Update internal TLS configuration

Check whether the EMQX internal listener (port 1883) uses TLS or plain TCP. Based on the EMQX config in Task 1, the internal listener is **plain TCP** (no `ssl_options` block on the `listeners.tcp.internal` config).

If internal listener is plain TCP, update the ingest service environment in docker-compose.yml:

```yaml
    environment:
      # ... existing ...
      # Remove or disable TLS for internal connection (EMQX internal listener is plain TCP)
      # MQTT_CA_CERT: "/mosquitto/certs/ca.crt"       # Not needed for plain TCP
      # MQTT_TLS_INSECURE: "true"                     # Not needed for plain TCP
```

And in `ingest.py`, the TLS block (lines 1847-1858) will gracefully skip when `MQTT_CA_CERT` file doesn't exist (the `if os.path.exists(MQTT_CA_CERT)` guard already handles this).

If you prefer to keep TLS on the internal listener, add SSL config to the EMQX `listeners.tcp.internal` block and keep the existing ingest TLS config as-is.

### Step 3: Verify MQTT client ID uniqueness

EMQX enforces unique client IDs by default (unlike Mosquitto which may allow duplicates). If two ingest instances try to connect with the same client ID, one will be disconnected.

Check if the ingest service sets a client ID. In the current code (line 1842):

```python
client = mqtt.Client()  # No client_id specified — paho generates a random one
```

This is fine — paho generates a unique random client ID each time. No change needed.

### Step 4: Verify subscription works

The ingest service subscribes to:
- `tenant/+/device/+/+` (line 1658)
- `tenant/+/device/+/shadow/reported` (line 1659)
- `tenant/+/device/+/commands/ack` (line 1660)

EMQX understands standard MQTT wildcards (`+` and `#`). No changes needed.

### Step 5: Remove application-level rate limiting (optional)

Since EMQX now handles per-client rate limiting at the broker level (`messages_rate = "10/s"`), the application-level token bucket in ingest_iot is partially redundant.

**Recommendation:** Keep the application-level rate limiter for now. It provides a second layer of defense and tracks per-device statistics. It can be removed in a later phase once EMQX rate limiting is verified in production.

### Step 6: Consider removing application-level cert validation

Since EMQX now validates device certificates at connection time (via the HTTP auth backend), the `_validate_cert_auth()` method in ingest_iot (lines 1308-1347) is partially redundant.

**Recommendation:** Keep it for now as defense-in-depth. The ingest service still validates that the cert CN matches the topic tenant/device, which is a defense layer independent of the broker. This can be simplified in Phase 162 when ingest becomes a NATS consumer (no longer directly connected to MQTT).

## Important Notes

- This is the **lowest-risk task** in the EMQX migration — the ingest service should work with EMQX without any code changes due to protocol compatibility
- The main thing to verify is the TLS configuration — whether the internal listener uses TLS or not
- If anything goes wrong, MQTT connection errors will appear in ingest logs immediately on startup

## Verification

```bash
# Start all services
docker compose up -d

# Check ingest connected to EMQX
docker compose logs --tail 20 ingest | grep -i "mqtt connected"

# Check EMQX shows the service_pulse client
curl -s -u "admin:${EMQX_DASHBOARD_PASSWORD}" \
  http://localhost:18083/api/v5/clients | jq '.data[] | {clientid, username, connected}'

# Verify telemetry flows through
# (use device simulator or manual publish)
docker compose logs --tail 5 ingest | grep "messages_received"
```
