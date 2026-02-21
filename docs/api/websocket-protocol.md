---
last-verified: 2026-02-20
sources:
  - services/ui_iot/app.py
  - services/ui_iot/routes/api_v2.py
  - services/ui_iot/routes/telemetry_stream.py
  - frontend/src/services/websocket/manager.ts
phases: [23, 66, 127, 142, 194, 203]
---

# WebSocket Protocol

> WebSocket and SSE real-time specifications.

## Overview

OpsConductor-Pulse supports:

- Legacy v2 WebSocket: `/api/v2/ws` (deprecated with v2 API)
- Current telemetry streaming WebSocket: `/api/v1/customer/telemetry/stream`
- Telemetry streaming SSE: `/api/v1/customer/telemetry/stream/sse`

All streaming protocols enforce tenant isolation derived from JWT claims.

## WebSocket: Legacy v2

### URL

1. Fetch a short-lived websocket ticket:

`GET /api/ws-ticket`

2. Connect with opaque ticket:

`WS /api/v2/ws?ticket=<opaque>`

Auth:

- The ticket is single-use and expires after 30 seconds.
- Ticket exchange resolves the same user JWT context server-side.
- JWT tokens are not placed in websocket URLs.

### Client → Server Messages

```json
{"action": "subscribe", "type": "device", "device_id": "dev-0001"}
{"action": "subscribe", "type": "alerts"}
{"action": "subscribe", "type": "fleet"}
{"action": "unsubscribe", "type": "device", "device_id": "dev-0001"}
{"action": "unsubscribe", "type": "alerts"}
{"action": "unsubscribe", "type": "fleet"}
```

### Server → Client Messages

Examples:

```json
{"type": "telemetry", "device_id": "dev-0001", "data": {"time": "...", "metrics": {...}}}
{"type": "alerts", "alerts": [...]}
{"type": "fleet_summary", "data": {"ONLINE": 10, "STALE": 2, "OFFLINE": 1, "total": 13, "active_alerts": 4}}
{"type": "subscribed", "channel": "device", "device_id": "dev-0001"}
{"type": "error", "message": "..."}
```

### Keepalive

The server sends periodic updates based on a keepalive/loop interval. Clients should:

- Treat connection drops as normal
- Reconnect with exponential backoff
- Resubscribe after reconnect

## WebSocket: Telemetry Stream (Current)

### URL

`WS /api/v1/customer/telemetry/stream?token=<jwt>&device_id=<csv>&metric=<csv>`

Auth:

- JWT passed in query param `token`
- Requires a valid customer role (`customer`, `tenant-admin`, operator roles are also accepted)

Initial filters:

- `device_id`: comma-separated device ids (optional)
- `metric`: comma-separated metric names (optional)

Server sends an initial `connected` message describing the resolved filters.

## SSE: Telemetry Stream

### URL

`GET /api/v1/customer/telemetry/stream/sse?device_id=<csv>&metric=<csv>`

Auth:

- Standard Authorization header/cookie JWT (HTTP auth dependencies apply)

Behavior:

- Server emits `data: <json>` events
- Uses `Last-Event-ID` for simple resume behavior (best-effort)
- Sends comment keepalives when idle

## Status Endpoint

`GET /api/v1/telemetry/stream/status`

- No auth required (intended for monitoring)
- Returns connection counts and limits

## Reconnection Guidance

- Use exponential backoff with jitter
- Re-send subscriptions/filters on reconnect
- For SSE, pass `Last-Event-ID` if you store it to reduce missed events

## See Also

- [API Overview](overview.md)
- [Customer Endpoints](customer-endpoints.md)
- [Dashboards](../features/dashboards.md)

