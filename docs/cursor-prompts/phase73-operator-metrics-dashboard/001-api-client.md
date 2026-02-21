# Prompt 001 — API Client: Operator Metrics Functions

Read `frontend/src/services/api/operator.ts`.
Read `services/ui_iot/routes/operator.py` — find the `/operator/system/metrics*` endpoints to understand exact response shapes.

## Add to `frontend/src/services/api/operator.ts`

```typescript
export interface SystemMetricsSnapshot {
  timestamp: string;
  ingest_messages_total: number;
  ingest_queue_depth: number;
  evaluator_rules_evaluated_total: number;
  evaluator_alerts_created_total: number;
  evaluator_evaluation_errors_total: number;
  fleet_active_alerts: Record<string, number>;    // tenant_id → count
  fleet_devices_by_status: Record<string, Record<string, number>>;  // tenant_id → status → count
  delivery_jobs_failed_total: number;
  // include any other fields the API returns
}

export interface MetricsHistoryPoint {
  timestamp: string;
  [key: string]: number | string;
}

export async function fetchSystemMetricsLatest(): Promise<SystemMetricsSnapshot> {
  return apiFetch('/operator/system/metrics/latest');
}

export async function fetchSystemMetricsHistory(params?: {
  metric?: string;
  minutes?: number;
}): Promise<{ points: MetricsHistoryPoint[] }> {
  const qs = new URLSearchParams(params as any).toString();
  return apiFetch(`/operator/system/metrics/history${qs ? '?' + qs : ''}`);
}
```

Note: Read the actual endpoint response shapes from operator.py before finalizing these types. Adjust field names to match what the API actually returns.

## Acceptance Criteria

- [ ] `SystemMetricsSnapshot` and `MetricsHistoryPoint` types defined
- [ ] `fetchSystemMetricsLatest()` and `fetchSystemMetricsHistory()` functions added
- [ ] `npm run build` passes (TypeScript clean)
