# Phase 25.7: Fix API Not Returning State Field

## Problem

`device_state.state` is populated in Postgres, but dashboard gauges show zero. The API likely isn't returning the `state` field.

## Investigation

### 1. Check the /devices endpoint

Look at `services/ui_iot/routes/api_v2.py` — find the `/devices` endpoint.

Check:
- Does the SQL query SELECT the `state` column?
- Does the response include `state` in the device dict?

### 2. Check the Device type

Look at `frontend/src/services/api/types.ts` — find the `Device` interface.

Check:
- Is `state` defined? Should be: `state?: Record<string, number>;`

### 3. Check browser DevTools

In the browser, open DevTools → Network → filter for `devices`.
Look at the actual JSON response. Does each device have a `state` field?

## Likely Fix

The API endpoint probably doesn't include `state` in the response.

### Fix in api_v2.py

Find the `/devices` endpoint and ensure:

1. The query includes `state`:
```python
SELECT device_id, tenant_id, site_id, status, last_seen_at, state FROM device_state ...
```

2. The response mapping includes state:
```python
{
    "device_id": row["device_id"],
    "tenant_id": row["tenant_id"],
    "site_id": row["site_id"],
    "status": row["status"],
    "last_seen_at": row["last_seen_at"].isoformat() if row["last_seen_at"] else None,
    "state": dict(row["state"]) if row["state"] else {},  # <-- ADD THIS
}
```

### Fix in types.ts

Ensure Device interface has:
```typescript
export interface Device {
  device_id: string;
  tenant_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
  state?: Record<string, number>;  // <-- ENSURE THIS EXISTS
}
```

## Verification

After fix:

```bash
# Rebuild and restart
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Check API directly (from host, adjust port if needed)
curl -s "http://localhost:8080/api/v2/devices?limit=2" | jq '.devices[0].state'
```

Should return: `{"battery_pct": 58, "temp_c": 22.2, ...}`

Then refresh dashboard — gauges should show values.

## Files to Fix

| File | Fix |
|------|-----|
| `services/ui_iot/routes/api_v2.py` | Add `state` to SELECT and response |
| `frontend/src/services/api/types.ts` | Add `state` to Device interface |
