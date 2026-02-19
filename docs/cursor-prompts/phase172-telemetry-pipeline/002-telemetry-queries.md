# Task 2: Update Telemetry Queries to Use Semantic Keys

## Modify file: `services/ui_iot/routes/devices.py` (telemetry query endpoints)

### Overview

The telemetry chart and export endpoints currently query the `telemetry` hypertable using raw JSONB keys. Update them to use semantic metric keys from `device_sensors`.

### Find the telemetry query endpoints

Look for endpoints that query telemetry data, likely:
- `GET /devices/{device_id}/telemetry` — chart data
- `GET /devices/{device_id}/telemetry/export` — CSV export
- Or they may be in a separate file (check `routes/` for telemetry-related files)

Also check the `fetchTelemetryHistory` patterns called by the frontend.

### Update: Use device_sensors metric_key for queries

When the frontend requests telemetry for a specific metric, it should pass the semantic `metric_key` (e.g., "temperature"), not the raw JSONB key. The telemetry table stores data with semantic keys (after Phase 172 Task 1 normalization), so queries should use the semantic key directly.

For existing (pre-normalization) telemetry data that was stored with raw keys, the queries need to check both:

```sql
-- Query that handles both old (raw) and new (semantic) keys:
SELECT time, payload->>$2 AS value
FROM telemetry
WHERE tenant_id = $1 AND device_id = $3
  AND time >= $4 AND time <= $5
  AND (payload ? $2)  -- $2 is the semantic metric_key
ORDER BY time
```

For historical data where the raw key was different, users will need to re-ingest or accept the gap. This is a known limitation documented in the migration notes.

### Add unit conversion metadata

When returning telemetry data, include the unit and range from `device_sensors`:

```python
# Fetch sensor metadata
sensor = await conn.fetchrow(
    "SELECT unit, min_range, max_range, precision_digits FROM device_sensors WHERE tenant_id = $1 AND device_id = $2 AND metric_key = $3",
    tenant_id, device_id, metric_key,
)

# Include in response
return {
    "metric_key": metric_key,
    "unit": sensor["unit"] if sensor else None,
    "min_range": sensor["min_range"] if sensor else None,
    "max_range": sensor["max_range"] if sensor else None,
    "data": [{"time": row["time"].isoformat(), "value": row["value"]} for row in rows],
}
```

### Update: telemetry chart endpoint to list available metrics

Add or update an endpoint that lists available metrics for a device (used by the frontend to populate chart selectors):

```python
@router.get("/devices/{device_id}/telemetry/metrics")
async def list_device_telemetry_metrics(device_id: str, pool=Depends(get_db_pool)):
    """List available metrics for telemetry charts — sourced from device_sensors."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT metric_key, display_name, unit, min_range, max_range
            FROM device_sensors
            WHERE tenant_id = $1 AND device_id = $2 AND status = 'active'
            ORDER BY metric_key
            """,
            tenant_id, device_id,
        )
    return [dict(r) for r in rows]
```

### Update: last_value on device_sensors

When new telemetry arrives, update `device_sensors.last_value` and `last_seen_at`. This could be done:
1. In the ingest pipeline (after batch write)
2. Via a PostgreSQL trigger on the telemetry table
3. Via a periodic batch update

Option 1 is simplest — after the batch write in `ingest.py`, issue an UPDATE:

```python
# After successful batch write, update device_sensors last_value
for record in batch:
    for metric_key, value in record.payload.items():
        # Batch these updates for efficiency
        await conn.execute(
            """
            UPDATE device_sensors
            SET last_value = $1, last_seen_at = now()
            WHERE tenant_id = $2 AND device_id = $3 AND metric_key = $4
            """,
            value, record.tenant_id, record.device_id, metric_key,
        )
```

For performance, batch these updates using a single query with UNNEST or a CTE.

## Verification

1. Telemetry chart for a device shows data using semantic metric keys
2. Chart selector shows available metrics from device_sensors
3. Exported CSV uses semantic metric keys as column headers
4. device_sensors.last_value and last_seen_at are updated after telemetry ingest
