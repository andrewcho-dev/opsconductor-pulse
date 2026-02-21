# Prompt 004 — Verify Phase 57

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

- [ ] GET /customer/devices/{id}/telemetry/history exists
- [ ] Returns avg/min/max/count per time bucket
- [ ] 5 valid range values: 1h, 6h, 24h, 7d, 30d
- [ ] 400 on invalid range
- [ ] Time range selector in TelemetryChartsSection
- [ ] Chart fetches from history endpoint
- [ ] `fetchTelemetryHistory` in devices.ts
- [ ] 6 unit tests in test_telemetry_history.py

## Report

Output PASS / FAIL per criterion.
