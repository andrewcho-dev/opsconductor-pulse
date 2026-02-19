---
last-verified: 2026-02-19
sources:
  - services/ingest_iot/ingest.py
phases: [15, 23, 101, 139, 142, 160, 161, 162]
---

# ingest

> NATS JetStream telemetry ingestion service.

## Overview

`ingest_iot` consumes telemetry from NATS JetStream, validates and rate-limits telemetry, and writes time-series records to TimescaleDB in batches.

Key responsibilities:

- Topic parsing: `tenant/{tenant_id}/device/{device_id}/{msg_type}`
- Auth cache: avoids per-message DB lookups
- Rate limiting: token bucket per (tenant, device)
- Batch writing: high-throughput inserts into `telemetry`
- Quarantine: rejects invalid messages into quarantine tables with a reason

## Architecture

Pipeline stages (high level):

1. JetStream consume → parse topic → extract tenant/device/msg_type
2. Validate required fields (`site_id`, timestamp), payload size, metric constraints
3. Device registry validation (cache + DB fallback)
4. Subscription status checks (block suspended/expired)
5. Batch insert telemetry records, update device last-seen/location as needed
6. Message route fan-out is published to NATS and delivered asynchronously by the `route-delivery` service (webhook/MQTT republish)

## Configuration

Environment variables read by the service:

| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_URL` | `nats://iot-nats:4222` | NATS server URL. |
| `PG_HOST` | `iot-postgres` | PostgreSQL host (used when `DATABASE_URL` is not set). |
| `PG_PORT` | `5432` | PostgreSQL port. |
| `PG_DB` | `iotcloud` | Database name. |
| `PG_USER` | `iot` | Database user. |
| `PG_PASS` | `iot_dev` | Database password. |
| `DATABASE_URL` | empty | Optional DSN; when set, preferred over `PG_*`. |
| `PG_POOL_MIN` | `2` | DB pool minimum connections. |
| `PG_POOL_MAX` | `10` | DB pool maximum connections. |
| `AUTO_PROVISION` | `0` | If enabled, auto-register unknown devices when capacity allows. |
| `REQUIRE_TOKEN` | `1` | If enabled, require `provision_token` validation. |
| `CERT_AUTH_ENABLED` | `0` | Enables certificate-based auth behaviors (where supported). |
| `COUNTERS_ENABLED` | `1` | Enables Prometheus counters. |
| `SETTINGS_POLL_SECONDS` | `5` | Poll interval for dynamic settings. |
| `LOG_STATS_EVERY_SECONDS` | `30` | Periodic stats logging interval. |
| `AUTH_CACHE_TTL_SECONDS` | `60` | Device auth cache TTL. |
| `AUTH_CACHE_MAX_SIZE` | `10000` | Auth cache maximum entries. |
| `BATCH_SIZE` | `500` | Telemetry batch size before flush. |
| `FLUSH_INTERVAL_MS` | `1000` | Max time before flushing telemetry batch. |
| `INGEST_WORKER_COUNT` | `4` | Number of ingestion workers. |
| `INGEST_QUEUE_SIZE` | `50000` | Queue size for ingestion events. |
| `DELIVERY_WORKER_COUNT` | `2` | Async route delivery workers (webhooks/MQTT republish). |
| `BUCKET_TTL_SECONDS` | `3600` | Rate limiter bucket TTL. |
| `BUCKET_CLEANUP_INTERVAL` | `300` | Bucket cleanup interval. |

## Shutdown

The ingest service handles SIGTERM/SIGINT gracefully to reduce data loss during deploy/restart:

- Stop accepting new MQTT messages
- Drain the ingest queue (bounded timeout)
- Stop ingest workers
- Drain route delivery queue and stop delivery workers
- Flush `TimescaleBatchWriter` (final batch flush)
- Close the DB pool

## Health & Metrics

- Health endpoint: `GET http://<container>:8080/health`
- Metrics endpoint: `GET http://<container>:8080/metrics` (Prometheus format)

## Dependencies

- EMQX MQTT broker
- PostgreSQL + TimescaleDB (telemetry + registry tables)
- PgBouncer (in compose) for pooling

## Troubleshooting

- Quarantine growth: inspect quarantine tables and rejection reasons (token invalid, site mismatch, payload size, rate limiting).
- Backpressure: tune `INGEST_WORKER_COUNT`, `INGEST_QUEUE_SIZE`, `BATCH_SIZE`, and `FLUSH_INTERVAL_MS`.
- MQTT TLS failures: verify `MQTT_CA_CERT` mount and broker certificate chain.

## See Also

- [Ingestion Endpoints](../api/ingest-endpoints.md)
- [System Overview](../architecture/overview.md)
- [Database](../operations/database.md)

