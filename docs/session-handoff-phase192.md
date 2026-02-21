# Session Handoff — Device Detail Page Redesign (Phases 188–192)

## Project

**OpsConductor Pulse** — Multi-tenant IoT fleet management SaaS platform.
Stack: React + TypeScript + Vite frontend, TanStack Query, shadcn/ui, Tailwind CSS v4. Python backend. PostgreSQL.

## Claude Operating Mode

Per `CLAUDE.md`, Claude operates as **PRINCIPAL ENGINEER / ARCHITECT**:
- **NEVER writes code directly** — only writes structured cursor prompts to `docs/cursor-prompts/phaseXX-description/`
- Each phase has `000-start.md` (overview) + numbered task files (`001-`, `002-`, etc.)
- Final task in every phase is always a documentation update
- Uses TaskCreate/TaskUpdate for tracking multi-step work

## Current Branch & State

- **Branch:** `phases-119-131-platform-maturity`
- **Last commit:** `b836f57 feat(phase187): overhaul device detail page layout`
- **Uncommitted changes:** Phases 188–192 are executed but NOT committed. All modifications are staged/unstaged:
  - `DeviceDetailPage.tsx` — modified (3 tabs, health strip, no charts on Overview)
  - `DeviceInfoCard.tsx` — modified (fragment-based 3-column property cards)
  - `DeviceSensorsDataTab.tsx` — modified (collapsible modules, max-w-2xl)
  - `DeviceHealthStrip.tsx` — NEW (compact 5-metric row)
  - `DeviceManageTab.tsx` — NEW (4-section manage tab)
  - 4 doc files updated (frontmatter + content for phases 188–192)
  - Cursor prompt directories created for phases 188–192

## What Was Done (This Session)

### Phase 188 — Device Detail Layout Fix (EXECUTED)
- Replaced monolithic `DeviceInfoCard` with fragment-based 3-column property card grid
- Fixed 80px labels (`w-20 shrink-0`), `SectionCard` pattern for bordered cards
- Full-width telemetry grid

### Phase 189 — Tab Consolidation 6→3 (EXECUTED)
- Consolidated from 6 tabs (Overview, Health, Transport, Twin/Commands, Security, Sensors/Data) to 3 tabs (Overview, Data, Manage)
- Created `DeviceManageTab.tsx` with 4 `ManageSection` areas: Connectivity, Control, Security, Subscription
- Moved health diagnostics to Overview tab
- Simplified KPI strip from 5→3 cards (Status, Open Alerts, Sensors)

### Phase 190 — Compact Modules (EXECUTED)
- Replaced per-slot card grid with compact single-table rows using `divide-y`

### Phase 191 — Collapse Empty Modules (EXECUTED)
- Wrapped expansion modules in collapsible `<details>` element
- Closed by default when 0 modules assigned, open when any assigned
- Summary: "▸ Expansion Modules — N slots, N assigned"
- Constrained to `max-w-2xl` (672px) to prevent full-width stretching

### Phase 192 — Slim Overview (PROMPTS WRITTEN, EXECUTED)
- Created `DeviceHealthStrip.tsx` — compact 5-stat boxes (Signal, Battery, CPU Temp, Memory, Uptime), no chart, no time range selector
- Removed from Overview: DeviceHealthPanel (signal chart + health details), Latest Telemetry card (12-metric grid), DeviceUptimePanel (uptime bar + 3 stats)
- Overview is now: DeviceInfoCard + DeviceHealthStrip + DeviceMapCard

## Current Device Detail Page Structure

```
PageHeader (device name, status badge, template badge, Edit/Create Job buttons)
├── KPI Strip (3 cards: Status, Open Alerts, Sensors)
└── Tabs
    ├── Overview
    │   ├── DeviceInfoCard (3-column: Identity | Hardware | Network+Location, Tags+Notes)
    │   ├── DeviceHealthStrip (5 compact stat boxes, latest values only)
    │   └── DeviceMapCard (if GPS coordinates exist)
    ├── Data
    │   ├── Expansion Modules (<details>, collapsed when empty, max-w-2xl)
    │   ├── Sensors table (CRUD)
    │   └── Telemetry charts (time-series, time range selector)
    └── Manage
        ├── Connectivity (DeviceTransportTab)
        ├── Control (DeviceTwinPanel + DeviceCommandPanel)
        ├── Security (DeviceApiTokensPanel + DeviceCertificatesTab)
        └── Subscription (DevicePlanPanel)
```

## Key Device Feature Files

| File | Purpose |
|------|---------|
| `DeviceDetailPage.tsx` | Main page — tabs, KPI strip, hooks |
| `DeviceInfoCard.tsx` | Identity property cards (fragment-based) |
| `DeviceHealthStrip.tsx` | Compact 5-metric health row (NEW) |
| `DeviceHealthPanel.tsx` | Full health panel with chart (still exists, no longer on Overview) |
| `DeviceUptimePanel.tsx` | Uptime bar + stats (still exists, no longer on Overview) |
| `DeviceMapCard.tsx` | Location map pin |
| `DeviceSensorsDataTab.tsx` | Data tab — modules, sensors, telemetry charts |
| `DeviceManageTab.tsx` | Manage tab — 4 sections (NEW) |
| `DeviceTransportTab.tsx` | Transport CRUD (~435 lines) |
| `DeviceTwinPanel.tsx` | Device twin key-value management |
| `DeviceCommandPanel.tsx` | Remote command dispatch |
| `DeviceApiTokensPanel.tsx` | API token management |
| `DeviceCertificatesTab.tsx` | X.509 certificate management |
| `DevicePlanPanel.tsx` | Subscription plan info + change dialog |
| `DeviceHealthTab.tsx` | Thin wrapper (composes HealthPanel + UptimePanel, unused) |
| `DeviceSecurityTab.tsx` | Thin wrapper (composes ApiTokens + Certificates, unused) |
| `DeviceTwinCommandsTab.tsx` | Thin wrapper (composes Twin + Command, unused) |
| `DeviceListPage.tsx` | Device list with health summary strip |

## Industry Research Findings (Completed)

Researched 9 IoT platforms: AWS IoT Core, Azure IoT Hub, Azure IoT Central, ThingsBoard, Losant, Particle, Balena, Hologram, Arduino IoT Cloud, Ubidots.

**Key finding:** NO platform puts telemetry charts on the device landing page. Universal pattern:
- Device page = identity + health snapshot + management
- Data visualization belongs on separate dashboards
- Historical data requires deliberate navigation (tabs, query builders, separate pages)
- Health/vitals shown as compact summary cards, not full charts

## Established Patterns

- **SectionCard:** `rounded-md border border-border p-3` with title header
- **Prop component:** `w-20 shrink-0` fixed-width labels to prevent justify-between stretching
- **ManageSection:** Icon + title + description + `border-b` separator for visual grouping
- **Collapsible details:** `<details>` with `[&::-webkit-details-marker]:hidden` + custom `▸` caret via `group-open:rotate-90`
- **MiniStat boxes:** Icon + label + large value + sub-value in bordered cards
- **Fragment return pattern:** Components return `<>` fragments, parent controls grid layout

## User Preferences

- Hates wasted whitespace — every pixel should earn its space
- Hates showing empty data — don't display sections with nothing to show
- Wants device management first, data visualization second
- Prefers compact, dense layouts over spacious ones
- Width-constrain lists that don't need full page width
- Collapse empty sections by default

## What's Next

The user may want to:
1. **Commit phases 188–192** — all changes are uncommitted
2. **Continue device detail refinement** — user said "we have so much more work to do on this"
3. **Structural redesign** — could move to Balena-style sidebar navigation where each concern gets its own full page (discussed but not pursued yet)
4. **Dead component cleanup** — `DeviceHealthTab.tsx`, `DeviceSecurityTab.tsx`, `DeviceTwinCommandsTab.tsx` are thin wrappers no longer used by any tab
5. **Phase 174 plan exists** in `.claude/plans/goofy-hatching-wind.md` — Fleet Navigation Restructure & Getting Started Guide (may already be implemented, needs verification)

## Cursor Prompt Locations

```
docs/cursor-prompts/phase188-device-detail-fix/     (000-002)
docs/cursor-prompts/phase189-device-detail-consolidation/ (000-003)
docs/cursor-prompts/phase190-compact-modules/        (000-002)
docs/cursor-prompts/phase191-collapse-empty-modules/ (000-002)
docs/cursor-prompts/phase192-slim-overview/          (000-002)
```
