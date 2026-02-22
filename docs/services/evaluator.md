---
last-verified: 2026-02-22
sources:
  - services/evaluator_iot/evaluator.py
  - compose/docker-compose.yml
phases: [1, 23, 43, 88, 142, 160, 163, 165, 217]
---

# evaluator

> Alert rule evaluation engine and device state tracker.

## Overview

`evaluator_iot` reads telemetry and fleet state from PostgreSQL/TimescaleDB and:

- Tracks device status (ONLINE/STALE/OFFLINE) using heartbeat timestamps.
- Generates NO_HEARTBEAT alerts when devices miss expected heartbeat windows.
- Evaluates customer-defined alert rules (threshold/window/anomaly/pattern) and opens/closes alerts.
- Stores cooldown and sliding-window state in Valkey so alerts are rate-limited and survive restarts.
- Runs on a timer-driven loop (default 60s) with per-tenant isolation and shard-aware rollups.

## Architecture

- Timer-based evaluation every `EVALUATION_INTERVAL_SECONDS` (default 60s) with a minimum guard `MIN_EVAL_INTERVAL_SECONDS`.
- LISTEN/NOTIFY remains enabled to collect `_pending_tenants` but no longer triggers immediate cycles.
- Per-tenant exception isolation and wall-clock budget (`TENANT_BUDGET_MS`) prevent a noisy tenant from aborting the cycle.
- Sliding window buffers and rule cooldowns are stored in Valkey (`wbuf:*`, `cooldown:*` keys).
- Shard-aware rollup query uses `abs(hashtext(tenant_id)) % EVALUATOR_SHARD_COUNT = EVALUATOR_SHARD_INDEX`.

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
| `NOTIFY_DATABASE_URL` | falls back to `DATABASE_URL` | DSN used for LISTEN/NOTIFY paths. |
| `PG_POOL_MIN` | `2` | DB pool minimum connections. |
| `PG_POOL_MAX` | `10` | DB pool maximum connections. |
| `HEARTBEAT_STALE_SECONDS` | `30` | Heartbeat staleness threshold. |
| `EVALUATION_INTERVAL_SECONDS` | `60` | Timer-driven evaluation interval. |
| `MIN_EVAL_INTERVAL_SECONDS` | `10` | Minimum gap between evaluations. |
| `RULE_COOLDOWN_SECONDS` | `300` | Per (tenant, rule, device) cooldown before re-evaluating a fired rule. |
| `TENANT_BUDGET_MS` | `500` | Max wall-clock ms spent per tenant per cycle. |
| `VALKEY_URL` | `redis://localhost:6379` | Valkey connection string (cooldowns + window buffers). |
| `EVALUATOR_SHARD_INDEX` | `0` | This instance’s shard partition (0-based). |
| `EVALUATOR_SHARD_COUNT` | `1` | Total evaluator shards. |
| `POLL_SECONDS` | `5` | Legacy notify timeout; retained for compatibility but no longer primary trigger. |

## Health & Metrics

- Health endpoint: `GET http://<container>:8080/health`
- Prometheus metrics exported (evaluations, alerts, errors, queue depth, DB pool).

## Dependencies

- PostgreSQL + TimescaleDB (telemetry + fleet tables)
- PgBouncer (in compose) for pooling
- Valkey (cooldowns + window buffers)

## Troubleshooting

- Cycles too frequent: raise `EVALUATION_INTERVAL_SECONDS` or `MIN_EVAL_INTERVAL_SECONDS`.
- Rules firing too often: increase `RULE_COOLDOWN_SECONDS`.
- Noisy tenant aborting cycles: confirm per-tenant failures stay isolated and adjust `TENANT_BUDGET_MS`.
- DB timeouts: verify PgBouncer pool sizing and DB health; sharding reduces per-instance scope.

## See Also

- [System Overview](../architecture/overview.md)
- [Alerting](../features/alerting.md)
- [Database](../operations/database.md)
- [Evaluator Scaling](../operations/evaluator-scaling.md)
