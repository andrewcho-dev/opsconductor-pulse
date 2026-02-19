---
last-verified: 2026-02-19
sources:
  - services/ops_worker/main.py
  - services/ops_worker/health_monitor.py
  - services/ops_worker/metrics_collector.py
  - services/ops_worker/workers/
  - services/ops_worker/workers/export_worker.py
phases: [43, 58, 88, 139, 142, 164]
---

# ops-worker

> Health monitoring, metrics collection, and background job runner.

## Overview

`ops_worker` is a background process that runs periodic operational tasks:

- Polls service health endpoints and optionally opens/closes system alerts.
- Collects platform metrics and writes time-series points to `system_metrics`.
- Runs periodic cleanup and automation jobs (exports, reports, OTA, certificate maintenance, command expiry, etc.).

## Architecture

Entry point: `services/ops_worker/main.py` starts and supervises multiple async tasks.

Key components:

- `health_monitor.py`: HTTP polling of service health endpoints.
- `metrics_collector.py`: periodic aggregation writes to TimescaleDB.
- `workers/`: task-specific workers invoked on their schedules.

## Exports (S3/MinIO)

The async export pipeline stores export artifacts in S3-compatible object storage (MinIO in local compose).

- `export_worker.py` writes the export to a local temp file, uploads it to `s3://$S3_BUCKET/{export_id}.{format}`, then deletes the temp file.
- The `export_jobs.file_path` field stores the S3 object key (not a local filesystem path).
- Expired exports are cleaned up by deleting the S3 object when the DB record expires.

For downloads, the UI API (`ui_iot`) generates a pre-signed URL and redirects the browser to download directly from S3/MinIO.

## Configuration

`ops_worker` reads environment variables across its modules:

Database:

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `iot-postgres` | PostgreSQL host (used when `DATABASE_URL` is not set). |
| `PG_PORT` | `5432` | PostgreSQL port. |
| `PG_DB` | `iotcloud` | Database name. |
| `PG_USER` | `iot` | Database user. |
| `PG_PASS` | `iot_dev` | Database password. |
| `DATABASE_URL` | empty | Optional DSN; when set, preferred over `PG_*`. |

Health monitor:

| Variable | Default | Description |
|----------|---------|-------------|
| `INGEST_HEALTH_URL` | `http://iot-ingest:8080` | Health endpoint for ingest service. |
| `EVALUATOR_HEALTH_URL` | `http://iot-evaluator:8080` | Health endpoint for evaluator service. |
| `HEALTH_CHECK_INTERVAL` | `60` | Health polling interval seconds. |
| `SYSTEM_ALERT_ENABLED` | `true` | Enables system alert generation from health state. |

Metrics collector:

| Variable | Default | Description |
|----------|---------|-------------|
| `METRICS_COLLECTION_INTERVAL` | `5` | Metrics collection interval seconds. |

## Health & Metrics

`ops_worker` is background-only (no HTTP server). It contributes:

- System metrics written to DB (`system_metrics`) for dashboards
- Prometheus-scraped metrics where applicable (depends on worker implementation)

## Dependencies

- PostgreSQL + TimescaleDB (system_metrics and fleet tables)
- HTTP connectivity to internal service health endpoints

## Troubleshooting

- Missing metrics: verify `ops_worker` is running and DB access is healthy.
- False system alerts: confirm `SYSTEM_ALERT_ENABLED` and health URL correctness.
- Load concerns: tune intervals (`HEALTH_CHECK_INTERVAL`, `METRICS_COLLECTION_INTERVAL`) to match environment.

## See Also

- [Monitoring](../operations/monitoring.md)
- [Runbook](../operations/runbook.md)
- [Database](../operations/database.md)

