---
last-verified: 2026-02-19
sources:
  - services/evaluator_iot/evaluator.py
phases: [1, 23, 43, 88, 142, 160, 163, 165]
---

# evaluator

> Alert rule evaluation engine and device state tracker.

## Overview

`evaluator_iot` reads telemetry and fleet state from PostgreSQL/TimescaleDB and:

- Tracks device status (ONLINE/STALE/OFFLINE) using heartbeat timestamps.
- Generates NO_HEARTBEAT alerts when devices miss expected heartbeat windows.
- Evaluates customer-defined alert rules (threshold operators) and opens/closes alerts.

## Architecture

Core loop:

1. Poll devices/rules on `POLL_SECONDS`.
2. For each device/rule, evaluate threshold conditions (with optional duration/time-window handling).
3. Write alert state transitions to `fleet_alert` and update device status in `device_state`.

## Configuration

Environment variables read by the service:

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `iot-postgres` | PostgreSQL host (used when `DATABASE_URL` is not set). |
| `PG_PORT` | `5432` | PostgreSQL port. |
| `PG_DB` | `iotcloud` | Database name. |
| `PG_USER` | `iot` | Database user. |
| `PG_PASS` | `iot_dev` | Database password. |
| `DATABASE_URL` | empty | Optional DSN; when set, preferred over `PG_*`. |
| `NOTIFY_DATABASE_URL` | falls back to `DATABASE_URL` | DSN used for LISTEN/NOTIFY paths (when enabled). |
| `PG_POOL_MIN` | `2` | DB pool minimum connections. |
| `PG_POOL_MAX` | `10` | DB pool maximum connections. |
| `POLL_SECONDS` | `5` | Main evaluation loop interval. |
| `HEARTBEAT_STALE_SECONDS` | `30` | Heartbeat staleness threshold. |
| `FALLBACK_POLL_SECONDS` | `POLL_SECONDS` | Fallback poll interval for degraded conditions. |
| `DEBOUNCE_SECONDS` | `0.5` | Debounce for notify-driven wakeups. |

## Health & Metrics

- Health endpoint: `GET http://<container>:8080/health`
- Prometheus metrics are exported by the service (counters for evaluations/alerts/errors).

## Dependencies

- PostgreSQL + TimescaleDB (telemetry + fleet tables)
- PgBouncer (in compose) for pooling

## Troubleshooting

- Evaluator falling behind: increase `POLL_SECONDS`, reduce rule/device cardinality, or scale the service.
- Heartbeat alerts too noisy: tune `HEARTBEAT_STALE_SECONDS` and device heartbeat cadence.
- DB timeouts: verify PgBouncer pool sizing and DB health.

## See Also

- [System Overview](../architecture/overview.md)
- [Alerting](../features/alerting.md)
- [Database](../operations/database.md)

