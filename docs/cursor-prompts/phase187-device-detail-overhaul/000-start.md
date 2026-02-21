# Phase 187 — Device Detail Page Overhaul

## Problem

The device detail page (`/devices/:deviceId`) is poorly organized with no visual hierarchy:

1. **DeviceInfoCard** crams 16+ fields into a single tiny card with `p-2` padding — device_id, status, site, last_seen, model, manufacturer, serial, MAC, IMEI, SIM, HW rev, FW version, location, tags, notes. It's an unreadable wall of small text.
2. **DeviceMapCard** takes 50% of the overview width for a map that's often just "No location set."
3. **DevicePlanPanel** is below the info+map, buried after scrolling.
4. **No status banner** — the device status (ONLINE/OFFLINE/STALE) is a tiny badge inside the info card. This is the most important thing on the page and it's barely visible.
5. **No telemetry snapshot** on the overview — to see current values you have to click the Sensors & Data tab.
6. **No alerts summary** — just a plain text link "View N alerts" at the bottom.
7. **Tags and notes are inline inputs** with no labels, no visual separation.

### What AWS IoT / Azure IoT Hub / ThingsBoard do

Professional IoT device detail pages have:
- **Status banner** at the top — large colored status with last seen time
- **Key stats row** — 3-4 KPI cards (sensors, alerts, uptime, firmware version)
- **Properties panel** — hardware metadata in a clean labeled grid, grouped by section
- **Latest telemetry** — live values shown prominently
- **Alerts summary** — count badge + recent alert cards
- **Map** — only if device has coordinates, not taking 50% of the page

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-overview-restructure.md` | Restructure the Overview tab layout |
| 2 | `002-device-info-card.md` | Rewrite DeviceInfoCard as a proper properties panel |
| 3 | `003-page-header-status.md` | Add status banner + KPI row to page header area |
| 4 | `004-update-docs.md` | Documentation updates |

## Target Overview Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ← Devices / GW-001                                                      │
│ Weather Station Pro                      [Template ▸] [Edit] [Job] [⋮] │
│                                                                         │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│ │ ● ONLINE │ │ 12       │ │ 0        │ │ 99.8%    │ │ v2.1.0   │      │
│ │ 2m ago   │ │ Sensors  │ │ Alerts   │ │ Uptime   │ │ Firmware │      │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                                         │
│ [Overview] [Sensors & Data] [Transport] [Health] [Twin] [Security]     │
│                                                                         │
│ ┌─ Device Properties ────────────────────┐ ┌─ Latest Telemetry ──────┐│
│ │ ┌─ Identity ─────────────────────────┐ │ │ temperature    24.5 °C  ││
│ │ │ Device ID   GW-001         [Copy]  │ │ │ humidity       62.1 %   ││
│ │ │ Site        HQ Campus              │ │ │ pressure       1013 hPa ││
│ │ │ Template    Weather Station Pro    │ │ │ battery        87 %     ││
│ │ │ Plan        Standard ($15/mo)      │ │ │ signal_rssi    -67 dBm  ││
│ │ └────────────────────────────────────┘ │ │ wind_speed     3.2 m/s  ││
│ │ ┌─ Hardware ─────────────────────────┐ │ │ solar_voltage  14.2 V   ││
│ │ │ Model       WS-PRO-3000           │ │ │ rain_rate      0.0 mm/h ││
│ │ │ Manufacturer Acme Devices         │ │ │                          ││
│ │ │ Serial      SN-2024-00142         │ │ │          Updated 2m ago  ││
│ │ │ MAC         AA:BB:CC:DD:EE:FF     │ │ └──────────────────────────┘│
│ │ │ HW Rev      r3.1                  │ │                             │
│ │ │ FW Version  2.1.0                 │ │ ┌─ Location ─────────────┐ │
│ │ └────────────────────────────────────┘ │ │ [Map with marker    ]  │ │
│ │ ┌─ Network ──────────────────────────┐ │ │ 37.7749, -122.4194     │ │
│ │ │ IMEI        123456789012345        │ │ │ San Francisco, CA      │ │
│ │ │ SIM/ICCID   89014103...           │ │ └────────────────────────┘ │
│ │ └────────────────────────────────────┘ │                             │
│ │ ┌─ Tags ─────────────────────────────┐ │                             │
│ │ │ [outdoor] [weather] [campus-a] [+] │ │                             │
│ │ └────────────────────────────────────┘ │                             │
│ │ ┌─ Notes ────────────────────────────┐ │                             │
│ │ │ Installed on rooftop B, tower 3    │ │                             │
│ │ └────────────────────────────────────┘ │                             │
│ └────────────────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
```

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Status + KPI cards visible above the tabs
- Overview tab has 2-column layout: properties left, telemetry + map right
- Properties grouped into Identity, Hardware, Network, Tags, Notes sections
- Telemetry shows latest metric values with units
- Map only shows when device has coordinates
- All existing tab functionality preserved
