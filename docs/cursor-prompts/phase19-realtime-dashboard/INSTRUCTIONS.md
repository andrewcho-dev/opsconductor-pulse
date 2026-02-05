# Phase 19: Real-Time Dashboard + WebSocket Integration

## Overview

Phase 18 built the React SPA with static data fetching via TanStack Query. This phase adds real-time capabilities: WebSocket connection for live alert streaming, Zustand stores for client-side state, dashboard widgets as isolated components, and a connection status indicator.

After this phase, the dashboard shows live-updating alerts without page reload, and the header displays WebSocket connection status (green dot = live, red dot = offline).

## What Changes

| Layer | Before (Phase 18) | After (Phase 19) |
|-------|-------------------|-------------------|
| Alert data | TanStack Query (60s refetch) | WebSocket live push + TanStack Query fallback |
| State management | TanStack Query only | TanStack Query + Zustand stores |
| Dashboard | Monolithic DashboardPage | Isolated widget components (StatCards, AlertStream, DeviceTable) |
| Connection | No WebSocket | Persistent WebSocket with auto-reconnect |
| Status | No indicator | Connection indicator in header (Live/Offline) |

## Architecture

### Data Flow

```
WebSocket (/api/v2/ws)
    │
    ▼
WebSocket Manager (singleton, non-React)
    │
    ├─► Message Bus (pub/sub)
    │       │
    │       ├─► topic: "alerts" ──► Zustand AlertStore.setLiveAlerts()
    │       │                            │
    │       │                            ▼
    │       │                       AlertStreamWidget (reads from store)
    │       │
    │       ├─► topic: "connection" ──► Zustand UIStore.setWsStatus()
    │       │                               │
    │       │                               ▼
    │       │                          AppHeader (connection dot)
    │       │
    │       └─► topic: "telemetry:{deviceId}" ──► (Phase 20: chart refs)
    │
    └─► Auto-reconnect with exponential backoff
```

### Update Cadence
- **Alerts**: Live push from WebSocket (server polls DB every 5s, pushes to subscribed clients)
- **Device counts**: TanStack Query with 30s staleTime + 60s refetchInterval (no WS push for device list)
- **Connection status**: Immediate on WS open/close events

## Task Sequence

| # | File | Description | Dependencies |
|---|------|-------------|--------------|
| 1 | `001-zustand-stores.md` | Install Zustand, create alert/UI/device stores | None |
| 2 | `002-websocket-service.md` | WebSocket manager, message bus, reconnect logic | #1 |
| 3 | `003-websocket-hook.md` | useWebSocket hook, wire to stores, connection indicator | #1, #2 |
| 4 | `004-dashboard-widgets.md` | Split dashboard into widget components, live AlertStream | #1-#3 |
| 5 | `005-tests-and-documentation.md` | Verify build, backend tests, README update | #1-#4 |

## Exit Criteria

- [ ] Zustand stores for alerts, UI state, and device state
- [ ] WebSocket connects to `/api/v2/ws?token=JWT` on app mount
- [ ] Auto-reconnect with exponential backoff (1s → 2s → 4s → max 30s)
- [ ] Alert stream widget updates live from WebSocket (no page reload)
- [ ] Connection indicator in header (green "Live" / red "Offline")
- [ ] Dashboard split into isolated widget components
- [ ] Widget ErrorBoundary prevents one widget crash from taking down the page
- [ ] Stat cards still work via TanStack Query
- [ ] `npm run build` succeeds
- [ ] All 395 Python backend tests pass

## WebSocket Protocol Reference

### Endpoint
`ws://localhost:8080/api/v2/ws?token=<JWT>`

### Client → Server Messages
```json
{"action": "subscribe", "type": "alerts"}
{"action": "subscribe", "type": "device", "device_id": "dev-0001"}
{"action": "unsubscribe", "type": "alerts"}
{"action": "unsubscribe", "type": "device", "device_id": "dev-0001"}
```

### Server → Client Messages
```json
{"type": "alerts", "alerts": [...]}
{"type": "telemetry", "device_id": "dev-0001", "data": {"timestamp": "...", "metrics": {...}}}
{"type": "subscribed", "channel": "alerts"}
{"type": "subscribed", "channel": "device", "device_id": "dev-0001"}
{"type": "unsubscribed", "channel": "alerts"}
{"type": "error", "message": "..."}
```

### Server Push Behavior
- Server polls database every `WS_POLL_SECONDS` (default: 5 seconds)
- On each poll, pushes ALL open alerts to clients subscribed to "alerts"
- On each poll, pushes latest telemetry for each subscribed device
- Alerts are the FULL list (not incremental) — client replaces entire alert array

### Auth
- JWT passed as `?token=` query parameter
- Closes with code 4001 if token missing/invalid/expired
- Closes with code 4003 if unauthorized role
