# Phase 25.6: Diagnose Missing Metric Data

## Problem

Dashboard gauges and device metrics show "no data" or zero values.

## Run These Diagnostics

### 1. Check device_state table

```bash
cd /home/opsconductor/simcloud/compose && docker compose exec iot-postgres psql -U iot -d iotcloud -c "SELECT device_id, status, state FROM device_state LIMIT 10"
```

**Expected:** state column should have JSON like `{"battery_pct": 85, "temp_c": 22}`

**If state is `{}` or empty:** The seed script didn't populate state. Fix below.

### 2. Check InfluxDB telemetry

```bash
cd /home/opsconductor/simcloud/compose && docker compose exec iot-influxdb influxdb3 query --database telemetry_tenant-a "SELECT * FROM telemetry ORDER BY time DESC LIMIT 5"
```

**Expected:** Rows with device_id, battery_pct, temp_c, etc.

**If empty or error:** Seed script didn't write to InfluxDB. Fix below.

### 3. Check API response

```bash
cd /home/opsconductor/simcloud/compose && docker compose exec ui curl -s "http://localhost:8080/api/v2/devices?limit=3" | python3 -m json.tool | head -50
```

**Expected:** Devices with `"state": {"battery_pct": ...}` field.

## Fixes Based on Findings

### Fix A: Populate device_state.state

If state is empty `{}`:

```bash
docker compose exec iot-postgres psql -U iot -d iotcloud -c "
UPDATE device_state
SET state = jsonb_build_object(
  'battery_pct', 50 + (random() * 50)::int,
  'temp_c', round((18 + random() * 10)::numeric, 1),
  'rssi_dbm', -80 + (random() * 30)::int,
  'humidity_pct', round((40 + random() * 30)::numeric, 1)
)
WHERE state = '{}'::jsonb OR state IS NULL;
"
```

### Fix B: Re-run seed script

If both Postgres and InfluxDB are empty:

```bash
cd /home/opsconductor/simcloud/compose && docker compose --profile seed run --rm seed
```

### Fix C: Check seed script for bugs

Review `scripts/seed_demo_data.py`:
- Does `seed_device_state()` insert state JSON?
- Does `seed_influxdb()` write line protocol correctly?

## After Fix

Refresh dashboard at `https://<host>/app/` and verify gauges show data.

## Report Findings

After running diagnostics, report:
1. What device_state.state contains
2. What InfluxDB query returns
3. What API returns for device state
