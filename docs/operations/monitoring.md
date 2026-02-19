---
last-verified: 2026-02-19
sources:
  - compose/prometheus/prometheus.yml
  - compose/prometheus/alert_rules.yml
  - compose/grafana/provisioning/
  - compose/grafana/dashboards/
phases: [58, 102, 139, 142, 164]
---

# Monitoring

> Prometheus metrics, Grafana dashboards, and health endpoints.

## Overview

The monitoring stack (Phase 139) is:

- Prometheus (scrapes `/metrics`)
- Grafana (pre-provisioned dashboards)
- Prometheus alert rules for health, latency, DB pool pressure, ingestion backlogs, auth failures, and evaluator errors

## Prometheus

### Configuration

From `compose/prometheus/prometheus.yml`:

- Global scrape interval: 15s
- Targets are configured as static configs for core services

### Scrape Targets

Configured jobs:

- `ui_iot` → `ui:8080` (`/metrics`)
- `ingest_iot` → `ingest:8080` (`/metrics`)
- `evaluator_iot` → `evaluator:8080` (`/metrics`)
- `ops_worker` → `ops_worker:8080` (`/metrics`)
- `route_delivery` → `route-delivery:8080` (`/metrics`)
- `emqx` → `mqtt:18083` (`/api/v5/prometheus/stats`)
- `nats` → `nats-exporter:7777` (`/metrics`)
- `prometheus` → `localhost:9090`

### Alert Rules

From `compose/prometheus/alert_rules.yml`:

- `ServiceDown` — `up == 0` for 1m
- `HighErrorRate` — HTTP 5xx error rate > 5% for 5m
- `HighLatency` — p95 latency > 2s for 5m
- `DBPoolExhausted` — `pulse_db_pool_free < 2` for 5m
- `HighAuthFailureRate` — > 10 auth failures per minute for 5m
- `IngestQueueBacklog` — ingest queue depth > 10000 for 5m
- `EvaluatorErrors` — evaluation errors rate > 0.1/s for 10m
- `DeliveryFailures` — delivery failure counter > 0 for 10m
- `NATSConsumerLagHigh` — ingest pending > 10000 for 2m
- `NATSConsumerLagCritical` — ingest pending > 50000 for 1m
- `RouteDeliveryLagHigh` — route-delivery pending > 1000 for 3m
- `BatchWriteLatencyHigh` — ingest batch write p95 > 2s for 3m
- `EMQXConnectionsHigh` — EMQX connections > 50000 for 5m
- `DLQDepthGrowing` — DLQ writes > 100/hour for 5m
- `DBPoolSaturated` — DB pool utilization > 80% for 5m

## Grafana

### Access

- URL: `http://localhost:3001`
- Admin credentials are configured via compose env vars

### Pre-Provisioned Dashboards

Provisioned dashboards (from `compose/grafana/dashboards/`):

- `api-overview.json`
- `service-health.json`
- `device-fleet.json`
- `alert-pipeline.json`
- `database.json`
- `auth-security.json`
- `tenant-overview.json`
- `infrastructure.json`

## Health Endpoints

Common health endpoints:

- ui_iot: `GET http://ui:8080/health`
- ingest_iot: `GET http://ingest:8080/health`
- evaluator_iot: `GET http://evaluator:8080/health`
- provision_api: `GET http://api:8081/health`
- Prometheus: `GET http://prometheus:9090/-/healthy`
- Grafana: `GET http://grafana:3001/api/health`

## Custom Metrics

Key custom metrics are defined in `services/shared/metrics.py` and include:

Ingestion:

- `pulse_ingest_messages_total`
- `pulse_ingest_queue_depth`
- `pulse_ingest_batch_write_seconds` (recorded under a synthetic tenant_id `__all__`)

Evaluator:

- `pulse_evaluator_rules_evaluated_total`
- `pulse_evaluator_alerts_created_total`
- `pulse_evaluator_evaluation_errors_total`

DB / processing:

- `pulse_db_pool_size`
- `pulse_db_pool_free`
- `pulse_processing_duration_seconds`

Per-tenant metrics:

- `pulse_ingest_messages_total{tenant_id=...}` — accepted/rejected/rate_limited counts
- `pulse_delivery_total{tenant_id=...}` — webhook/mqtt_republish delivery success/failure counts
- `pulse_delivery_dlq_total{tenant_id=...}` — DLQ writes per tenant

Note: adding `tenant_id` labels increases time-series cardinality. This is manageable at hundreds of tenants; at very large scale, use recording rules to pre-aggregate.

HTTP / auth:

- `pulse_http_requests_total`
- `pulse_http_request_duration_seconds`
- `pulse_auth_failures_total`

## See Also

- [Runbook](runbook.md)
- [Deployment](deployment.md)
- [Security](security.md)

