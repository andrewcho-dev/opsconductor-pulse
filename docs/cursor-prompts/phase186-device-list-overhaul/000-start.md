# Phase 186 — Device List Overhaul & Updates Tab Merge

## Problem

The device list screen is a custom master-detail split panel — 380px card list on the left, cramped DeviceDetailPane on the right. This looks nothing like AWS IoT Console, Azure IoT Hub, ThingsBoard, or any professional IoT platform. All of them use:

1. **Full-width DataTable** with sortable columns (Status, Device ID, Template, Site, Last Seen, Alerts)
2. **Click row → navigate to device detail page** (not a side pane)
3. **Proper pagination** ("Showing 1–25 of 142")
4. **Filter bar** above the table
5. **No master-detail split**

Additionally, the Devices Hub has "Campaigns" and "Firmware" as separate tabs when they're two sides of the same OTA workflow. They should be a single "Updates" tab.

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-device-list-datatable.md` | Replace DeviceListPage with full-width DataTable |
| 2 | `002-merge-updates-tab.md` | Merge Campaigns + Firmware into single "Updates" tab |
| 3 | `003-cleanup-dead-code.md` | Delete DeviceDetailPane and unused sub-components |
| 4 | `004-update-docs.md` | Documentation updates |

## Target Result

**Devices Hub: 4 tabs** — Devices, Templates, Map, Updates

**Device list:** Full-width DataTable modeled after AWS IoT / Azure IoT Hub:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Devices                                    [Add Device ▼]              │
│ Manage your device fleet                                                │
│                                                                         │
│ [● 12 Online  ● 3 Stale  ● 1 Offline  |  16 total]                    │
│                                                                         │
│ [Search devices...        ] [Status ▼] [Site ▼] [Template ▼]          │
│                                                                         │
│ Status │ Device ID        │ Template    │ Site      │ Last Seen │ Alerts│
│ ───────┼──────────────────┼─────────────┼───────────┼───────────┼───────│
│ ● ON   │ sensor-001       │ Weather St  │ HQ        │ 2m ago    │       │
│ ● ON   │ sensor-002       │ Weather St  │ HQ        │ 5m ago    │ 2     │
│ ● STALE│ gateway-01       │ Gateway v2  │ Warehouse │ 3h ago    │       │
│ ● OFF  │ pump-controller  │ Pump Ctrl   │ Field-A   │ 2d ago    │ 1     │
│                                                                         │
│ Showing 1–16 of 16                              [← Previous] [Next →]  │
└─────────────────────────────────────────────────────────────────────────┘
```

Click any row → navigates to `/devices/:deviceId` (the existing full detail page with 6 tabs).

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Device list is a full-width DataTable with sortable columns
- Row click navigates to `/devices/:deviceId`
- Health strip still shows Online/Stale/Offline counts
- Search + Status + Site filters work
- "Updates" tab shows campaigns table + firmware table vertically
- DeviceDetailPane.tsx deleted
- No TypeScript errors
