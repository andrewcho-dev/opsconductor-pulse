# Phase 189 — Device Detail Tab Consolidation (6 → 3 Tabs)

## Problem

The device detail page has 6 tabs with poor information architecture:

1. **Transport tab is 80% empty space** — typically just 1 transport entry with collapsible JSON configs
2. **Health data is hidden** — the most important "is my device working?" data is buried in tab 4, not on the Overview
3. **Twin, Commands, Security, Transport are all "management" tasks** scattered across 4 separate tabs
4. **No visual distinction** between subject areas within tabs — everything looks the same
5. **KPI strip is bloated** — 5 cards where 3 suffice (Firmware and Plan info visible elsewhere)

## Fix

Consolidate 6 tabs into 3 with clear information hierarchy:

| Tab | Purpose | Content |
|-----|---------|---------|
| **Overview** | "What is this device and how is it doing?" | Properties + health diagnostics + telemetry snapshot + uptime + map + tags/notes |
| **Data** | "What is it reporting?" | Modules + sensors table + telemetry charts (unchanged) |
| **Manage** | "How is it configured?" | Connectivity + Control + Security + Plan (4 visually distinct sections) |

```
┌─────────────────────────────────────────────────────────────────────────┐
│ GW-001                                     [●STALE·never] [Edit] [Job] │
│ EdgeGate EG-200 · SimCloud Devices · Site: acme-hq                     │
│                                                                         │
│ [● STALE  ] [1 Alert   ] [8 Sensors ]                                  │
│   never        ↑ red                                                    │
│                                                                         │
│ [Overview]  [Data]  [Manage]                                           │
│                                                                         │
│ ┌─ Identity ──────┐ ┌─ Hardware ────────┐ ┌─ Network + Location ─────┐ │
│ │ ...              │ │ ...               │ │ ...                      │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────────────┘ │
│ ┌─ Tags ─────────────────┐ ┌─ Notes ────────────────────────────────┐ │
│ │ ...                     │ │ ...                                    │ │
│ └─────────────────────────┘ └────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ Device Health ──────────────────── [1h][6h][24h][7d][30d] ────────┐ │
│ │ Signal 72% │ Battery 87% │ CPU 42.1C │ Memory 64% │ Uptime 5d    │ │
│ │ [─── Signal Quality Chart ───────────────────────────────────────] │ │
│ │ Network: LTE  Cell: 29301  TX: 1.2MB  RX: 340KB  GPS: 37.77,-122 │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ Latest Telemetry ─────────────────────────────────────────────────┐ │
│ │ temperature  24.5 │ humidity  62 │ pressure  1013 │ battery  87   │ │
│ │ signal -67        │ wind  3.2    │ solar  14.2    │ rain_1h  0    │ │
│ │                                                      Updated 3m ago │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ Uptime ────────────────────────────────── [24h][7d][30d] ────────┐ │
│ │ [████████████████████████████████░░░] Availability (24h)           │ │
│ │ Uptime: 99.5%  │  Offline: 45 min  │  Status: ONLINE              │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─ Map ─────────────────────────────────────────────────────────────┐ │
│ │ [Leaflet map, 200px]                                               │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Manage Tab Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Overview]  [Data]  [Manage]                                           │
│                                                                         │
│ 📡 Connectivity                                                        │
│ Protocol configuration and physical connectivity                        │
│ ─────────────────────────────────────────────────────────────────────── │
│ [MQTT Direct] [Cellular] [active] [primary]     [Edit] [Delete]        │
│ Last connected: 2/15/2026 3:28 PM                                      │
│ ▶ Protocol config                                                      │
│ ▶ Connectivity config                           [Add Transport]        │
│                                                                         │
│ ⌨ Control                                                              │
│ Device twin state and remote commands                                   │
│ ─────────────────────────────────────────────────────────────────────── │
│ [Device Twin panel]                                                     │
│ [Device Command panel]                                                  │
│                                                                         │
│ 🛡 Security                                                            │
│ API tokens and X.509 certificates                                       │
│ ─────────────────────────────────────────────────────────────────────── │
│ [API Tokens section]                                                    │
│ [Certificates section]                                                  │
│                                                                         │
│ 💳 Subscription                                                        │
│ Device plan, limits, and features                                       │
│ ─────────────────────────────────────────────────────────────────────── │
│ [DevicePlanPanel]                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-manage-tab.md` | Create DeviceManageTab component with 4 sectioned areas |
| 2 | `002-restructure-tabs.md` | Restructure DeviceDetailPage: 3 tabs, health on Overview, simplified KPI |
| 3 | `003-update-docs.md` | Documentation updates |

## Key Design Decisions

1. **Existing sub-components are reused directly** — DeviceHealthPanel, DeviceUptimePanel, DeviceTransportTab, DeviceTwinPanel, DeviceCommandPanel, DeviceApiTokensPanel, DeviceCertificatesTab, DevicePlanPanel all take just `deviceId` as prop. No refactoring needed.
2. **Manage tab sections are NOT collapsible** — all visible by default. The user wants visual distinction, not hidden content.
3. **Section headers use icon + title + description + border separator** — lightweight visual grouping.
4. **KPI strip reduced to 3** — Status+LastSeen, Alerts, Sensors. Firmware visible in Hardware card, Plan visible in Manage tab.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- Only 3 tabs visible: Overview, Data, Manage
- Overview shows property cards + health diagnostics + telemetry + uptime + map
- Data tab unchanged (modules, sensors, charts)
- Manage tab has 4 clearly separated sections with icon headers
- KPI strip has 3 cards (no Firmware or Plan cards)
- All functionality preserved (edit, tag, note, transport, twin, commands, security, plan change)
