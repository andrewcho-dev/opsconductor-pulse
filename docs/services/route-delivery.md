---
last-verified: 2026-02-19
sources:
  - services/route_delivery/delivery.py
  - compose/nats/init-streams.sh
phases: [162, 164, 165]
---

# route-delivery

> Dedicated message route delivery service (webhook + MQTT republish).

## Overview

`route_delivery` consumes message route jobs from NATS JetStream (stream `ROUTES`) and performs delivery asynchronously so ingest processing is not blocked by slow destinations.

## Architecture

- JetStream stream: `ROUTES`
- Durable pull consumer: `route-delivery`
- Subject filter: `routes.>`
- Job payload: JSON envelope published by the ingest pipeline containing:
  - `tenant_id`
  - `route` (destination type + config)
  - `payload` (message payload to deliver)

## Delivery Targets

- `webhook` (HTTP request with optional HMAC signature header)
- `mqtt_republish` (publish to internal MQTT broker topics)
- `postgresql` (no-op in delivery service; payload already written by ingest)

## Retry + DLQ Semantics

JetStream redelivery settings (see `compose/nats/init-streams.sh`):

- `max_deliver=3`
- `wait=30s` (ack wait)

After the final delivery failure, the service writes a record to the application DLQ table in PostgreSQL:

- Table: `dead_letter_messages`

This DLQ is database-backed (not a separate NATS DLQ stream).

## Health & Metrics

HTTP server on port `8080`:

- `GET /health`
- `GET /ready`
- `GET /metrics`

Key Prometheus metrics:

- `pulse_delivery_total{tenant_id, destination_type, result}`
- `pulse_delivery_seconds_bucket{destination_type}`
- `pulse_delivery_dlq_total{tenant_id}`
- `pulse_route_delivery_nats_pending`

## Configuration

Environment variables:

- `NATS_URL` (default `nats://localhost:4222`)
- `DATABASE_URL` (optional; when unset uses `PG_HOST`/`PG_PORT`/`PG_DB`/`PG_USER`/`PG_PASS`)
- `DELIVERY_WORKER_COUNT` (default `4`)
- `WEBHOOK_TIMEOUT_SECONDS` (default `10`)

MQTT republish (optional; only used when destinations require it):

- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`
- `MQTT_TLS`, `MQTT_TLS_INSECURE`

## See Also

- [Monitoring](../operations/monitoring.md)
- [Service Map](../architecture/service-map.md)
- [ingest](ingest.md)

---
last-verified: 2026-02-19
sources:
  - services/route_delivery/delivery.py
  - compose/docker-compose.yml
phases: [162]
---

# route-delivery

> Delivers message routes (webhooks, MQTT republish) from the NATS `ROUTES` stream.

## Overview

The ingest pipeline publishes matched routes as jobs to `routes.{tenant_id}` (JetStream stream `ROUTES`).
This service consumes those jobs and performs delivery asynchronously with retry.

## Delivery Types

- `webhook`: HTTP request with optional `X-Signature-256` (HMAC-SHA256)
- `mqtt_republish`: publish payload to a configured MQTT topic template
- `postgresql`: no-op (already written by ingest worker)

## Retry + DLQ

- JetStream consumer `max_deliver=3` controls retry attempts
- On the final failed attempt, the job is written to `dead_letter_messages` and the message is terminated

## Configuration

Environment variables:

- `NATS_URL` (default `nats://localhost:4222`)
- `DATABASE_URL` or `PG_*` (DLQ writes)
- `DELIVERY_WORKER_COUNT` (default `4`)
- `WEBHOOK_TIMEOUT_SECONDS` (default `10`)
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` (optional; required for `mqtt_republish`)

