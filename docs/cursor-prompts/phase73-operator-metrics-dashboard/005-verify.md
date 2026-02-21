# Prompt 005 — Verify Phase 73

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### API Client
- [ ] `SystemMetricsSnapshot` and `MetricsHistoryPoint` types in operator.ts
- [ ] `fetchSystemMetricsLatest()` and `fetchSystemMetricsHistory()` added

### Frontend Page
- [ ] SystemMetricsPage.tsx at /operator/system-metrics
- [ ] 4 chart panels (ingest rate, active alerts, device status, delivery failures)
- [ ] EChartWrapper used for rendering
- [ ] Auto-refresh every 30s with last-updated indicator

### Navigation
- [ ] `/operator/system-metrics` route registered
- [ ] "System Metrics" link in operator nav

### Unit Tests
- [ ] test_system_metrics_endpoints.py with 3 tests

## Report

Output PASS / FAIL per criterion.
