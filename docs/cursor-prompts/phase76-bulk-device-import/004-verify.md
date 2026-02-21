# Prompt 004 — Verify Phase 76

## Step 1
```bash
pytest -m unit -v 2>&1 | tail -30
```

## Step 2
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] POST /customer/devices/import in customer.py
- [ ] 500-row and 1 MB limits enforced
- [ ] BulkImportPage.tsx with file picker + results table
- [ ] importDevicesCSV() in devices.ts
- [ ] Route /devices/import wired
- [ ] tests/unit/test_bulk_device_import.py with 5 tests

## Report
Output PASS / FAIL per criterion.
