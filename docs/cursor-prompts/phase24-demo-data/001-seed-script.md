# Phase 24.1: Create Demo Data Seed Script

## Task

Create `scripts/seed_demo_data.py` that populates PostgreSQL and InfluxDB with realistic demo data.

## Requirements

### Environment Variables
```python
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8181")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "influx-dev-token-change-me")
```

### Demo Data Structure

**Tenants:**
- `tenant-a` (matches Keycloak customer1)
- `tenant-b` (matches Keycloak customer2)

**Sites per tenant:**
```python
SITES = {
    "tenant-a": ["warehouse-east", "warehouse-west", "cold-storage-1"],
    "tenant-b": ["factory-floor", "loading-dock", "office-hvac"],
}
```

**Devices per site:** 5 devices each (15 per tenant, 30 total)

**Device naming:** `{site}-sensor-{01-05}` (e.g., `warehouse-east-sensor-01`)

### PostgreSQL Tables to Populate

#### 1. device_registry
```python
# For each device:
{
    "tenant_id": tenant_id,
    "device_id": device_id,
    "site_id": site_id,
    "status": "ACTIVE",
    "provision_token_hash": hashlib.sha256(f"tok-{device_id}".encode()).hexdigest(),
    "fw_version": random.choice(["1.0.0", "1.1.0", "1.2.3", "2.0.0"]),
    "metadata": {"model": random.choice(["DHT22", "BME280", "SHT31"]), "installed": "2024-01-15"}
}
```

#### 2. device_state
```python
# Most devices ONLINE, 2-3 per tenant STALE
{
    "tenant_id": tenant_id,
    "device_id": device_id,
    "site_id": site_id,
    "status": "ONLINE" or "STALE",
    "last_heartbeat_at": now or now - 2 minutes (if STALE),
    "last_telemetry_at": now or now - 2 minutes (if STALE),
    "last_seen_at": now or now - 2 minutes (if STALE),
    "state": {
        "battery_pct": random 60-100 (or 15-25 for low battery devices),
        "temp_c": random 18-26 (or 32-38 for high temp devices),
        "rssi_dbm": random -70 to -50 (or -95 to -85 for weak signal),
        "humidity_pct": random 40-60
    }
}
```

#### 3. alert_rules (5 per tenant)
```python
RULES_TEMPLATE = [
    {"name": "Low Battery Warning", "metric_name": "battery_pct", "operator": "LT", "threshold": 25.0, "severity": 2, "description": "Battery below 25%"},
    {"name": "Critical Battery", "metric_name": "battery_pct", "operator": "LT", "threshold": 10.0, "severity": 1, "description": "Battery critically low"},
    {"name": "High Temperature", "metric_name": "temp_c", "operator": "GT", "threshold": 35.0, "severity": 3, "description": "Temperature exceeds 35°C"},
    {"name": "Freezing Alert", "metric_name": "temp_c", "operator": "LT", "threshold": 2.0, "severity": 2, "description": "Temperature near freezing"},
    {"name": "Weak Signal", "metric_name": "rssi_dbm", "operator": "LT", "threshold": -85.0, "severity": 4, "description": "Signal strength degraded"},
]
```

#### 4. fleet_alert (for STALE devices and threshold violations)
```python
# For each STALE device:
{
    "tenant_id": tenant_id,
    "site_id": site_id,
    "device_id": device_id,
    "alert_type": "NO_HEARTBEAT",
    "fingerprint": f"NO_HEARTBEAT:{device_id}",
    "status": "OPEN",
    "severity": 4,
    "confidence": 0.9,
    "summary": f"Device {device_id} has not sent heartbeat",
    "details": {"last_heartbeat_at": "..."}
}

# For devices with low battery (state.battery_pct < 25):
{
    "alert_type": "THRESHOLD",
    "fingerprint": f"RULE:{rule_id}:{device_id}",
    "severity": 2,
    "summary": f"Low Battery Warning: {device_id} battery at {battery}%",
    "details": {"rule_id": "...", "rule_name": "Low Battery Warning", "metric_name": "battery_pct", "metric_value": battery, "operator": "LT", "threshold": 25.0}
}
```

### InfluxDB Data

#### Create databases
```
telemetry_tenant-a
telemetry_tenant-b
```

#### Generate 7 days of telemetry

For each device, generate data points every 5 minutes for 7 days (2016 points per device).

**Line protocol format:**
```
telemetry,device_id={device_id},site_id={site_id} seq={seq}i,battery_pct={battery},temp_c={temp},rssi_dbm={rssi}i,humidity_pct={humidity} {timestamp_ns}
```

**Data patterns:**
- `battery_pct`: Start at 100, slowly drain 0.5% per hour, reset to 100 randomly (simulates recharge)
- `temp_c`: Base 22 + sin wave (daily cycle) + random noise ±2
- `rssi_dbm`: Base -65 + random walk ±5, clamp to -100 to -30
- `humidity_pct`: Base 50 + random ±10

**Heartbeats:** Generate matching heartbeat data
```
heartbeat,device_id={device_id},site_id={site_id} seq={seq}i {timestamp_ns}
```

## Script Structure

```python
#!/usr/bin/env python3
"""Seed demo data for Pulse IoT platform."""

import asyncio
import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx


async def main():
    print("Connecting to PostgreSQL...")
    pool = await asyncpg.create_pool(...)

    print("Seeding device_registry...")
    await seed_device_registry(pool)

    print("Seeding device_state...")
    await seed_device_state(pool)

    print("Seeding alert_rules...")
    await seed_alert_rules(pool)

    print("Seeding fleet_alert...")
    await seed_fleet_alerts(pool)

    print("Seeding InfluxDB telemetry (7 days)...")
    await seed_influxdb()

    print("Done!")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Idempotency

Use `ON CONFLICT DO NOTHING` or check existence before insert. Script should be safe to run multiple times.

## Verification

```bash
# Run locally (with port-forwarding or direct connection)
cd /home/opsconductor/simcloud
python3 scripts/seed_demo_data.py

# Or inside container network
docker compose exec -T postgres psql -U iot -d iotcloud -c "SELECT COUNT(*) FROM device_registry"
docker compose exec -T postgres psql -U iot -d iotcloud -c "SELECT COUNT(*) FROM alert_rules"
```

## Files

| Action | File |
|--------|------|
| CREATE | `scripts/seed_demo_data.py` |
