# Prompt 002 — SystemMetricsPage with ECharts

Read `frontend/src/lib/charts/EChartWrapper.tsx` fully — understand the props interface and how to pass ECharts `option` objects.
Read `frontend/src/lib/charts/theme.ts` for dark/light theme definitions.
Read `frontend/src/features/operator/TenantDetailPage.tsx` for page layout patterns.
Read `frontend/src/services/api/operator.ts` (just updated).

## Create `frontend/src/features/operator/SystemMetricsPage.tsx`

### Page Layout

Header: "System Metrics" with "Last updated: {timestamp}" and "Auto-refreshing every 30s" indicator.

Four chart panels in a 2×2 grid (or responsive stack on mobile):

**Panel 1: Ingest Rate** (line chart)
- X axis: time (last 60 minutes)
- Y axis: messages/min
- Uses `fetchSystemMetricsHistory({ metric: 'ingest_messages_total', minutes: 60 })`
- Show as step-line or smooth line

**Panel 2: Active Alerts by Tenant** (bar chart)
- X axis: tenant_id (truncated)
- Y axis: alert count
- Uses current snapshot `fleet_active_alerts` from `fetchSystemMetricsLatest()`
- Colored bars (red for >0, green for 0)

**Panel 3: Device Status Breakdown** (stacked bar or pie)
- Shows ONLINE/STALE/OFFLINE counts aggregated across all tenants
- Uses `fleet_devices_by_status` from latest snapshot
- Colors: green=ONLINE, yellow=STALE, red=OFFLINE

**Panel 4: Delivery Failures** (line or number card)
- Single large number: total failed delivery jobs
- Subtitle: "Since service start"
- From `delivery_jobs_failed_total` in latest snapshot

### Auto-Refresh

```typescript
useEffect(() => {
  fetchData();
  const interval = setInterval(fetchData, 30_000);
  return () => clearInterval(interval);
}, []);
```

### ECharts Usage Pattern

Follow the existing `EChartWrapper` props interface. Pass ECharts `option` objects.
For time-series, use `{ type: 'time' }` for x-axis with ISO timestamp strings.

## Acceptance Criteria

- [ ] SystemMetricsPage.tsx exists with 4 chart panels
- [ ] Uses EChartWrapper for rendering
- [ ] Auto-refreshes every 30s
- [ ] Shows last-updated timestamp
- [ ] `npm run build` passes
