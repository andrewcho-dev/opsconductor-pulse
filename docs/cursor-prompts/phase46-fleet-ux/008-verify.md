# Prompt 008 — Verify: Full Suite + Manual Smoke Test

## Step 1: Unit tests
```bash
pytest -m unit -v 2>&1 | tail -5
```
Expected: 0 failures.

## Step 2: Frontend tests + build
```bash
cd frontend && npm run test -- --run 2>&1 | tail -5
cd frontend && npm run build 2>&1 | tail -5
```
Expected: all pass, clean build.

## Step 3: API smoke tests (with running stack)

```bash
TOKEN="..."  # valid customer JWT

# 1. Unfiltered — confirm total is returned
curl -s "http://localhost/api/v2/devices?limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '{total, count: (.devices|length)}'

# 2. Status filter
curl -s "http://localhost/api/v2/devices?status=ONLINE&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '{total, count: (.devices|length)}'

# 3. Search
curl -s "http://localhost/api/v2/devices?q=sensor&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '{total, first_device: .devices[0].device_id}'

# 4. Tag filter (use a tag that exists in your data)
curl -s "http://localhost/api/v2/devices?tags=temperature&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '{total}'

# 5. Fleet summary
curl -s "http://localhost/customer/devices/summary" \
  -H "Authorization: Bearer $TOKEN" | jq .

# 6. Invalid status — expect 400
curl -s "http://localhost/api/v2/devices?status=DEAD" \
  -H "Authorization: Bearer $TOKEN" | jq .status
```

## Step 4: Manual UI check

Open the device list page in browser and confirm:
- [ ] Fleet summary widget visible at top with ONLINE/STALE/OFFLINE/Total counts
- [ ] Search input present — type a partial device ID and table updates
- [ ] Status filter buttons present — clicking "Online" filters the table
- [ ] Pagination shows "X–Y of Z total"
- [ ] Tag filter still works (existing functionality preserved)
- [ ] "Group by tag" toggle shows devices organized under tag headings
- [ ] Grouped view is collapsible per tag

## Step 5: Report

All checks must be green before Phase 47.

## Gate for Phase 47

Phase 47 is PostgreSQL LISTEN/NOTIFY — replacing the 5s polling loops with event-driven notifications.
This cuts end-to-end alert latency from ~13s to ~2s with minimal architecture change.
