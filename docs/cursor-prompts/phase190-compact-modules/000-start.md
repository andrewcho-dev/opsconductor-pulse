# Phase 190 — Compact Expansion Modules Section

## Problem

On the Data tab, each expansion module slot renders as a full-width bordered card with `p-4` padding. With 4 template slots (all empty), this eats ~400px of vertical space for information that could fit in ~100px. The sensors table and telemetry charts — the actual important content — are pushed below the fold.

Each empty slot currently looks like:
```
┌────────────────────────────────────────────────────────────────────┐
│ analog_1  Analog Port 1  [analog]                                 │  ← card border + p-4
│ 0/1 assigned                              [Assign Module]         │
│ No modules assigned.                                              │  ← wasted line
│                                                                    │  ← wasted padding
└────────────────────────────────────────────────────────────────────┘
```

Repeated 4 times = ~400px of empty cards before you see any sensors or data.

## Fix

Replace the per-slot card layout with a single compact bordered table where each slot is one dense row. The "No modules assigned" text disappears — a 0/1 count is self-explanatory. When a slot HAS assigned modules, they appear as indented sub-rows below.

Target layout:
```
Expansion Modules
┌─────────────────────────────────────────────────────────────────┐
│ analog_1  Analog Port 1   [analog]     0/1   [Assign Module]  │
│ analog_2  Analog Port 2   [analog]     0/1   [Assign Module]  │
│ onewire_1 1-Wire Bus      [1-wire]     0/8   [Assign Module]  │
│ fsk_radio FSK Radio Link  [fsk]        0/4   [Assign Module]  │
└─────────────────────────────────────────────────────────────────┘
```

~100px total instead of ~400px.

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-compact-modules.md` | Rewrite expansion modules section in DeviceSensorsDataTab |
| 2 | `002-update-docs.md` | Documentation updates |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Expansion modules fit in ~1/4 the previous vertical space
- Sensors table and telemetry charts visible without scrolling past empty module cards
- Assign Module buttons still work
- Assigned modules (when present) display correctly
