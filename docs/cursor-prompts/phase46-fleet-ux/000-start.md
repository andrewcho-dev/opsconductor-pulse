# Phase 46: Fleet UX — Server-Side Search, Filtering, and Fleet Aggregation

## What Exists Today

- `GET /customer/devices` returns all devices, paginated (limit/offset). No filter params.
- Tag filtering is 100% client-side: React fetches ALL devices, then filters in memory.
- No total count returned — pagination UI cannot show "of N total".
- No text search — no way to find a device by ID, model, serial number, or address.
- No fleet-level status summary — no "X online, Y stale, Z offline" at the top of the page.
- Tags used for filtering only — no grouping/organization view.

## What This Phase Adds

1. **Server-side filtering** — `GET /customer/devices?status=ONLINE&tags=rack-a,rack-b&q=sensor-0`
2. **Server-side total count** — response includes `total` so pagination can show "1-100 of 847"
3. **Full-text / prefix search** — search by `device_id`, `model`, `serial_number`, `site_id`, `address`
4. **Fleet status summary widget** — counts of ONLINE / STALE / OFFLINE devices at top of page
5. **Tag grouping view** — "Group by tag" toggle shows devices organized under their tags

## Key Files

### Backend
- `services/ui_iot/db/queries.py` — `fetch_devices_v2()` (add filter params + total count)
- `services/ui_iot/routes/customer.py` — `GET /customer/devices` endpoint (add Query params)

### Frontend
- `frontend/src/features/devices/DeviceListPage.tsx` — main page (server-side filter wiring)
- `frontend/src/features/devices/DeviceFilters.tsx` — add search input + status filter
- `frontend/src/features/devices/DeviceTable.tsx` — add total count display
- `frontend/src/services/api/devices.ts` — update `fetchDevices()` to pass filter params
- `frontend/src/hooks/use-devices.ts` — update query key + params

## Execution Order

| Prompt | Description | Priority |
|--------|-------------|----------|
| 001 | Backend: add filter params + total count to `fetch_devices_v2()` | CRITICAL |
| 002 | Backend: update `GET /customer/devices` endpoint to accept filter params | CRITICAL |
| 003 | Frontend: update API client + hook to pass filter params | HIGH |
| 004 | Frontend: add search input + status filter to `DeviceFilters.tsx` | HIGH |
| 005 | Frontend: fleet status summary widget | HIGH |
| 006 | Frontend: tag grouping view toggle | MEDIUM |
| 007 | Unit tests for backend filter query + frontend components | HIGH |
| 008 | Verify: full suite + manual smoke test | CRITICAL |

## Verification

```bash
# Backend filter works
curl "http://localhost/api/v2/devices?status=ONLINE&q=sensor&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '{total: .total, count: (.devices | length)}'

# Unit tests
pytest -m unit -v 2>&1 | tail -5

# Frontend build
cd frontend && npm run build && npm run test -- --run
```
