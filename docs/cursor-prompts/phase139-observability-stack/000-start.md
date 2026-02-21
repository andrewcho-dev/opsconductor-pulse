# Phase 139 — Observability Stack

## Goal
Deploy Prometheus + Grafana to scrape all service `/metrics` endpoints and provide pre-built dashboards.

## Current State
- All services expose Prometheus-compatible `/metrics` endpoints via `prometheus_client` library
- Services with metrics: ui_iot (port 8081), ingest_iot (aiohttp handler), evaluator_iot, ops_worker (port 8080), dispatcher (deprecated, being removed in 138), delivery_worker (deprecated)
- Shared metrics defined in `services/shared/metrics.py`: HTTP request/duration, auth failures, evaluator counters, fleet gauges, DB pool, ingest queue
- No Prometheus scraper or Grafana deployed

## Existing Compose Structure
- `compose/docker-compose.yml` — main compose file (604 lines)
- `compose/` contains: `caddy/`, `keycloak/`, `mosquitto/`, `postgres/`, `services/`
- No `compose/prometheus/` or `compose/grafana/` directories exist

## Execution Order
1. `001-prometheus.md` — Add Prometheus service + scrape config
2. `002-grafana.md` — Add Grafana service + datasource provisioning
3. `003-dashboards.md` — Create 6 pre-built Grafana dashboards
4. `004-alert-rules.md` — Add Prometheus alerting rules

## Verification (after all tasks)
```bash
docker compose up -d prometheus grafana
curl localhost:9090/targets          # all targets UP
# Open localhost:3001 (Grafana)      # dashboards with live data
```
