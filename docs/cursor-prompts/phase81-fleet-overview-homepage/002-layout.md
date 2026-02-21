# Prompt 002 — Full Homepage Layout Redesign

Read `frontend/src/features/dashboard/DashboardPage.tsx` and all widget files
in `frontend/src/features/dashboard/widgets/` fully before making changes.

## Replace DashboardPage layout with:

```
┌─────────────────────────────────────────────────────────┐
│  Fleet Overview                              [Last: 30s] │
├─────────────────────────────────────────────────────────┤
│  [ KPI Strip: 6 cards across full width ]               │
├─────────────────────────────────────────────────────────┤
│  [ Fleet Uptime Bar (full width, from Phase 78) ]       │
├──────────────────────────┬──────────────────────────────┤
│  Active Alerts           │  Device Status               │
│  (top 5 OPEN, severity   │  (online/offline/stale       │
│   sorted, with ack btn)  │   donut + count)             │
├──────────────────────────┼──────────────────────────────┤
│  Alert Trend (7d chart)  │  Recently Active Devices     │
│                          │  (last 5 by telemetry time)  │
└──────────────────────────┴──────────────────────────────┘
```

### Changes to make:

1. **Replace top section**: Remove current StatCardsWidget. Replace with `<FleetKpiStrip />`.

2. **Add Fleet Uptime Bar**: Import `UptimeSummaryWidget` from Phase 78 (already exists at
   `frontend/src/features/devices/UptimeSummaryWidget.tsx`). Place it below the KPI strip
   as a compact full-width bar.

3. **Active Alerts panel** (left column):
   - Show top 5 OPEN alerts sorted by severity (CRITICAL first)
   - Each row: severity badge, device name, alert type, time ago
   - "Acknowledge" button inline per row
   - "View all alerts →" link at bottom
   - Use existing `useAlerts` hook

4. **Device Status panel** (right column):
   - Reuse existing `DeviceStatusWidget` (donut chart)

5. **Alert Trend** (left, bottom row):
   - Reuse existing `AlertTrendWidget`

6. **Recently Active Devices** (right, bottom row):
   - New simple component: fetch GET /api/v2/devices?limit=5&sort=last_seen
   - Show: device name, status dot (green/yellow/red), last seen time ago
   - "View all devices →" link at bottom

### Page header changes:
- Title: "Fleet Overview"
- Subtitle: tenant name or "Real-time operational view"
- Add "Last updated: X seconds ago" timestamp top-right (updates every 30s)

## Acceptance Criteria
- [ ] DashboardPage uses new layout
- [ ] FleetKpiStrip renders at top
- [ ] UptimeSummaryWidget shown full-width
- [ ] Active Alerts panel shows top 5 with inline ack
- [ ] Recently Active Devices panel shows 5 devices with status dots
- [ ] All existing widgets (AlertTrend, DeviceStatus) preserved
- [ ] `npm run build` passes
