# Phase 188 — Fix Device Detail Page Layout

## Problem

Phase 187's device detail layout is broken:

1. **Properties panel is ~900px wide** — PropertyRow has label on far-left, value on far-right with 600px of empty space between. Unreadable.
2. **Everything stacked vertically** — Identity (4 rows) → Hardware (6 rows) → Network (2 rows) → Location → Tags → Notes = massive vertical scroll just for properties.
3. **Telemetry squeezed into tiny 360px right column** — "No telemetry data yet" in a matchbox.
4. **Layout ratio is backwards** — static properties get all the space, live data gets a sliver.

## Fix

Restructure the Overview tab to use compact property cards side-by-side instead of one tall vertical list. Replace the DeviceInfoCard monolith with multiple small cards arranged in a grid.

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-overview-layout-fix.md` | Restructure Overview tab into compact card grid |
| 2 | `002-update-docs.md` | Documentation updates |

## Target Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ GW-001                                    [●STALE·never] [Edit] [Job]  │
│ EdgeGate EG-200 · SimCloud Devices · Site: acme-hq                     │
│                                                                         │
│ [●STALE ] [8 Sensors] [1 Alert ] [2.4.1 FW] [standard Plan]           │
│  never                                                                  │
│                                                                         │
│ [Overview] [Sensors & Data] [Transport] [Health] [Twin] [Security]     │
│                                                                         │
│ ┌─ Identity ──────┐ ┌─ Hardware ──────────┐ ┌─ Network ─────────────┐ │
│ │ ID    GW-001 📋 │ │ Model     EG-200    │ │ IMEI  35265610014... │ │
│ │ Site  acme-hq   │ │ Mfr   SimCloud Dev  │ │ SIM   89012600123... │ │
│ │ Tmpl  Lifeline▸ │ │ Serial EG200-2024.. │ └──────────────────────┘ │
│ │ Seen  never     │ │ MAC   A4:CF:12:...  │ ┌─ Location ────────────┐ │
│ └─────────────────┘ │ HW Rev  v2.1        │ │ 37.774, -122.419     │ │
│                      │ FW Ver  2.4.1       │ │ San Francisco, CA    │ │
│                      └─────────────────────┘ └──────────────────────┘ │
│                                                                         │
│ ┌─ Latest Telemetry ─────────────────────────────────────────────────┐ │
│ │ temperature  24.5°C │ humidity  62% │ pressure  1013hPa │ bat 87% │ │
│ │ signal  -67dBm      │ wind  3.2m/s │ solar  14.2V      │ rain 0  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ Tags ──────────────────────┐ ┌─ Notes ────────────────────────────┐ │
│ │ [outdoor] [weather] [+   ]  │ │ Installed on rooftop B, tower 3   │ │
│ └─────────────────────────────┘ └────────────────────────────────────┘ │
│                                                                         │
│ [Device Plan: standard — $15/mo — Change Plan]                         │
└─────────────────────────────────────────────────────────────────────────┘
```

Key principles:
- **Property sections side-by-side** in a 3-column grid, not stacked vertically
- **PropertyRow uses a compact layout** — no justify-between stretching across 900px
- **Telemetry is full-width** with metrics in a horizontal grid
- **Tags + Notes side-by-side** on one row
- **Everything visible without scrolling** (or minimal scroll)

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Property sections (Identity, Hardware, Network, Location) arranged in a grid, not one tall column
- No huge whitespace gaps between labels and values
- Telemetry snapshot is full-width with metrics in a grid
- Tags and Notes on the same row
- Minimal or no scrolling needed to see the full Overview
