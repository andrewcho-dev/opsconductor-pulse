# Phase 26.5: Fix API Time Filter Passthrough

## Problem

- InfluxDB direct query: **0.7 seconds** (fast)
- API endpoint: **1-2 minutes** (slow)
- Frontend sends `start=2026-02-06T03:56:04.547Z` in request

The time filter isn't being passed from API to InfluxDB query.

## Step 1: Trace the code path

Check `services/ui_iot/routes/api_v2.py` — find the telemetry endpoint.

Look for where it calls the InfluxDB query function:

```python
@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    request: Request,
    limit: int = Query(500),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    # ... validation ...

    # THIS CALL - does it pass start and end?
    data = await fetch_device_telemetry_dynamic(
        http_client,
        tenant_id,
        device_id,
        start,  # <-- Is this being passed?
        end,    # <-- Is this being passed?
        limit
    )
```

**Check:** Is `start` actually passed to `fetch_device_telemetry_dynamic()`?

## Step 2: Check the function signature

In `services/ui_iot/db/influx_queries.py`, check `fetch_device_telemetry_dynamic()`:

```python
async def fetch_device_telemetry_dynamic(
    http_client,
    tenant_id: str,
    device_id: str,
    start: str | None = None,  # <-- Does this parameter exist?
    end: str | None = None,    # <-- Does this parameter exist?
    limit: int = 500
):
```

**If the function doesn't have start/end parameters, that's the bug.**

## Step 3: Check the SQL construction

Inside `fetch_device_telemetry_dynamic()`, look for where SQL is built:

```python
where_parts = [f"device_id = '{device_id}'"]

# THIS MUST EXIST:
if start:
    where_parts.append(f"time >= '{start}'")
if end:
    where_parts.append(f"time <= '{end}'")

sql = f"SELECT * FROM telemetry WHERE {' AND '.join(where_parts)} ORDER BY time DESC LIMIT {limit}"
```

**If the start/end conditions are missing, add them.**

## Likely Fix

The function call in api_v2.py might be missing the start/end arguments:

```python
# WRONG - missing start/end
data = await fetch_device_telemetry_dynamic(http_client, tenant_id, device_id, limit)

# CORRECT - pass start/end
data = await fetch_device_telemetry_dynamic(http_client, tenant_id, device_id, start, end, limit)
```

Or the function signature in influx_queries.py doesn't accept start/end.

## Apply Fix

1. Ensure `fetch_device_telemetry_dynamic()` accepts `start` and `end` parameters
2. Ensure the API endpoint passes `start` and `end` to the function
3. Ensure the SQL query includes the time filter when start/end are provided

## Verification

After fix:

```bash
docker compose restart ui
```

Load device detail page - should load in <2 seconds.

## Files

| File | Check/Fix |
|------|-----------|
| `services/ui_iot/routes/api_v2.py` | Ensure start/end passed to query function |
| `services/ui_iot/db/influx_queries.py` | Ensure function accepts and uses start/end |
