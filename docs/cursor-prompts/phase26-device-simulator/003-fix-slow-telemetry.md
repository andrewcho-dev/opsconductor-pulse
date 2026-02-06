# Phase 26.3: Fix Slow Telemetry Loading

## Problem

Telemetry charts take 1-2 minutes to load. The InfluxDB query is likely scanning too much data.

## Investigation

### 1. Check the query being executed

Look at `services/ui_iot/db/influx_queries.py` — find `fetch_device_telemetry_dynamic()`.

Check:
- What time range is being queried?
- Is there a LIMIT?
- Is the query using indexes properly?

### 2. Check frontend time range

Look at `frontend/src/features/devices/TelemetryChartsSection.tsx`:
- What time range is being requested? (1h, 6h, 24h, 7d?)
- Default might be too wide

### 3. Check InfluxDB logs

```bash
docker compose logs iot-influxdb --tail=50
```

Look for slow query warnings.

## Likely Fixes

### Fix A: Default to shorter time range

In `frontend/src/features/devices/TelemetryChartsSection.tsx`, change default time range from 7d to 1h:

```typescript
const [timeRange, setTimeRange] = useState<TimeRange>("1h");  // Was "7d" or "24h"
```

### Fix B: Add proper time filter to query

In `services/ui_iot/db/influx_queries.py`, ensure the query has a time filter:

```python
# BAD: No time filter - scans everything
sql = f"SELECT * FROM telemetry WHERE device_id = '{device_id}' ORDER BY time DESC LIMIT {limit}"

# GOOD: Time filter reduces scan
sql = f"""
SELECT * FROM telemetry
WHERE device_id = '{device_id}'
  AND time >= now() - interval '{hours} hours'
ORDER BY time DESC
LIMIT {limit}
"""
```

### Fix C: Reduce default limit

The frontend might be requesting too many points. In `frontend/src/hooks/use-device-telemetry.ts` or similar:

```typescript
// Reduce from 500 to 120 points
const { data } = useTelemetry(deviceId, startTime, undefined, 120);
```

### Fix D: Add caching

If same device is queried repeatedly, cache the result for a few seconds.

## Quick Test

After making changes, time the query:

```bash
time curl -s "http://localhost:8080/api/v2/devices/warehouse-east-sim-01/telemetry?limit=100&start=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Cookie: pulse_session=<token>"
```

Should complete in under 1 second.

## Apply Fix

1. Change default time range to 1h in frontend
2. Ensure API passes time filter to InfluxDB
3. Rebuild frontend and restart UI

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

## Files

| File | Fix |
|------|-----|
| `frontend/src/features/devices/TelemetryChartsSection.tsx` | Default to 1h time range |
| `frontend/src/hooks/use-device-telemetry.ts` | Reduce limit to 120 |
| `services/ui_iot/db/influx_queries.py` | Ensure time filter in query |
