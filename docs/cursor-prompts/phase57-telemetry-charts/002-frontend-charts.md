# Prompt 002 — Frontend: Time Range Selector + History Chart

Read `frontend/src/features/devices/TelemetryChartsSection.tsx` fully.
Read `frontend/src/services/api/devices.ts` for existing API patterns.
Read `frontend/src/hooks/use-device-telemetry.ts` (or similar) to understand hook pattern.

## Add API Function

In `frontend/src/services/api/devices.ts`:

```typescript
export interface TelemetryHistoryPoint {
  time: string;
  avg: number | null;
  min: number | null;
  max: number | null;
  count: number;
}

export interface TelemetryHistoryResponse {
  device_id: string;
  metric: string;
  range: string;
  bucket_size: string;
  points: TelemetryHistoryPoint[];
}

export async function fetchTelemetryHistory(
  deviceId: string,
  metric: string,
  range: '1h' | '6h' | '24h' | '7d' | '30d'
): Promise<TelemetryHistoryResponse> {
  return apiFetch(`/customer/devices/${deviceId}/telemetry/history?metric=${encodeURIComponent(metric)}&range=${range}`);
}
```

## Update TelemetryChartsSection.tsx

Add a time range selector at the top of the section:

```
[ 1h ] [ 6h ] [ 24h ] [ 7d ] [ 30d ]
```

Default: `24h`.

When range changes:
1. Fetch history from new API endpoint for each displayed metric
2. Display avg as a solid line
3. If min/max available, shade the min-max band around the avg line (use existing chart library patterns — recharts, Chart.js, or whatever is already used)

Do NOT remove the live telemetry (recent data) — the history chart supplements it.

If the chart library already used supports area charts or `<Area>` / fill between, use that. If not, just render the avg line.

## Acceptance Criteria

- [ ] Time range selector (1h/6h/24h/7d/30d) visible in TelemetryChartsSection
- [ ] Selecting a range fetches from /telemetry/history
- [ ] Chart renders avg line
- [ ] No TypeScript errors
- [ ] `npm run build` passes
