# Phase 25.5: Fix Gauge Data Not Displaying

## Problem

Fleet health gauges show zero/empty despite having seeded data.

## Investigation Steps

### 1. Check device_state table

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT tenant_id, device_id, status, state FROM device_state LIMIT 10"
```

Expected: `state` column should contain JSON like `{"battery_pct": 85, "temp_c": 22.5, "rssi_dbm": -65}`

If `state` is `{}` or null, the seed script didn't populate it correctly.

### 2. Check what API returns

```bash
curl -s "http://localhost:8080/api/v2/devices?limit=5" \
  -H "Cookie: pulse_session=<token>" | jq '.devices[0].state'
```

Or check browser DevTools → Network → look at `/api/v2/devices` response.

### 3. Check FleetHealthWidget logic

In `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx`, the widget reads:
```typescript
const state = device.state || {};
if (typeof state.battery_pct === "number") { ... }
```

Verify that:
- `useDevices()` returns devices with `.state` populated
- The state object has the expected keys

### 4. Possible Issues

**Issue A: Seed script didn't populate state**
- Check `scripts/seed_demo_data.py` → `seed_device_state()` function
- Ensure it inserts JSON into the `state` column

**Issue B: API doesn't return state field**
- Check `services/ui_iot/routes/api_v2.py` → `/devices` endpoint
- Ensure the query selects the `state` column
- Ensure the response includes `state` in the device object

**Issue C: Frontend type mismatch**
- Check `frontend/src/services/api/types.ts` → `Device` interface
- Ensure `state?: Record<string, number>` or similar is defined

### 5. Fix

Based on findings, either:
- Re-run seed script with corrected state data
- Fix API to return state field
- Fix frontend to read correct field name

## Quick Fix: Update device_state with metrics

If state is empty, run this to populate test data:

```sql
UPDATE device_state
SET state = jsonb_build_object(
  'battery_pct', 50 + random() * 50,
  'temp_c', 18 + random() * 10,
  'rssi_dbm', -80 + random() * 30,
  'humidity_pct', 40 + random() * 30
)
WHERE state = '{}'::jsonb OR state IS NULL;
```

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud -c "UPDATE device_state SET state = jsonb_build_object('battery_pct', 50 + random() * 50, 'temp_c', 18 + random() * 10, 'rssi_dbm', -80 + random() * 30, 'humidity_pct', 40 + random() * 30) WHERE state = '{}'::jsonb OR state IS NULL"
```

Then refresh the dashboard.

## Files to Check

| File | What to Check |
|------|---------------|
| `scripts/seed_demo_data.py` | `seed_device_state()` - is state populated? |
| `services/ui_iot/routes/api_v2.py` | `/devices` endpoint - is state returned? |
| `frontend/src/services/api/types.ts` | `Device` interface - is state typed? |
| `frontend/src/features/dashboard/widgets/FleetHealthWidget.tsx` | Reading `device.state.battery_pct` etc. |
