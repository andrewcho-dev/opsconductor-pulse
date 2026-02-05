# Phase 17: Modern Visualization Dashboard

## Goal

Replace hardcoded sparkline charts with interactive Chart.js visualizations showing ALL dynamic device metrics. Add WebSocket-powered live updates to the dashboard. Enable time-range exploration of historical telemetry.

## Problem Statement

Phase 14 added flexible metric ingestion (arbitrary metric keys like `pressure_psi`, `humidity_pct`, `vibration_g`). Phase 16 added an API that returns all metrics dynamically. But the UI still:
- Hardcodes 3 metrics (battery_pct, temp_c, rssi_dbm) in device charts
- Uses server-rendered SVG sparklines (not interactive)
- Refreshes via full-page meta-refresh (not real-time)
- Ignores the API v2 and WebSocket endpoints entirely

## Execution Order

Tasks MUST be executed in order. Each task depends on previous tasks.

| # | File | Description | Dependencies |
|---|------|-------------|--------------|
| 1 | `001-chartjs-setup.md` | Chart.js CDN, chart CSS classes | None |
| 2 | `002-dynamic-device-charts.md` | Replace sparklines with dynamic Chart.js charts | #1 |
| 3 | `003-websocket-live-dashboard.md` | WebSocket live alerts + periodic stats refresh | #1 |
| 4 | `004-time-range-controls.md` | Time-range buttons, enhanced device list | #2 |
| 5 | `005-tests-and-documentation.md` | Tests and README update | #1-#4 |

## Architecture Decisions

1. **Chart.js via CDN**: No build step (no webpack/vite). Chart.js 4 + chartjs-adapter-date-fns loaded from jsDelivr CDN.
2. **Hybrid rendering**: Server renders page structure + initial data (fast first load). JavaScript enhances with interactive charts and real-time updates.
3. **Dynamic metric discovery**: JS fetches from API v2 `/devices/{id}/telemetry`, discovers all metric keys from the response, creates a chart per metric.
4. **WebSocket token**: Route handlers pass the `pulse_session` cookie value to templates via a `ws_token` context variable. JS reads it from a `data-ws-token` attribute.
5. **Progressive enhancement**: Existing pages still work without JS. WebSocket failure falls back to periodic API polling.

## Verification

After each task:
```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```
