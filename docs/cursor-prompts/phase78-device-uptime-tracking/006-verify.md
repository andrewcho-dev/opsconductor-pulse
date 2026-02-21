# Prompt 006 — Verify Phase 78

## Step 1
```bash
pytest -m unit -v 2>&1 | tail -30
```

## Step 2
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] GET /customer/devices/{id}/uptime in customer.py
- [ ] GET /customer/fleet/uptime-summary in customer.py
- [ ] UptimeBar.tsx with color thresholds
- [ ] DeviceUptimePanel.tsx with range selector
- [ ] UptimeSummaryWidget.tsx with auto-refresh
- [ ] API client: getDeviceUptime, getFleetUptimeSummary
- [ ] tests/unit/test_device_uptime.py with 6 tests

## Report
Output PASS / FAIL per criterion.
