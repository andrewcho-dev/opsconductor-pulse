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

