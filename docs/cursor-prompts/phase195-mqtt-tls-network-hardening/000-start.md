# Phase 195 — MQTT TLS and Network Hardening

## Goal

Enable TLS for all MQTT traffic and remove weak EMQX/MQTT defaults from docker-compose. Device telemetry must not travel in cleartext.

## Current State (problem)

- `compose/docker-compose.yml` sets `MQTT_TLS: "false"` and `MQTT_TLS_INSECURE: "true"` on multiple services.
- `EMQX_DASHBOARD_PASSWORD` defaults to `admin123` and `EMQX_NODE_COOKIE` defaults to `emqx_pulse_secret`.
- Internal MQTT authentication secret defaults to `changeme_auth_secret`.
- No TLS certificates are provisioned for the MQTT broker.

## Target State

- MQTT TLS enabled for external (device) connections.
- Weak EMQX defaults removed — fail if env vars are missing.
- A self-signed CA + broker cert is generated for local development (not committed — gitignored).
- Production deployments use real certs via the existing Caddy TLS infrastructure or cert mounts.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-remove-mqtt-weak-defaults.md` | Remove weak defaults from docker-compose | — |
| 2 | `002-enable-mqtt-tls.md` | Enable MQTT TLS in docker-compose + EMQX config | Step 1 |
| 3 | `003-service-mqtt-tls-clients.md` | Update Python service MQTT clients to use TLS | Step 2 |
| 4 | `004-frontend-mqtt-tls.md` | Update frontend MQTT connection to use WSS/TLS | Step 2 |
| 5 | `005-dev-cert-generation.md` | Add dev cert generation script | Step 2 |
| 6 | `006-update-documentation.md` | Update affected docs | Steps 1–5 |

## Verification

```bash
# No weak defaults remain
grep -E 'admin123|changeme|emqx_pulse_secret' compose/docker-compose.yml
# Must return zero results

# TLS not disabled
grep 'MQTT_TLS.*false\|MQTT_TLS_INSECURE.*true' compose/docker-compose.yml
# Must return zero results
```

## Documentation Impact

- `docs/operations/deployment.md` — MQTT TLS setup instructions
- `docs/services/emqx.md` or `docs/architecture/service-map.md` — Update MQTT transport description
