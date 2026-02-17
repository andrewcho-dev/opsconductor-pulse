---
last-verified: 2026-02-17
sources:
  - services/ui_iot/middleware/auth.py
  - services/ui_iot/app.py
phases: [1, 7, 23, 101, 128, 142]
---

# API Overview

> Authentication, versioning, and message format specifications.

## Authentication

OpsConductor-Pulse uses Keycloak OIDC for user authentication. API requests use JWT bearer tokens validated by `ui_iot` against Keycloak JWKS.

### Getting a Token (Development)

In development, the realm is configured to allow obtaining a token for test users.

```bash
TOKEN="$(curl -s -X POST "https://localhost/realms/pulse/protocol/openid-connect/token" \
  -d "client_id=pulse-spa" \
  -d "grant_type=password" \
  -d "username=customer1" \
  -d "password=test123" \
  --insecure | jq -r .access_token)"
```

Use it:

```bash
curl -s --insecure \
  -H "Authorization: Bearer $TOKEN" \
  "https://localhost/api/v1/customer/devices"
```

### JWT Claims

Token validation includes:

- Issuer: `KEYCLOAK_PUBLIC_URL/realms/<KEYCLOAK_REALM>`
- Audience: `JWT_AUDIENCE` (default `pulse-ui`)
- Signature: RS256 with JWKS from `KEYCLOAK_JWKS_URI` (cached)

Tenant identity is derived from the token payload:

- Preferred claim: `organization` (dict or list form)
- Legacy fallback (during migration): `tenant_id`

### Role-Based Access

Roles come from `realm_access.roles`. Core roles:

- `customer` / `tenant-admin` (customer plane)
- `operator` / `operator-admin` (operator plane)

## API Versioning

### Current: /api/v1/customer/* and /api/v1/operator/*

- `/api/v1/customer/*`: tenant-scoped APIs (requires organization membership unless operator)
- `/api/v1/operator/*`: cross-tenant operator APIs (operator role required; audited)

### Deprecated: /api/v2/* (sunset 2026-09-01)

Legacy v2 endpoints (including legacy WebSocket) exist for backward compatibility.

- Deprecated prefix: `/api/v2/*`
- Sunset date: 2026-09-01 (planned)

See the migration reference for mapping guidance.

## Pulse Envelope v1

### Transport (MQTT / HTTP)

MQTT:

- Broker: Mosquitto
- Topic convention: `tenant/{tenant_id}/device/{device_id}/{msg_type}`
- Payload: JSON

HTTP:

- Endpoint: `POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/{msg_type}`
- Header auth: `X-Provision-Token`

### Schema

The ingest pipeline accepts an envelope with these common fields:

```json
{
  "version": "1",
  "ts": "2026-02-09T09:15:23.045Z",
  "site_id": "site-abc",
  "seq": 42,
  "metrics": {
    "temp_c": 25.4,
    "humidity_pct": 61.2,
    "door_open": true
  },
  "provision_token": "tok-xxxxxxxx",
  "lat": 37.7749,
  "lng": -122.4194
}
```

Notes:

- `tenant_id` and `device_id` are taken from the MQTT topic / HTTP path (not from the payload).
- For HTTP ingestion via `ui_iot`, only the modeled fields are accepted by request validation.
- MQTT ingestion via `ingest_iot` tolerates additional fields and may use `lat/lng` (or `latitude/longitude`) for device location updates.

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | No (defaults to `"1"`) | Envelope version. Must be `"1"`. |
| `ts` | string | Yes | ISO 8601 timestamp. Parsed as UTC if timezone missing. |
| `site_id` | string | Yes | Must match the device's registered `site_id` (`SITE_MISMATCH` otherwise). |
| `seq` | integer | No | Sequence number (optional). |
| `metrics` | object | No | Up to 50 key/value pairs. Keys max length 128; values are numeric or boolean. |
| `provision_token` | string | Conditional | Required when token enforcement is enabled. |
| `lat`/`lng` | number | No | Optional location (supported by MQTT ingest). |

### Validation & Quarantine

Invalid messages are rejected and written to `quarantine_events` with a reason. Common reasons include:

- `unsupported_envelope_version:<v>`
- `PAYLOAD_TOO_LARGE`
- `TOO_MANY_METRICS`
- `METRIC_KEY_TOO_LONG`
- `METRIC_KEY_INVALID`
- `RATE_LIMITED`
- `UNREGISTERED_DEVICE`
- `DEVICE_REVOKED`
- `SITE_MISMATCH`
- `TOKEN_MISSING`
- `TOKEN_INVALID`

The MQTT ingestion pipeline adds additional quarantine reasons for topic parsing and subscription capacity checks.

## Common Patterns

### Pagination

List endpoints commonly support:

- `limit` (default varies by endpoint)
- `offset`

### Error Responses

FastAPI errors use:

```json
{"detail": "message"}
```

Validation errors return 422 with a structured list of issues.

### Rate Limiting

Some endpoints are guarded by rate limits (SlowAPI). When rate limited:

- HTTP 429 is returned
- Rate limit headers may be included when enabled

## See Also

- [Customer Endpoints](customer-endpoints.md)
- [Operator Endpoints](operator-endpoints.md)
- [Ingestion Endpoints](ingest-endpoints.md)
- [WebSocket Protocol](websocket-protocol.md)
- [API Migration: v2 → customer](../reference/api-migration-v2-to-customer.md)

