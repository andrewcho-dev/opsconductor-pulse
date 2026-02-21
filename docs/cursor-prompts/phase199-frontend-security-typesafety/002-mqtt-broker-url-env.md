# Task 2: Move MQTT Broker URL to Environment Variable

## Context

`frontend/src/services/api/devices.ts` has `broker_url: "mqtt://localhost:1883"` hardcoded in the `provisionDevice()` response. This is always wrong outside of local development. The broker URL must come from either the API response (preferred) or a Vite environment variable.

## Actions

1. Read `frontend/src/services/api/devices.ts` in full, focusing on the `provisionDevice()` function.

2. Check: does the backend `POST /provision/device` (or equivalent) already return a `broker_url` in its response? If yes, use that field directly rather than hardcoding anything. This is the preferred approach — the server knows its own address.

3. If the backend does NOT return `broker_url`, add a fallback using a Vite env var:

```typescript
const brokerUrl = import.meta.env.VITE_MQTT_BROKER_URL ?? "mqtts://localhost:8883";

return {
  device_id: created.device_id,
  client_id: created.device_id,
  password: `tok-${created.device_id.toLowerCase()}`,
  broker_url: brokerUrl,
};
```

4. Create or update `frontend/.env.example` to include:
```
# MQTT broker URL for provisioned devices
VITE_MQTT_BROKER_URL=mqtts://localhost:8883
```

5. If the backend API was updated in phase 195 to return `broker_url`, read the backend route and ensure the URL is correct (uses `mqtts://` and port 8883 after TLS is enabled).

6. Do not change any other provisioning logic.

## Verification

```bash
grep -rn 'localhost:1883\|mqtt://localhost' frontend/src/
# Must return zero results
```
