# Prompt 002 — Backend: Update `GET /customer/devices` Endpoint

## Context

`fetch_devices_v2()` now accepts filter params and returns `{devices, total}`. The `GET /customer/devices` route in `services/ui_iot/routes/customer.py` must be updated to:
1. Accept the new query parameters
2. Pass them to `fetch_devices_v2()`
3. Return `total` in the response
4. Add a new `GET /customer/devices/summary` endpoint for the fleet summary widget

## Your Task

**Read `services/ui_iot/routes/customer.py`** — find the `list_devices` endpoint and the existing `Query` parameter pattern.

### Update `list_devices`

New signature:

```python
@router.get("/devices")
async def list_devices(
    limit: int = Query(100, ge=1, le=1000),   # increase max from 500 to 1000
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),          # ONLINE | STALE | OFFLINE
    tags: str | None = Query(None),            # comma-separated: "rack-a,rack-b"
    q: str | None = Query(None, max_length=100),
    site_id: str | None = Query(None),
    pool=Depends(get_db_pool),
):
```

**Validate `status`** — only accept known values:
```python
VALID_DEVICE_STATUSES = {"ONLINE", "STALE", "OFFLINE"}
if status is not None and status.upper() not in VALID_DEVICE_STATUSES:
    raise HTTPException(status_code=400, detail="Invalid status value")
status = status.upper() if status else None
```

**Parse `tags`** — split comma-separated string:
```python
tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
```

**Call updated `fetch_devices_v2()`:**
```python
result = await fetch_devices_v2(
    conn, tenant_id,
    limit=limit, offset=offset,
    status=status, tags=tag_list, q=q, site_id=site_id
)
```

**Return `total` in response:**
```python
return {
    "tenant_id": tenant_id,
    "devices": result["devices"],
    "total": result["total"],
    "limit": limit,
    "offset": offset,
}
```

### Add `GET /customer/devices/summary`

```python
@router.get("/devices/summary")
async def get_fleet_summary(pool=Depends(get_db_pool)):
    """Fleet status summary: counts of ONLINE/STALE/OFFLINE devices."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            summary = await fetch_fleet_summary(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch fleet summary")
        raise HTTPException(status_code=500, detail="Internal server error")
    return summary
```

Import `fetch_fleet_summary` from `services/ui_iot/db/queries.py`.

**Note on route ordering:** FastAPI matches routes in order. If `/devices/summary` is defined AFTER `/devices/{device_id}`, it will be caught by the `{device_id}` param route. Ensure `/devices/summary` is defined BEFORE `/devices/{device_id}` in the router.

## Acceptance Criteria

- [ ] `GET /customer/devices?status=ONLINE` returns only ONLINE devices
- [ ] `GET /customer/devices?tags=rack-a,rack-b` returns devices with BOTH tags
- [ ] `GET /customer/devices?q=sensor-0` returns devices matching the search
- [ ] `GET /customer/devices` response includes `"total": N`
- [ ] `GET /customer/devices/summary` returns `{ONLINE, STALE, OFFLINE, total}`
- [ ] Invalid `status` returns 400
- [ ] `pytest -m unit -v` passes
