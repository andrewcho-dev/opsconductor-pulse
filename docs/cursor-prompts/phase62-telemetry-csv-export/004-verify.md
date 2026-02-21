# Prompt 004 — Verify Phase 62

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

- [ ] GET /customer/devices/{id}/telemetry/export exists in customer.py
- [ ] Returns text/csv with Content-Disposition
- [ ] JSONB metric keys flattened to columns
- [ ] Empty data returns headers-only CSV
- [ ] Range validation (400 on invalid)
- [ ] Limit cap at 10000
- [ ] "Download CSV" button in TelemetryChartsSection
- [ ] 7 unit tests in test_telemetry_export.py

## Report

Output PASS / FAIL per criterion.
