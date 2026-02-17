---
last-verified: 2026-02-17
sources:
  - compose/prometheus/prometheus.yml
  - compose/prometheus/alert_rules.yml
  - compose/grafana/provisioning/
  - compose/grafana/dashboards/
phases: [58, 102, 139, 142]
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
- `ops_worker` → `ops_worker:8080` (`/metrics` via `prometheus_client.start_http_server`)
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

Evaluator:

- `pulse_evaluator_rules_evaluated_total`
- `pulse_evaluator_alerts_created_total`
- `pulse_evaluator_evaluation_errors_total`

DB / processing:

- `pulse_db_pool_size`
- `pulse_db_pool_free`
- `pulse_processing_duration_seconds`

HTTP / auth:

- `pulse_http_requests_total`
- `pulse_http_request_duration_seconds`
- `pulse_auth_failures_total`

## See Also

- [Runbook](runbook.md)
- [Deployment](deployment.md)
- [Security](security.md)

