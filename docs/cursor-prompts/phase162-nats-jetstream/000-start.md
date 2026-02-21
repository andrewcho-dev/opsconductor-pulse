# Phase 162 — NATS JetStream Integration (R3)

## Goal

Add NATS JetStream as the durable message backbone between EMQX and all consumers. This is the core architectural change that enables:
- **No more data loss** — NATS streams are durable; messages survive broker/consumer restarts
- **Horizontal scaling** — multiple ingest workers in a consumer group, add more to scale
- **Unified ingestion** — both MQTT and HTTP data flow through the same pipeline
- **Async route delivery** — webhook/republish delivery via NATS with retry support

## Prerequisites

- Phase 160 (Foundation Hardening) complete
- Phase 161 (EMQX Migration) complete

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-nats-config.md` | Add NATS JetStream to docker-compose, create streams |
| 002  | `002-emqx-nats-bridge.md` | Configure EMQX rule engine to bridge MQTT → NATS |
| 003  | `003-ingest-nats-consumer.md` | Refactor ingest_iot from MQTT subscriber to NATS consumer |
| 004  | `004-http-ingest-nats-publisher.md` | Refactor HTTP ingest to publish to NATS instead of direct DB writes |
| 005  | `005-route-delivery-service.md` | Create dedicated route delivery worker consuming from NATS |
| 006  | `006-update-docs.md` | Update documentation |

## Architecture After This Phase

```
MQTT Devices              HTTP Devices
     │                         │
┌────▼─────┐            ┌─────▼─────┐
│  EMQX    │            │  ui_iot   │
│  broker  │            │  /ingest  │
└────┬─────┘            └─────┬─────┘
     │ rule engine             │ NATS publish
     │                        │
┌────▼────────────────────────▼────┐
│         NATS JetStream           │
│  TELEMETRY.{tenant_id}           │
│  SHADOW.{tenant_id}              │
│  COMMANDS.{tenant_id}            │
│  ROUTES.{tenant_id}              │
└────┬──────────────┬──────────────┘
     │              │
┌────▼────┐   ┌────▼──────────┐
│ Ingest  │   │ Route         │
│ Workers │   │ Delivery      │
│ (N pods)│   │ Workers       │
└────┬────┘   └───────────────┘
     │
┌────▼─────┐
│PostgreSQL│
└──────────┘
```

## Verification

```bash
# 1. NATS health
curl -s http://localhost:8222/healthz

# 2. Stream info
nats stream info TELEMETRY --server nats://localhost:4222

# 3. Consumer info
nats consumer info TELEMETRY ingest-workers --server nats://localhost:4222

# 4. End-to-end: publish via MQTT, verify telemetry in DB
mosquitto_pub -h localhost -p 1883 -u service_pulse -P "$MQTT_ADMIN_PASSWORD" \
  -t "tenant/test/device/dev1/telemetry" \
  -m '{"site_id":"s1","provision_token":"tok","metrics":{"temp":22}}'
# Check DB for the record
```
