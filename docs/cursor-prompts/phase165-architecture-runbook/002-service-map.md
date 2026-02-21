# Task 2: Update Service Map

## File to Modify

- `docs/architecture/service-map.md`

## What to Do

Update the service map to reflect the post-rearchitecture topology. This is the quick-reference doc engineers use when debugging — every service, port, dependency, and data flow must be accurate.

### Changes Required

#### 1. Update Network Topology

Replace:
> Devices publish telemetry to Mosquitto MQTT (external TLS port 8883) which feeds `ingest_iot`.

With:
> Devices publish telemetry to EMQX (external TLS port 8883). EMQX bridges messages to NATS JetStream. Ingest workers consume from NATS for durable, horizontally-scalable processing.

#### 2. Update Port Reference table

Replace the Mosquitto row with EMQX and add new services:

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| EMQX | 1883/8083 | 8883 (TLS) | MQTT/WS |
| EMQX Dashboard | 18083 | 18083 | HTTP |
| NATS | 4222 | — | NATS |
| NATS Monitoring | 8222 | — | HTTP |
| route_delivery | 8080 | — | HTTP (metrics) |
| MinIO (S3 API) | 9000 | 9000 | HTTP |
| MinIO Console | 9090 | 9090 | HTTP |

Keep all existing services but remove the Mosquitto row.

#### 3. Update Service Dependencies table

Update ingest_iot:
- Depends On: **NATS JetStream** (replaces Mosquitto), PgBouncer/PostgreSQL
- Why: Consumes telemetry from NATS TELEMETRY stream + writes to DB

Add route_delivery:
- Depends On: NATS JetStream, PgBouncer/PostgreSQL
- Why: Consumes route delivery jobs from NATS ROUTES stream, delivers to webhooks

Update ops_worker:
- Add: MinIO (for export storage)

Update Prometheus:
- Add: EMQX, NATS, route_delivery to scrape targets

Add EMQX:
- Depends On: NATS (bridge destination)
- Why: Bridges MQTT messages to NATS streams

Add NATS:
- Depends On: (none — standalone)
- Why: Message backbone for all inter-service async communication

Add MinIO:
- Depends On: (none — standalone)
- Why: S3-compatible object storage for exports and reports

#### 4. Update Core Data Flow

Replace:
```
1. Device → Mosquitto (MQTT/TLS) → ingest_iot
2. ingest_iot → TimescaleDB telemetry hypertable
```

With:
```
1. Device → EMQX (MQTT/TLS) → NATS bridge → TELEMETRY stream
2. ingest_workers (consumer group) → validate + batch write → TimescaleDB
3. HTTP ingestion: ui_iot /ingest/* → publish to NATS TELEMETRY → same consumer group
```

Update alert operations:
```
1. Alert created → publish to NATS ROUTES stream
2. route_delivery consumers → deliver to Slack/PagerDuty/Teams/HTTP webhook
3. DLQ captures failed deliveries for retry
```

#### 5. Add NATS Streams section

Document the NATS stream topology:

| Stream | Subjects | Purpose | Consumers |
|--------|----------|---------|-----------|
| TELEMETRY | `telemetry.{tenant_id}.{device_id}` | Raw device telemetry | `ingest-workers` (group) |
| SHADOW | `shadow.{tenant_id}.{device_id}` | Device shadow updates | `shadow-processor` |
| COMMANDS | `commands.{tenant_id}.{device_id}` | Device commands | `command-forwarder` |
| ROUTES | `routes.{tenant_id}.{route_id}` | Notification delivery jobs | `route-delivery` (group) |

#### 6. Update YAML frontmatter

```yaml
---
last-verified: 2026-02-19
sources:
  - compose/docker-compose.yml
  - compose/caddy/Caddyfile
  - compose/emqx/emqx.conf
  - compose/nats/nats-server.conf
phases: [88, 98, 138, 139, 142, 161, 162, 163, 164, 165]
---
```
