# Phase 23: HTTP/REST Telemetry Ingestion

## Overview

Add HTTP/REST telemetry ingestion as an alternative to MQTT. Devices POST JSON to `/ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}` with the same validation, auth, and write pipeline as MQTT.

## Why

- Universal compatibility — every device/gateway/PLC can make HTTP requests
- Firewall-friendly (HTTPS always allowed)
- No MQTT library needed

## Architecture

- Endpoint lives in `ui_iot` (not a new service)
- Shared logic extracted to `services/shared/ingest_core.py`
- Both MQTT (`ingest_iot`) and HTTP (`ui_iot`) import shared validation/write logic

## Execute Prompts In Order

1. `001-extract-ingest-core.md` — Extract shared module from ingest.py
2. `002-http-ingest-endpoint.md` — Single-message POST endpoint
3. `003-batch-endpoint.md` — Batch POST endpoint (up to 100 messages)
4. `004-caddy-and-env.md` — Caddy routing + environment variables
5. `005-tests-and-docs.md` — Unit tests + documentation

## Key Files

| File | Role |
|------|------|
| `services/ingest_iot/ingest.py` | Source of shared logic to extract |
| `services/shared/ingest_core.py` | NEW shared module |
| `services/ui_iot/app.py` | FastAPI app to extend |
| `services/ui_iot/routes/ingest.py` | NEW ingest router |
| `compose/caddy/Caddyfile` | Reverse proxy config |
| `compose/docker-compose.yml` | Environment variables |

## Endpoints

### Single Message
```
POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}
Headers: X-Provision-Token: tok-xxxxx
Body: {"site_id": "lab-1", "seq": 1, "metrics": {"temp_c": 25.5}}
Response: 202 Accepted
```

### Batch (up to 100)
```
POST /ingest/v1/batch
Body: {"messages": [...]}
Response: 202 Accepted {"accepted": N, "rejected": M, "results": [...]}
```

## Start Now

Read and execute `001-extract-ingest-core.md`.
