# Phase 20: Telemetry Visualization — ECharts + uPlot

## Overview

Phase 19 added Zustand stores, WebSocket manager, and live dashboard widgets. Phase 20 adds interactive telemetry charts using two complementary chart engines:

- **Apache ECharts** — Rich visualizations: gauges, donuts, radar charts. Used for <500 data points.
- **uPlot** — Ultra-fast time-series line charts. Used for historical telemetry (120-1000 data points).

The primary deliverable is a fully functional **Device Detail Page** with:
1. Device information card (status, site, last seen)
2. Current metric gauges (ECharts gauge per metric)
3. Historical time-series charts (uPlot per metric)
4. Time range selector (1h, 6h, 24h, 7d)
5. Live WebSocket telemetry streaming with chart updates
6. Device-specific alert history

Secondary deliverable: **Fleet health widget** on the dashboard (device status donut chart).

---

## Architecture Reference

### Chart Engine Selection Rules

| Use Case | Engine | Reason |
|----------|--------|--------|
| Gauges (battery, temp, RSSI) | ECharts | Rich gauge component |
| Fleet status donut | ECharts | Pie/donut chart |
| Time-series history (telemetry) | uPlot | Fast rendering, 120-1000 points |
| Any chart with >500 points | uPlot | Performance at scale |
| Any chart with rich interaction needs | ECharts | Tooltips, animations, legends |

### Data Flow: Device Detail Page

```
REST API (initial load)          WebSocket (live updates)
    |                                  |
    v                                  v
useTelemetry(deviceId)      messageBus.on("telemetry:{deviceId}")
    |                                  |
    v                                  v
120 historical points         1 point per ~5s push
    |                                  |
    +----------+  +--------------------+
               |  |
               v  v
        useDeviceTelemetry hook
        (merges REST + WS data)
               |
               v
        Rolling buffer (max 500 points)
               |
      +--------+--------+
      |                  |
      v                  v
MetricGauge          TimeSeriesChart
(ECharts gauge)      (uPlot line chart)
```

### WebSocket Protocol (Device Telemetry)

Subscribe to a device's telemetry:
```json
{"action": "subscribe", "type": "device", "device_id": "dev-0001"}
```

Server pushes every WS_POLL_SECONDS (default 5):
```json
{
  "type": "telemetry",
  "device_id": "dev-0001",
  "data": {
    "timestamp": "2024-01-15T10:30:00+00:00",
    "metrics": {"battery_pct": 87.5, "temp_c": 22.3, "rssi_dbm": -65, "snr_db": 12.5}
  }
}
```

The message bus routes this to topic `telemetry:dev-0001`.

### Existing API Endpoints

| Endpoint | What it returns |
|----------|----------------|
| `GET /api/v2/devices/{id}` | `{ device: Device }` with full state JSONB |
| `GET /api/v2/devices/{id}/telemetry?limit=120&start=...&end=...` | `{ telemetry: TelemetryPoint[], count }` |
| `GET /api/v2/devices/{id}/telemetry/latest?count=1` | Latest N readings |
| `GET /api/v2/alerts?status=OPEN&limit=50` | Alert list (can filter by device_id in future) |

### Existing Types

```typescript
interface TelemetryPoint {
  timestamp: string;                        // ISO 8601
  metrics: Record<string, number | boolean>; // Dynamic metric keys
}

interface Device {
  device_id: string;
  tenant_id: string;
  site_id: string;
  status: string;           // "ONLINE" | "STALE"
  last_seen_at: string | null;
  last_heartbeat_at: string | null;
  last_telemetry_at: string | null;
  state: DeviceState | null; // Latest metric values
}
```

### Existing Infrastructure (from Phase 19)

- `wsManager.subscribe("device", deviceId)` — subscribes to device telemetry on WS
- `wsManager.unsubscribe("device", deviceId)` — unsubscribes
- `messageBus.on("telemetry:{deviceId}", handler)` — listen for telemetry pushes
- `useAlertStore` — live alerts from WS
- `useUIStore` — WS connection status
- `useDeviceStore` — device state (populated from REST, will receive WS updates in future)

---

## Task Execution Order

| # | File | Description | Dependencies |
|---|------|-------------|-------------|
| 1 | `001-chart-libraries.md` | Install ECharts + uPlot, theme, config, transforms | None |
| 2 | `002-chart-components.md` | EChart wrapper, uPlot wrapper, gauge, time-series | #1 |
| 3 | `003-device-telemetry-hook.md` | useDeviceTelemetry hook with REST + WS fusion | #1 |
| 4 | `004-device-detail-page.md` | Full device detail page with charts | #1, #2, #3 |
| 5 | `005-tests-and-documentation.md` | Build verification, backend tests, documentation | #1-#4 |

Execute tasks in order. Each task has its own test section — verify before moving on.

---

## Key Constraints

1. **No backend changes** in Phase 20. All API endpoints already exist.
2. **Dynamic metrics**: Devices can report ANY metric names. Don't hardcode to 4 metrics. Discover available metrics from the data.
3. **Known metrics have config**: battery_pct, temp_c, rssi_dbm, snr_db have predefined gauge ranges and units. Unknown metrics use auto-scaling.
4. **Dark theme**: All charts must match the existing dark theme (HSL variables in index.css).
5. **ErrorBoundary**: All chart sections wrapped in WidgetErrorBoundary.
6. **memo optimization**: Chart components wrapped in React.memo.
7. **Cleanup**: All hooks must clean up WS subscriptions and chart instances on unmount.
