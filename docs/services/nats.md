---
last-verified: 2026-02-19
sources:
  - compose/docker-compose.yml
  - compose/nats/nats.conf
  - compose/nats/init-streams.sh
phases: [162]
---

# nats (jetstream)

> Durable message backbone for MQTT + HTTP ingestion and route delivery.

## Overview

This deployment runs NATS with JetStream enabled. Producers publish into subjects; consumers pull from durable JetStream streams/consumers.

## Ports

- `4222`: NATS client port (localhost-only in compose)
- `8222`: HTTP monitoring (localhost-only in compose)

## Streams

Streams created by `compose/nats/init-streams.sh`:

- `TELEMETRY` (subjects: `telemetry.>`): device telemetry + heartbeat envelopes
- `SHADOW` (subjects: `shadow.>`): reported shadow updates
- `COMMANDS` (subjects: `commands.>`): command acknowledgements
- `ROUTES` (subjects: `routes.>`): route delivery jobs (work-queue style)

## Consumers

Durable pull consumers:

- `TELEMETRY/ingest-workers`: ingest worker consumer group
- `SHADOW/ingest-shadow`: shadow processing consumer
- `COMMANDS/ingest-commands`: command ack processing consumer
- `ROUTES/route-delivery`: route delivery consumer group

## Retention

- `TELEMETRY`, `SHADOW`, `COMMANDS` use `limits` retention (bounded by `max_age`, `max_bytes`)
- `ROUTES` uses `work` retention (messages removed once ACKed)

