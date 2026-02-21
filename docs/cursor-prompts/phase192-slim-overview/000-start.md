# Phase 192 — Slim Down Device Overview Tab

## Problem

Industry research across 9 IoT platforms (AWS IoT Core, Azure IoT Hub, Azure IoT Central, ThingsBoard, Losant, Particle, Balena, Hologram, Arduino IoT Cloud, Ubidots) revealed a universal pattern: **no platform puts charts or historical telemetry on the device landing page.** The device detail page is for identity + health snapshot + management.

Our current Overview tab has 5 heavy components:

1. DeviceInfoCard (identity property cards) — appropriate
2. DeviceHealthPanel (5 metrics + signal quality chart + health details + time range selector) — too much
3. Latest Telemetry card (up to 12 metrics in a bordered grid) — duplicated on Data tab
4. DeviceUptimePanel (uptime bar + 3-stat grid + time range selector) — too much
5. DeviceMapCard (location pin) — appropriate

This forces users to scroll past diagnostics and charts to reach the Data or Manage tabs.

## Fix

1. Create `DeviceHealthStrip` — compact 5-metric row (Signal, Battery, CPU Temp, Memory, Uptime) with no chart, no time range selector, no detail row
2. Remove DeviceHealthPanel, "Latest Telemetry" card, and DeviceUptimePanel from Overview
3. Overview becomes: **DeviceInfoCard + DeviceHealthStrip + DeviceMapCard** — identity, health snapshot, location

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-slim-overview.md` | Create health strip + slim overview tab |
| 2 | `002-update-docs.md` | Documentation updates |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Overview shows only: identity cards, compact 5-metric health strip, map
- No charts on Overview tab
- No telemetry values grid on Overview tab
- No uptime panel on Overview tab
- No time range selectors on Overview tab
- Data tab unchanged (still has expansion modules, sensors, telemetry charts)
- Manage tab unchanged
