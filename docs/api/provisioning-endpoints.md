---
last-verified: 2026-02-17
sources:
  - services/provision_api/app.py
phases: [52, 74, 89, 142]
---

# Provisioning Endpoints

> Device provisioning admin API (standalone service on port 8081).

## Overview

The provisioning API is a separate FastAPI service (`provision_api`) exposed on `http://localhost:8081`.

- Admin endpoints are under `/api/admin/*` and require `X-Admin-Key`.
- Device activation endpoints are under `/api/device/*` and are used during provisioning/activation flows.

## Authentication

### Admin Auth (X-Admin-Key)

Admin routes require:

- Header: `X-Admin-Key: <ADMIN_KEY>`

If the key is missing or incorrect, the service returns 401/403.

## Endpoints

### GET /health

Health check.

```bash
curl -s "http://localhost:8081/health"
```

### POST /api/admin/devices

Create/register a device in the provisioning registry.

Auth: `X-Admin-Key`

```bash
curl -s -X POST "http://localhost:8081/api/admin/devices" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"tenant_id":"tenant-a","device_id":"dev-001","site_id":"site-1"}'
```

### GET /api/admin/devices

List registered devices (supports filtering via query params).

Auth: `X-Admin-Key`

```bash
curl -s "http://localhost:8081/api/admin/devices?tenant_id=tenant-a" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### POST /api/admin/devices/{tenant_id}/{device_id}/revoke

Revoke a device (marks it revoked so it can no longer ingest).

Auth: `X-Admin-Key`

```bash
curl -s -X POST "http://localhost:8081/api/admin/devices/tenant-a/dev-001/revoke" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### POST /api/admin/devices/{tenant_id}/{device_id}/rotate-token

Rotate device provision token and return a new one-time token.

Auth: `X-Admin-Key`

```bash
curl -s -X POST "http://localhost:8081/api/admin/devices/tenant-a/dev-001/rotate-token" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### POST /api/admin/integrations

Create a legacy integration record (for migration/retention workflows).

Auth: `X-Admin-Key`

```bash
curl -s -X POST "http://localhost:8081/api/admin/integrations" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"tenant_id":"tenant-a","name":"legacy-webhook","integration_type":"webhook","config":{}}'
```

### GET /api/admin/integrations

List legacy integrations.

Auth: `X-Admin-Key`

```bash
curl -s "http://localhost:8081/api/admin/integrations?tenant_id=tenant-a" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### POST /api/admin/integration-routes

Create a legacy integration route.

Auth: `X-Admin-Key`

```bash
curl -s -X POST "http://localhost:8081/api/admin/integration-routes" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"tenant_id":"tenant-a","integration_id":"...","deliver_on":["OPEN"],"min_severity":3}'
```

### GET /api/admin/integration-routes

List legacy integration routes.

Auth: `X-Admin-Key`

```bash
curl -s "http://localhost:8081/api/admin/integration-routes?tenant_id=tenant-a" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### POST /api/device/activate

Device activation endpoint (used by devices/tools to exchange an activation code for a provision token).

```bash
curl -s -X POST "http://localhost:8081/api/device/activate" \
  -H "Content-Type: application/json" \
  -d '{"activation_code":"..."}'
```

## See Also

- [Device Management](../features/device-management.md)
- [Ingestion Endpoints](ingest-endpoints.md)
- [Service: provision-api](../services/provision-api.md)

