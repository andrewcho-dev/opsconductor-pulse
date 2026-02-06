# Phase 25.8: Fix Telemetry API Response

## Root Cause

The telemetry API endpoint at `services/ui_iot/routes/api_v2.py` returns a response **missing `tenant_id`**, but the frontend TypeScript interface expects it.

## Fix 1: Add tenant_id to API response

**File:** `services/ui_iot/routes/api_v2.py`

Find the `get_device_telemetry` endpoint (around line 317-350).

Change the return statement from:
```python
return JSONResponse(jsonable_encoder({
    "device_id": device_id,
    "telemetry": data,
    "count": len(data),
}))
```

To:
```python
return JSONResponse(jsonable_encoder({
    "tenant_id": tenant_id,  # ADD THIS
    "device_id": device_id,
    "telemetry": data,
    "count": len(data),
}))
```

## Fix 2: Verify /devices endpoint returns state

**File:** `services/ui_iot/routes/api_v2.py`

Find the `/devices` endpoint. Ensure the response includes the `state` field from `device_state` table.

The SQL query should SELECT state:
```python
SELECT tenant_id, device_id, site_id, status, last_seen_at, state FROM device_state WHERE ...
```

And the response mapping should include:
```python
{
    "device_id": row["device_id"],
    "tenant_id": row["tenant_id"],
    "site_id": row["site_id"],
    "status": row["status"],
    "last_seen_at": row["last_seen_at"].isoformat() if row["last_seen_at"] else None,
    "state": dict(row["state"]) if row["state"] else {},  # ENSURE THIS EXISTS
}
```

## Verification

```bash
# Restart UI
cd /home/opsconductor/simcloud/compose && docker compose restart ui

# Test telemetry endpoint (adjust device_id to one that exists)
# Check browser DevTools Network tab for /api/v2/devices/{id}/telemetry response
```

After fix:
- Device detail page should show telemetry charts
- Dashboard gauges should show fleet averages

## Files

| Action | File |
|--------|------|
| MODIFY | `services/ui_iot/routes/api_v2.py` |
