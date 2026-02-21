# Prompt 004 — Frontend: Fleet Uptime Widget

Read `frontend/src/features/devices/DeviceListPage.tsx` or `FleetSummaryWidget.tsx` to understand the fleet dashboard layout.

## Create `frontend/src/features/devices/UptimeSummaryWidget.tsx`

Displays:
- "Fleet Availability" heading
- Large % number (avg_uptime_pct) with UptimeBar
- Row: X Online | Y Offline | Z Total
- Auto-refreshes every 60 seconds

Fetches: GET /customer/fleet/uptime-summary

## Add API client function in `frontend/src/services/api/devices.ts`

```typescript
export async function getFleetUptimeSummary(): Promise<FleetUptimeSummary>

interface FleetUptimeSummary {
  total_devices: number;
  online: number;
  offline: number;
  avg_uptime_pct: number;
  as_of: string;
}
```

## Wire into Fleet / Dashboard page

Import and render `<UptimeSummaryWidget />` alongside existing fleet summary widgets.

## Acceptance Criteria
- [ ] UptimeSummaryWidget.tsx exists
- [ ] Shows avg_uptime_pct with UptimeBar
- [ ] Online/Offline counts displayed
- [ ] Auto-refreshes every 60s
- [ ] `npm run build` passes
