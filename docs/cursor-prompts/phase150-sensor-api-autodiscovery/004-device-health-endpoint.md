# Task 004 — Device Health Telemetry Endpoint

## File

Add to `services/ui_iot/routes/sensors.py`

## Endpoint

### `GET /api/v1/customer/devices/{device_id}/health`

Query platform health telemetry for a device. Returns time-series diagnostic data (signal, battery, CPU, data usage, GPS).

**Query params:**
- `range` (optional, default "24h") — Time range: "1h", "6h", "24h", "7d", "30d"
- `limit` (optional, default 100, max 1000) — Max data points to return

**Response:**
```json
{
  "device_id": "GW-001",
  "range": "24h",
  "data_points": [
    {
      "time": "2026-02-18T10:30:00Z",
      "rssi": -67,
      "signal_quality": 78,
      "network_type": "LTE-M",
      "battery_pct": null,
      "battery_voltage": null,
      "power_source": "line",
      "cpu_temp_c": 42.3,
      "memory_used_pct": 34,
      "storage_used_pct": 18,
      "uptime_seconds": 2592000,
      "reboot_count": 2,
      "data_tx_bytes": 524288,
      "data_rx_bytes": 1048576,
      "gps_lat": 41.8781,
      "gps_lon": -87.6298,
      "gps_fix": true
    }
  ],
  "total": 1,
  "latest": { ... }  // Most recent data point (convenience field)
}
```

**Logic:**
1. Verify device exists
2. Parse range to interval: `{"1h": "1 hour", "6h": "6 hours", "24h": "1 day", "7d": "7 days", "30d": "30 days"}`
3. Query `device_health_telemetry`:
```sql
SELECT time, rssi, rsrp, rsrq, sinr, signal_quality, network_type, cell_id,
       battery_pct, battery_voltage, power_source, charging,
       cpu_temp_c, memory_used_pct, storage_used_pct, uptime_seconds, reboot_count, error_count,
       data_tx_bytes, data_rx_bytes, data_session_bytes,
       gps_lat, gps_lon, gps_accuracy_m, gps_fix
FROM device_health_telemetry
WHERE tenant_id = $1 AND device_id = $2 AND time > now() - $3::INTERVAL
ORDER BY time DESC
LIMIT $4
```
4. The `latest` field is just `data_points[0]` (most recent)

### `GET /api/v1/customer/devices/{device_id}/health/latest`

Shortcut for just the most recent health data point.

**Response:** Single data point object (not wrapped in array).

**Logic:**
```sql
SELECT * FROM device_health_telemetry
WHERE tenant_id = $1 AND device_id = $2
ORDER BY time DESC LIMIT 1
```

## Notes

- Use `dict(row)` on asyncpg records, then serialize timestamps with `.isoformat()`
- The `time` column is TIMESTAMPTZ — asyncpg returns it as a `datetime` object
- NULL values should be preserved in the response (not omitted), so the frontend knows which fields the device reports
- The hypertable indexes on `(tenant_id, device_id, time DESC)` make these queries efficient

## Verification

```bash
cd services/ui_iot && python3 -c "from routes.sensors import router; print([r.path for r in router.routes if 'health' in r.path])"
```
