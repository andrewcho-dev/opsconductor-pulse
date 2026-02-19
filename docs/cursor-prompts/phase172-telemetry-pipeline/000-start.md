# Phase 172 — Telemetry Pipeline & Metric Normalization

## Goal

Update the ingest pipeline to translate raw firmware telemetry keys to semantic metric names using `metric_key_map` from `device_modules`. Update telemetry queries to use semantic keys from `device_sensors`. Mark the legacy Metrics page as deprecated.

## Prerequisites

- Phase 167 complete (device_modules with metric_key_map exists)
- Phase 169 complete (device_sensors table populated, new sensor endpoints)
- Ingest pipeline: `services/ingest_iot/ingest.py` (NATS JetStream consumer)
- HTTP ingest: `services/ui_iot/routes/ingest.py`

## Architecture

```
Raw telemetry message:
  { "port_3_temp": 23.5, "port_3_humidity": 45.2, "battery": 85 }

  ↓ metric_key_map lookup (per device_module)
  ↓ metric_key_map: { "port_3_temp": "temperature", "port_3_humidity": "humidity" }

Normalized telemetry:
  { "temperature": 23.5, "humidity": 45.2, "battery": 85 }
  (unmapped keys like "battery" pass through unchanged)
```

The normalization happens **before** batch write to TimescaleDB. The stored telemetry uses semantic keys, making queries consistent regardless of firmware version or port assignment.

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-ingest-normalization.md` | metric_key_map lookup + translation in ingest pipeline |
| 2 | `002-telemetry-queries.md` | Update telemetry chart/export queries to use semantic keys |
| 3 | `003-metrics-deprecation.md` | Deprecation notices on MetricsPage |
| 4 | `004-update-docs.md` | Update ingest, monitoring, architecture docs |

## Verification

```bash
# Send test telemetry with raw keys
curl -X POST http://localhost:8080/ingest/v1/tenant/test-tenant/device/gw-001/telemetry \
  -H "Content-Type: application/json" \
  -d '{"port_3_temp": 23.5, "battery": 85}'

# Verify stored with semantic keys
psql -c "SELECT payload FROM telemetry WHERE device_id = 'gw-001' ORDER BY time DESC LIMIT 1;"
# Should show: {"temperature": 23.5, "battery": 85}
```
