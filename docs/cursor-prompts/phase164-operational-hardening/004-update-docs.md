# Task 4: Update Documentation

## Files to Update

- `docs/operations/monitoring.md` — Add S3/MinIO export storage, per-tenant metrics, Prometheus alert rules, Grafana dashboards
- `docs/operations/deployment.md` — Add MinIO service, S3 environment variables, Prometheus scrape targets
- `docs/services/ops-worker.md` — Document S3 export workflow (boto3, pre-signed URLs)
- `docs/services/ingest.md` — Document per-tenant Prometheus metrics and labels
- `docs/architecture/service-map.md` — Add MinIO, Prometheus scrape targets (EMQX, NATS, route-delivery)

## For Each File

1. Read the current content
2. Update the relevant sections to reflect this phase's changes:

### `docs/operations/monitoring.md`
- Add section: **Per-Tenant Metrics** — describe `tenant_id` label on `pulse_ingest_messages_total`, `pulse_delivery_total`, `pulse_delivery_dlq_total`
- Add section: **Infrastructure Alert Rules** — list all alerts from `alert_rules.yml` with thresholds and severities
- Add section: **Grafana Dashboards** — describe `tenant-overview.json` and `infrastructure.json` dashboards
- Add section: **Prometheus Scrape Targets** — document EMQX (`/api/v5/prometheus/stats`), NATS (`/metrics`), route-delivery (`:8080`)
- Note cardinality warning: `tenant_id` label manageable at 500 tenants, needs recording rules at 10K+

### `docs/operations/deployment.md`
- Add MinIO service to the service inventory with ports (9000 S3 API, 9090 Console)
- Document `minio-init` container for bucket creation (`exports`, `reports`)
- Add S3 environment variables: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`
- Note: for production AWS S3, omit `S3_ENDPOINT` and use IAM roles

### `docs/services/ops-worker.md`
- Update export worker section: now uses boto3 for S3 uploads instead of local filesystem
- Document pre-signed URL flow for downloads (1-hour expiry)
- Note: `export-data` volume removed, replaced by S3 bucket

### `docs/services/ingest.md`
- Add Prometheus metrics section listing all exposed metrics with labels
- Document route delivery metrics: `pulse_delivery_total`, `pulse_delivery_seconds`, `pulse_delivery_dlq_total`
- Note metrics server on port 8080 for route delivery service

### `docs/architecture/service-map.md`
- Add MinIO to infrastructure services
- Add Prometheus scrape relationships to EMQX, NATS, and route-delivery

3. Update the YAML frontmatter:
   - Set `last-verified: 2026-02-19`
   - Add `164` to the `phases` array
   - Add/update `sources` if new source files are relevant:
     - `compose/prometheus/alert_rules.yml`
     - `compose/prometheus/prometheus.yml`
     - `compose/grafana/provisioning/dashboards/tenant-overview.json`
     - `compose/grafana/provisioning/dashboards/infrastructure.json`
     - `services/ops_worker/workers/export_worker.py`
     - `services/route_delivery/delivery.py`

4. Verify no stale information remains (e.g., references to local filesystem exports, missing scrape targets)
