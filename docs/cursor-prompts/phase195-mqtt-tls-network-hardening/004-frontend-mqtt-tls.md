# Task 4: Update Frontend MQTT Connection for TLS (mqtts://)

## Context

If the frontend connects directly to EMQX via MQTT.js (over WebSocket), the connection URL must use `mqtts://` or `wss://` instead of `mqtt://` or `ws://` after TLS is enabled.

## Actions

1. Search the frontend for MQTT connection strings:
   ```
   grep -rn 'mqtt://\|ws://.*1883\|ws://.*8883\|mqttClient\|mqtt.connect' frontend/src/
   ```

2. Read each file containing MQTT connection code.

3. For each `mqtt://` or `ws://` URL pointing to the broker:
   - Change the scheme to `mqtts://` or `wss://` as appropriate.
   - Change the port from 1883 to 8883.
   - Ensure the connection options include the correct TLS settings for MQTT.js:
     ```typescript
     const client = mqtt.connect("mqtts://broker-host:8883", {
       rejectUnauthorized: true,  // Must be true in production
       // In dev with self-signed cert, set to false only if VITE_MQTT_INSECURE=true
     });
     ```

4. Make `rejectUnauthorized` configurable via a Vite env var `VITE_MQTT_TLS_INSECURE` that defaults to `false`. Never hard-code `rejectUnauthorized: false`.

5. If the broker URL is currently hardcoded as `mqtt://localhost:1883` (as found in `src/services/api/devices.ts`), change it to read from `import.meta.env.VITE_MQTT_BROKER_URL`. Add `VITE_MQTT_BROKER_URL=mqtts://localhost:8883` to `frontend/.env.example`.

## Verification

```bash
grep -rn "mqtt://" frontend/src/
# Must return zero results — all connections use mqtts:// or wss://

grep -rn "localhost:1883" frontend/src/
# Must return zero results
```
