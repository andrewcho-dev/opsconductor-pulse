---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/ingest.py
  - services/ingest_iot/ingest.py
phases: [15, 23, 101, 142]
---

# Ingestion Endpoints

> HTTP and MQTT telemetry ingestion endpoints and conventions.

## Overview

There are two ingestion paths:

- MQTT ingestion (primary): devices publish to Mosquitto; `ingest_iot` consumes and writes telemetry.
- HTTP ingestion (alternate): devices send telemetry to `ui_iot` under `/ingest/v1/*`.

Both paths validate device registration, enforce rate limits, and quarantine invalid messages.

## HTTP Ingestion (ui_iot)

Base prefix: `/ingest/v1`

Auth:

- `X-Provision-Token: <token>` (required; validated against device registry hash)

### POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}

Ingest a single telemetry or heartbeat message.

- Path params: `tenant_id`, `device_id`, `msg_type`
- Body fields (modeled):
  - `version` (optional, defaults to `"1"`)
  - `ts` (optional ISO8601 string; if missing the server will use receive time)
  - `site_id` (required)
  - `seq` (optional)
  - `metrics` (optional dict of numbers/bools)

Response:

- `202 Accepted` on success
- `4xx` on validation/auth/rate-limit rejection

Example:

```bash
curl -s --insecure -X POST \
  -H "Content-Type: application/json" \
  -H "X-Provision-Token: $PROVISION_TOKEN" \
  "https://localhost/ingest/v1/tenant/tenant-a/device/dev-001/telemetry" \
  -d '{"site_id":"site-1","ts":"2026-02-17T12:00:00Z","seq":1,"metrics":{"temp_c":22.5}}'
```

### POST /ingest/v1/batch

Batch ingestion. Body shape:

```json
{
  "messages": [
    {
      "tenant_id": "tenant-a",
      "device_id": "dev-001",
      "msg_type": "telemetry",
      "provision_token": "tok-...",
      "site_id": "site-1",
      "ts": "2026-02-17T12:00:00Z",
      "seq": 1,
      "metrics": {"temp_c": 22.5}
    }
  ]
}
```

Response shape:

```json
{
  "accepted": 1,
  "rejected": 0,
  "results": [
    {"index": 0, "status": "accepted"}
  ]
}
```

Example:

```bash
curl -s --insecure -X POST \
  -H "Content-Type: application/json" \
  "https://localhost/ingest/v1/batch" \
  -d '{"messages":[{"tenant_id":"tenant-a","device_id":"dev-001","msg_type":"telemetry","provision_token":"tok-...","site_id":"site-1","ts":"2026-02-17T12:00:00Z","seq":1,"metrics":{"temp_c":22.5}}]}'
```

### GET /ingest/v1/metrics/rate-limits

Returns rate limiter statistics for monitoring.

Auth:

- JWT bearer (operator use is typical)

Example:

```bash
curl -s --insecure \
  -H "Authorization: Bearer $TOKEN" \
  "https://localhost/ingest/v1/metrics/rate-limits"
```

## MQTT Ingestion (ingest_iot)

Topic convention:

- `tenant/{tenant_id}/device/{device_id}/{msg_type}`

Common `msg_type` values include `telemetry` and `heartbeat`.

Auth:

- `provision_token` is read from the payload and validated against the device registry when token enforcement is enabled.
- `site_id` must be present in the payload and match the registry.

Quarantine:

- Invalid topic formats, tenant mismatches between topic and payload, missing required fields, rate limiting, subscription capacity blocks, and auth failures are written to quarantine tables with a reason.

## Batch Writer Behavior

Both ingestion paths ultimately write to `telemetry` via a batch writer:

- Records are buffered and flushed based on `BATCH_SIZE` and `FLUSH_INTERVAL_MS`.
- Failures increment error counters and may quarantine records depending on where rejection happens (pre-write vs write-time).

## See Also

- [API Overview](overview.md)
- [Customer Endpoints](customer-endpoints.md)
- [Service: ingest](../services/ingest.md)
- [Database](../operations/database.md)

