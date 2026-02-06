# Phase 26.4: Debug InfluxDB Query Performance

## Problem

6h time range takes 1-2 minutes to load. Time filter may not be reaching InfluxDB.

## Step 1: Add logging to see actual query

**File:** `services/ui_iot/db/influx_queries.py`

Find `fetch_device_telemetry_dynamic()` and add print statement:

```python
async def fetch_device_telemetry_dynamic(...):
    # ... build query ...

    print(f"[influx] QUERY: {sql}")  # ADD THIS
    print(f"[influx] device_id={device_id} start={start} end={end} limit={limit}")  # ADD THIS

    # ... execute query ...
```

Then restart UI and check logs:

```bash
docker compose restart ui
docker compose logs -f ui 2>&1 | grep influx
```

Load a device detail page and see what query is actually being sent.

## Step 2: Check if start/end are passed correctly

**File:** `services/ui_iot/routes/api_v2.py`

Find the telemetry endpoint and verify start/end are passed:

```python
@router.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(
    device_id: str,
    request: Request,
    limit: int = Query(500, ge=1, le=2000),
    start: str | None = Query(None),  # Should be ISO timestamp
    end: str | None = Query(None),
):
    print(f"[api] telemetry request: device={device_id} start={start} end={end} limit={limit}")
    # ...
```

## Step 3: Test query directly in InfluxDB

```bash
# Get into influxdb container
docker compose exec iot-influxdb sh

# Run query directly with time filter
influxdb3 query --database telemetry_tenant-a "
SELECT * FROM telemetry
WHERE device_id = 'warehouse-east-sim-01'
  AND time >= now() - interval '1 hour'
ORDER BY time DESC
LIMIT 50
"
```

If this is fast (<1s) but the API is slow, the problem is in how the API builds/sends the query.

## Step 4: Check if time filter is in WHERE clause

The query in `influx_queries.py` should look like:

```python
where_parts = [f"device_id = '{device_id}'"]
if start:
    where_parts.append(f"time >= '{start}'")
if end:
    where_parts.append(f"time <= '{end}'")
```

If `start` is None or empty string, the time filter won't be added.

## Step 5: Check frontend - what start time is sent?

**File:** `frontend/src/hooks/use-device-telemetry.ts`

Look for where `fetchTelemetry()` is called. Check what `start` value is passed:

```typescript
const start = getStartTime(timeRange);  // Should compute ISO timestamp
const { data } = useTelemetry(deviceId, start, undefined, limit);
```

If `start` is undefined or not computed correctly, no time filter is sent.

## Likely Root Cause

The frontend or API isn't sending/receiving the `start` parameter correctly, so InfluxDB scans all data.

## Quick Fix

In `influx_queries.py`, add a fallback time filter:

```python
# If no start time provided, default to last 6 hours
if not start:
    start = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
```

## Files

| File | Action |
|------|--------|
| `services/ui_iot/db/influx_queries.py` | Add logging, add fallback time filter |
| `services/ui_iot/routes/api_v2.py` | Add logging to see params |
