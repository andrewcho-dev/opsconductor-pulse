# Phase 66: Real-Time Fleet Dashboard

## What Exists

- WebSocket endpoint: `/api/v2/ws` with JWT token auth (`?token=JWT_TOKEN`)
- `ConnectionManager` in `ws_manager.py` with `device_subscriptions` + `alert_subscription`
- Client can send: `{"action": "subscribe", "type": "alerts"}` → receives `{"type": "alerts", "alerts": [...]}`
- LISTEN/NOTIFY channels: `new_fleet_alert`, `device_state_changed`
- `FleetSummaryWidget.tsx` exists — shows ONLINE/STALE/OFFLINE counts via REST polling (30s)
- `useFleetSummary()` hook polls `GET /customer/devices/summary` every 30 seconds

## Problem

Fleet dashboard updates are delayed by up to 30 seconds. When an alert opens or a device goes offline, the summary widget shows stale data.

## What This Phase Adds

1. **WebSocket fleet subscription** — add a new subscription type `"fleet"` to the WS protocol. When subscribed, client receives fleet summary updates pushed in real-time whenever `new_fleet_alert` or `device_state_changed` fires.
2. **Backend: push fleet summary on alert/device events** — in `_ws_push_loop`, when LISTEN/NOTIFY fires on `new_fleet_alert` or `device_state_changed`, recompute fleet summary and push to all `fleet`-subscribed clients.
3. **Frontend: useFleetSummaryWS hook** — WebSocket-based fleet summary. Falls back to REST polling if WS unavailable.
4. **Frontend: wire FleetSummaryWidget** — use the new WS hook, show "Live" badge when connected.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: fleet subscription in WS protocol |
| 002 | Frontend: useFleetSummaryWS hook |
| 003 | Frontend: wire FleetSummaryWidget + live badge |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `services/ui_iot/routes/api_v2.py` — prompt 001 (WS push loop)
- `services/ui_iot/ws_manager.py` — prompt 001 (ConnectionManager)
- `frontend/src/hooks/use-fleet-summary.ts` — prompt 002
- `frontend/src/features/devices/FleetSummaryWidget.tsx` — prompt 003
