# Phase 149 — Device/Sensor Separation: Database Foundation

## Overview

The system currently conflates devices (gateways) and sensors as a single entity in `device_registry`. This phase establishes the correct data model:

- **Device/Gateway** — The physical unit connecting to our platform. Has hardware identity, cellular connection, firmware. Billable unit.
- **Sensor** — A measurement point associated with a device. Has type, unit, range. Auto-discovered from telemetry. Not independently billed, but limited per device.
- **Platform Health Telemetry** — System-collected diagnostics about the device itself (RSSI, signal strength, battery, etc.). Always collected, not a customer sensor, not counted against sensor limits.

## Architecture

```
Device/Gateway (device_registry)
  │
  ├── Cellular Connection (device_connections)
  │     carrier, plan, data_limit, sim_status, apn, ip
  │
  ├── Platform Health (device_health_telemetry — TimescaleDB hypertable)
  │     rssi, signal_quality, battery_pct, cpu_temp, memory_pct,
  │     data_used_mb, uptime_seconds, reboot_count, error_count, gps
  │     Always collected. Not a sensor. Ops infrastructure data.
  │
  └── Customer Sensors (sensors)
        1..N per device (up to sensor_limit)
        Auto-discovered from telemetry metric keys
        temperature → 22.5°C, humidity → 65%, etc.
```

## Execution Order

1. `001-sensors-table.md` — Create `sensors` table with device FK
2. `002-device-connections-table.md` — Create `device_connections` table for cellular/connectivity data
3. `003-device-health-telemetry.md` — Create `device_health_telemetry` hypertable for platform diagnostics
4. `004-expand-device-identity.md` — Add missing hardware identity columns to `device_registry`
5. `005-sensor-limit-on-tiers.md` — Add `sensor_limit` to `device_tiers` and `device_registry`
6. `006-seed-data-overhaul.md` — Replace SENSOR-* seed data with proper gateway→sensor relationships

## Key Decisions

- **Migration numbers**: 099 through 104 (latest existing is 098)
- **Sensors are auto-discovered**: No upfront declaration. Created when new metric keys appear in telemetry.
- **Billing stays device-based**: Subscriptions count devices. `sensor_limit` per tier/device caps sensors per gateway.
- **Platform health is separate**: Stored in its own hypertable, not in `telemetry`, not a sensor.
- **Existing seed data is expendable**: User confirmed all current SENSOR-* records can be deleted.
- **Single cellular connection per device**: One-to-one relationship (device_connections).
