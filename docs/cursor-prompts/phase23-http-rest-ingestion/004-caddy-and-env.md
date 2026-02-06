# Phase 23.4: Caddy Routing and Environment Variables

## Task

Route `/ingest/*` through Caddy to `iot-ui` and add environment variables.

## Step 1: Update Caddyfile

Modify `compose/caddy/Caddyfile`.

Add this block **BEFORE** other `handle` blocks (Caddy matches first):

```caddyfile
handle /ingest/* {
    reverse_proxy iot-ui:8080
}
```

Place it near the existing `/api/*` or `/app/*` routes.

## Step 2: Update docker-compose.yml

Modify `compose/docker-compose.yml` in the `iot-ui` service.

Add these environment variables:

```yaml
  iot-ui:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      INFLUXDB_URL: "http://iot-influxdb:8181"
      INFLUXDB_TOKEN: "${INFLUXDB_TOKEN:-influx-dev-token-change-me}"
      AUTH_CACHE_TTL_SECONDS: "60"
      INFLUX_BATCH_SIZE: "500"
      INFLUX_FLUSH_INTERVAL_MS: "1000"
      REQUIRE_TOKEN: "1"
```

## Step 3: Ensure shared module is accessible

Check that `services/shared` is accessible in the iot-ui container.

Option A - If using volume mounts, add:
```yaml
volumes:
  - ../services/shared:/app/shared:ro
```

Option B - If using Dockerfile COPY, add to `compose/ui_iot/Dockerfile`:
```dockerfile
COPY services/shared /app/shared
```

## Verification

```bash
# Rebuild and test routing
cd /home/opsconductor/simcloud/compose && docker compose up -d --build iot-ui

# Test endpoint is routable (will 422 without proper body, but proves routing works)
curl -v -X POST "http://localhost/ingest/v1/tenant/test/device/test/telemetry" \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: test" \
  -d '{}'
```

## Files

| Action | File |
|--------|------|
| MODIFY | `compose/caddy/Caddyfile` |
| MODIFY | `compose/docker-compose.yml` |
| POSSIBLY MODIFY | `compose/ui_iot/Dockerfile` |
