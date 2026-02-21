# Task 005 — Expand Device Detail Response

## File

Modify `services/ui_iot/routes/devices.py`

## Context

The existing `GET /api/v1/customer/devices/{device_id}` endpoint returns device registry fields. It should now also include:
- Sensor count and sensor list
- Connection info (if exists)
- Latest health snapshot (if exists)

## Changes

Find the device detail endpoint (likely `get_device` or similar, look for `@router.get("/devices/{device_id}")`). After fetching the device record from `device_registry`, add three additional queries inside the same `tenant_connection` block:

### 1. Fetch sensors

```python
sensor_rows = await conn.fetch(
    """
    SELECT sensor_id, metric_name, sensor_type, label, unit,
           min_range, max_range, precision_digits, status,
           auto_discovered, last_value, last_seen_at, created_at
    FROM sensors
    WHERE tenant_id = $1 AND device_id = $2
    ORDER BY metric_name
    """,
    tenant_id, device_id,
)
```

### 2. Fetch connection

```python
conn_row = await conn.fetchrow(
    """
    SELECT connection_type, carrier_name, plan_name, sim_iccid, sim_status,
           data_limit_mb, data_used_mb, data_used_updated_at,
           network_status, ip_address, last_network_attach
    FROM device_connections
    WHERE tenant_id = $1 AND device_id = $2
    """,
    tenant_id, device_id,
)
```

### 3. Fetch latest health

```python
health_row = await conn.fetchrow(
    """
    SELECT time, rssi, signal_quality, network_type, battery_pct, battery_voltage,
           power_source, cpu_temp_c, memory_used_pct, uptime_seconds, reboot_count,
           gps_lat, gps_lon, gps_fix
    FROM device_health_telemetry
    WHERE tenant_id = $1 AND device_id = $2
    ORDER BY time DESC LIMIT 1
    """,
    tenant_id, device_id,
)
```

### 4. Add to response

Add these to the returned dict:

```python
result["sensors"] = [dict(r) for r in sensor_rows]
result["sensor_count"] = len(sensor_rows)
result["sensor_limit"] = device_row["sensor_limit"] or 20  # from device_registry
result["connection"] = dict(conn_row) if conn_row else None
result["health"] = dict(health_row) if health_row else None
```

Ensure datetime fields are serialized to ISO format strings (check if existing code uses a serializer or manual `.isoformat()` calls — match the pattern).

## Also Update: Device List Endpoint

For the `GET /api/v1/customer/devices` list endpoint, add a `sensor_count` subquery to the main query so the device list shows how many sensors each device has:

```sql
SELECT dr.*,
       ds.status AS connection_status,
       ds.last_seen_at,
       (SELECT COUNT(*) FROM sensors s WHERE s.tenant_id = dr.tenant_id AND s.device_id = dr.device_id) AS sensor_count
FROM device_registry dr
LEFT JOIN device_state ds ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
WHERE dr.tenant_id = $1
...
```

This adds `sensor_count` to each device in the list response without a separate query.

## Notes

- These are read-only additions — no changes to existing response fields
- If `sensors`, `device_connections`, or `device_health_telemetry` tables don't exist yet (migration not yet run), the queries will error. Add `try/except` around these three new queries so the device detail endpoint still works even if migrations haven't been applied:

```python
try:
    sensor_rows = await conn.fetch(...)
except Exception:
    sensor_rows = []
```

This provides graceful degradation.

## Verification

```bash
cd services/ui_iot && python3 -m compileall -q routes/devices.py
```
