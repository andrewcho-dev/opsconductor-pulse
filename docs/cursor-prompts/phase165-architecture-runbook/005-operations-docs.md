# Task 5: Update Operations Documentation

## Files to Modify

- `docs/operations/deployment.md` — Add K8s/Helm alongside Docker Compose, new services
- `docs/operations/runbook.md` — Add EMQX, NATS, MinIO, route-delivery troubleshooting
- `docs/operations/monitoring.md` — Update scrape targets, alert rules, dashboards, metrics
- `docs/operations/database.md` — Configurable pool sizing, managed PG notes
- `docs/operations/security.md` — EMQX auth backend, NATS auth, CRL auto-update

## What to Do

### 1. Update `docs/operations/deployment.md`

Read current content, then update:

**New services in Docker Compose:**
- EMQX: replaces Mosquitto, ports 1883/8883/18083/8083
- NATS: port 4222 (client), 8222 (monitoring)
- MinIO: port 9000 (S3 API), 9090 (console)
- minio-init: bucket creation sidecar
- route_delivery: webhook delivery service, port 8080 (metrics)

**Environment variables inventory:**
Add all new env vars introduced in Phases 160–164:
- `PG_POOL_MIN`, `PG_POOL_MAX` (all services)
- `NATS_URL`, `NATS_CREDS_FILE`
- `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`
- `EMQX_NODE_NAME`, `EMQX_DASHBOARD_DEFAULT_USERNAME`, `EMQX_DASHBOARD_DEFAULT_PASSWORD`
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`

**Kubernetes deployment (Phase 163):**
- Add section: Helm chart location (`deploy/helm/pulse/`)
- Document `values.yaml` structure: global settings, per-service replicas/resources
- Note HPA configuration for ingest and route-delivery
- Reference managed PostgreSQL configuration (RDS/Cloud SQL)
- Link to `docs/operations/kubernetes.md` for full K8s guide

**Removed:**
- Mosquitto service (replaced by EMQX)
- `export-data` volume (replaced by MinIO)
- Hard-coded DB pool sizes

### 2. Update `docs/operations/runbook.md`

Read current content, then add new troubleshooting sections:

**EMQX Broker:**
- Dashboard not loading: verify EMQX is healthy, check port 18083
- Auth failures: check `ui_iot` internal auth endpoint (`/api/v1/internal/mqtt-auth`), verify device credentials in DB
- High connection count: check `emqx_connections_count` metric, consider EMQX cluster scaling
- Bridge to NATS failing: verify NATS is reachable from EMQX, check bridge config in `emqx.conf`
- CRL update: CRL updates are now automatic via cron job (Phase 161 Task 3), verify cron is running

**NATS JetStream:**
- Consumer lag high: check `nats_consumer_num_pending` metric, scale consumer replicas
- Stream storage full: check disk usage, adjust stream `max_bytes` limit
- Messages not being consumed: verify consumer is connected (`nats consumer info TELEMETRY ingest-workers`)
- NATS down: critical — all ingestion stops; restart NATS, messages are durable so no data loss after recovery
- Useful CLI commands: `nats stream ls`, `nats consumer ls TELEMETRY`, `nats stream info TELEMETRY`

**MinIO / S3:**
- Export download fails: verify MinIO is healthy, check bucket exists (`mc ls pulse/exports`)
- Pre-signed URL expired: URLs expire after 1 hour; re-trigger download from UI
- MinIO not starting: check disk space on `minio-data` volume

**Route Delivery:**
- DLQ growing: check webhook destinations for failures, inspect DLQ messages
- High latency: check destination response times, tune `DELIVERY_TIMEOUT`
- Service down: restart route-delivery container; NATS retains messages, no data loss

**Update existing sections:**
- Replace Mosquitto troubleshooting with EMQX troubleshooting
- Update "MQTT Broker" section title to "EMQX Broker"
- Update health endpoint list: add EMQX (`http://iot-emqx:18083/api/v5/status`), NATS (`http://iot-nats:8222/healthz`), route_delivery (`http://iot-route-delivery:8080/health`), MinIO (`http://iot-minio:9000/minio/health/live`)

**Add Kubernetes operations section:**
- Pod not starting: check resource limits, image pull errors
- HPA not scaling: check metrics-server is deployed, verify HPA targets
- Rolling update stuck: check pod disruption budgets
- Link to `docs/operations/kubernetes.md` for full guide

### 3. Update `docs/operations/monitoring.md`

Read current content, then update:

**Scrape Targets:**
Add new Prometheus scrape jobs:
- `emqx` → `iot-emqx:18083` (path: `/api/v5/prometheus/stats`)
- `nats` → `iot-nats:8222` (path: `/metrics`)
- `route-delivery` → `iot-route-delivery:8080` (path: `/metrics`)

**Alert Rules:**
Add the Phase 164 infrastructure alerts:
- `NATSConsumerLagHigh` / `NATSConsumerLagCritical`
- `BatchWriteLatencyHigh`
- `EMQXConnectionsHigh`
- `DLQDepthGrowing`
- `RouteDeliveryLagHigh`
- `DBPoolSaturated`
- `IngestServiceDown`, `RouteDeliveryDown`, `EMQXDown`, `NATSDown`

**Grafana Dashboards:**
Add new dashboards from Phase 164:
- `tenant-overview.json` — per-tenant throughput, rejection rate, top tenants
- `infrastructure.json` — NATS lag, EMQX connections, batch write latency, DB pool utilization, DLQ depth

**Custom Metrics:**
Add route delivery metrics:
- `pulse_delivery_total` (labels: `tenant_id`, `destination_type`, `result`)
- `pulse_delivery_seconds` (labels: `destination_type`)
- `pulse_delivery_dlq_total` (labels: `tenant_id`)

Update ingest metrics:
- `pulse_ingest_batch_write_seconds` (labels: `tenant_id`)
- `pulse_ingest_nats_pending` (gauge)

### 4. Update `docs/operations/database.md`

Read current content, then update:

**Configurable pool sizing (Phase 160):**
- All services now read `PG_POOL_MIN` and `PG_POOL_MAX` from environment
- No longer hard-coded to `min_size=2, max_size=10`
- Production recommendation: scale pool max based on expected concurrency and PG `max_connections`

**Managed PostgreSQL (Phase 163):**
- Add section on using managed PostgreSQL (RDS, Cloud SQL, Azure Database)
- PgBouncer may be optional with managed PG (most offer built-in connection pooling)
- Migration script compatibility: `db/migrate.py` works with any PostgreSQL 15+ instance
- TimescaleDB extension: must be available on the managed instance

### 5. Update `docs/operations/security.md`

Read current content, then update:

**EMQX authentication (Phase 161):**
- HTTP auth backend replaces Mosquitto ACL file
- Per-device topic ACL enforcement at broker level
- Failed auth visible in EMQX dashboard and Prometheus metrics

**CRL management (Phase 161):**
- Automated CRL distribution via cron job (replaces manual SIGHUP)
- CRL update checks certificate revocation list and pushes to EMQX
- No broker restart needed for CRL updates (EMQX hot-reloads)

**NATS authentication:**
- NATS uses credential files for service authentication
- No device-level NATS access (devices only reach EMQX, bridge handles forwarding)

### 6. Update YAML frontmatter on all files

- Set `last-verified: 2026-02-19`
- Add `165` and relevant phase numbers to the `phases` array
- Add new source file paths
