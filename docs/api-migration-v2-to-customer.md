# API Migration Guide: /api/v2/ to /customer/

## Timeline

- Deprecated: 2026-02-16
- Sunset date: 2026-09-01 (endpoints will be removed)
- Removal phase: Phase 129

## Endpoint Mapping

| Deprecated `/api/v2/` endpoint | Replacement `/customer/` endpoint | Notes |
|---|---|---|
| `GET /api/v2/devices` | `GET /customer/devices` | Same query params: limit, offset, status, tags, q, site_id |
| `GET /api/v2/devices/{device_id}` | `GET /customer/devices/{device_id}` | |
| `GET /api/v2/fleet/summary` | `GET /customer/fleet-summary` | Response shape may differ slightly |
| `GET /api/v2/alerts` | `GET /customer/alerts` | Same filters: status, alert_type, limit, offset |
| `GET /api/v2/alerts/trend` | `GET /customer/alerts/trend` | |
| `GET /api/v2/alerts/{alert_id}` | `GET /customer/alerts/{alert_id}` | |
| `GET /api/v2/alert-rules` | `GET /customer/alert-rules` | |
| `GET /api/v2/alert-rules/{rule_id}` | `GET /customer/alert-rules/{rule_id}` | |
| `GET /api/v2/devices/{device_id}/telemetry` | `GET /customer/devices/{device_id}/telemetry` | |
| `GET /api/v2/devices/{device_id}/telemetry/latest` | `GET /customer/devices/{device_id}/telemetry/latest` | |
| `GET /api/v2/telemetry/summary` | `GET /customer/telemetry/summary` | |
| `GET /api/v2/telemetry/chart` | `GET /customer/telemetry/chart` | |
| `GET /api/v2/metrics/reference` | `GET /customer/metrics/reference` | |
| `GET /api/v2/health` | `GET /healthz` | Use the main health endpoint |
| `WS /api/v2/ws` | `WS /customer/ws` | Same protocol, same auth (query param token) |

## Authentication

Both `/api/v2/` and `/customer/` use the same JWT authentication via the `JWTBearer` dependency. No auth changes needed.

## Response Format Differences

The `/customer/` endpoints may have slightly different response envelope shapes. Key differences:

1. `/customer/fleet-summary` returns a different response shape vs `/api/v2/fleet/summary`
2. `/customer/alerts` may include additional fields like `notification_status`

## Migration Steps

1. Update your API base URL from `/api/v2/` to `/customer/`
2. Update WebSocket URL from `ws://host/api/v2/ws?token=...` to `ws://host/customer/ws?token=...`
3. Review response shapes for any minor differences
4. Test all endpoints before the sunset date

## Deprecation Headers

All `/api/v2/` responses now include:

- `Deprecation: true`
- `Sunset: 2026-09-01`
- `Link: </customer/>; rel="successor-version"`
- `X-Deprecated: true; ...migration instructions...`

