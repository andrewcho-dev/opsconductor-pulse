# Task 3: Reorganize API Documentation

## Context

`docs/API_REFERENCE.md` (~300 lines) is a single file covering all endpoints for all audiences. `docs/PULSE_ENVELOPE_V1.md` (~100 lines) covers the telemetry message format. These need to be split by audience and expanded.

## Source Material

- `docs/API_REFERENCE.md` — current API reference (endpoints, examples)
- `docs/PULSE_ENVELOPE_V1.md` — telemetry envelope spec
- `docs/api-migration-v2-to-customer.md` — deprecation mapping (moves to `reference/`)
- Route source files for accuracy verification:
  - `services/ui_iot/routes/customer.py` — customer endpoints
  - `services/ui_iot/routes/operator.py` — operator endpoints
  - `services/ui_iot/routes/ingest.py` — HTTP ingestion
  - `services/ui_iot/routes/api_v2.py` — WebSocket + legacy REST
  - `services/ui_iot/routes/alerts.py` — alert endpoints
  - `services/ui_iot/routes/devices.py` — device endpoints
  - `services/ui_iot/routes/metrics.py` — metrics endpoints
  - `services/ui_iot/routes/exports.py` — export endpoints
  - `services/ui_iot/routes/escalation.py` — escalation endpoints
  - `services/ui_iot/routes/notifications.py` — notification channel endpoints
  - `services/ui_iot/routes/oncall.py` — on-call endpoints
  - `services/ui_iot/routes/jobs.py` — IoT job endpoints
  - `services/ui_iot/routes/ota.py` — OTA firmware endpoints
  - `services/ui_iot/routes/users.py` — user management endpoints
  - `services/ui_iot/routes/roles.py` — role management endpoints
  - `services/ui_iot/routes/system.py` — system/operator endpoints
  - `services/ui_iot/routes/dashboards.py` — dashboard endpoints
  - `services/ui_iot/routes/analytics.py` — analytics endpoints
  - `services/ui_iot/routes/preferences.py` — user preference endpoints
  - `services/ui_iot/routes/message_routing.py` — message routing endpoints
  - `services/ui_iot/routes/telemetry_stream.py` — WS/SSE endpoints
  - `services/ui_iot/routes/billing.py` — billing endpoints
  - `services/ui_iot/routes/organization.py` — organization endpoints
  - `services/ui_iot/routes/certificates.py` — certificate endpoints
  - `services/provision_api/app.py` — provisioning endpoints

## Actions

### File 1: `docs/api/overview.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/middleware/auth.py
  - services/ui_iot/app.py
phases: [1, 7, 23, 101, 128, 142]
---
```

**Content:**
- Authentication model (Keycloak OIDC, JWT Bearer, how to get a dev token)
- API versioning story (`/customer/*` is current, `/api/v2/*` is deprecated with sunset date 2026-09-01)
- Pulse Envelope v1 specification (merge from PULSE_ENVELOPE_V1.md — full schema, transport details for MQTT and HTTP, field descriptions, validation rules, quarantine behavior)
- Common response patterns (pagination, error format)
- Rate limiting behavior

**Structure:**
```markdown
# API Overview
> Authentication, versioning, and message format specifications.

## Authentication
### Getting a Token (Development)
### JWT Claims
### Role-Based Access
## API Versioning
### Current: /customer/* and /operator/*
### Deprecated: /api/v2/* (sunset 2026-09-01)
## Pulse Envelope v1
### Transport (MQTT / HTTP)
### Schema
### Field Reference
### Validation & Quarantine
## Common Patterns
### Pagination
### Error Responses
### Rate Limiting
## See Also
```

### File 2: `docs/api/customer-endpoints.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/customer.py
  - services/ui_iot/routes/alerts.py
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/metrics.py
  - services/ui_iot/routes/exports.py
  - services/ui_iot/routes/escalation.py
  - services/ui_iot/routes/notifications.py
  - services/ui_iot/routes/oncall.py
  - services/ui_iot/routes/jobs.py
  - services/ui_iot/routes/ota.py
  - services/ui_iot/routes/dashboards.py
  - services/ui_iot/routes/preferences.py
  - services/ui_iot/routes/billing.py
  - services/ui_iot/routes/certificates.py
phases: [23, 96, 122, 123, 125, 126, 127, 134, 142]
---
```

**Content:** Extract all customer-facing endpoints from the route files. For each endpoint, document:
- HTTP method + path
- Auth requirement
- Request params/body
- Response shape
- Example curl

Read each route file listed in `sources` above. Extract every `@router.get`, `@router.post`, `@router.put`, `@router.patch`, `@router.delete` that serves customer-facing routes. Group by feature domain:

```markdown
# Customer API Endpoints
> Tenant-scoped REST API for customer users.

## Fleet & Devices
## Alerts
## Alert Rules
## Escalation Policies
## Notification Channels & Routing
## On-Call Schedules
## IoT Jobs & Commands
## OTA Firmware
## Dashboards
## Reports & Exports
## Billing & Subscriptions
## Certificates
## User Preferences
## See Also
```

### File 3: `docs/api/operator-endpoints.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/operator.py
  - services/ui_iot/routes/system.py
  - services/ui_iot/routes/users.py
  - services/ui_iot/routes/roles.py
  - services/ui_iot/routes/analytics.py
  - services/ui_iot/routes/organization.py
  - services/ui_iot/routes/message_routing.py
phases: [30, 43, 65, 97, 130, 142]
---
```

**Content:** All operator-facing endpoints. Same format as customer endpoints.

```markdown
# Operator API Endpoints
> Cross-tenant admin API for operators. All access is audited.

## Tenant Management
## Cross-Tenant Device & Alert Inventory
## System Health & Metrics
## User Management (Keycloak Admin)
## Role Management
## Organizations
## Message Routing & Event Export
## Analytics
## Operator Audit Log
## See Also
```

### File 4: `docs/api/ingest-endpoints.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/ingest.py
  - services/ingest_iot/ingest.py
phases: [15, 23, 101, 142]
---
```

**Content:** HTTP and MQTT ingestion endpoints. Include:
- Single message POST
- Batch POST
- MQTT topic conventions
- Auth (X-Provision-Token)
- Rate limiting
- Batch writer behavior

### File 5: `docs/api/provisioning-endpoints.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/provision_api/app.py
phases: [52, 74, 89, 142]
---
```

**Content:** Provisioning API endpoints. Read `services/provision_api/app.py` and document every route. Include:
- Auth (X-Admin-Key header)
- Device registration
- Token generation
- Activation flow

### File 6: `docs/api/websocket-protocol.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/api_v2.py
  - services/ui_iot/routes/telemetry_stream.py
phases: [23, 66, 127, 142]
---
```

**Content:** WebSocket and SSE real-time specs. Read the source files and document:
- WS connection URL and auth (query param token)
- Message types (alerts, telemetry updates)
- Keepalive behavior
- SSE endpoint for telemetry streaming
- Reconnection guidance

## Accuracy Rules

- Read every route file listed in `sources` before writing. Do NOT copy from API_REFERENCE.md without verifying against the current code.
- Every endpoint documented must have a matching route decorator in the source.
- Do not document endpoints that no longer exist.
- Use the actual path prefixes from the router definitions (e.g., `prefix="/customer"` or `prefix="/api/v1/operator"`).
