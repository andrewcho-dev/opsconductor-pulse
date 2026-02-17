---
last-verified: 2026-02-17
sources:
  - compose/docker-compose.yml
phases: [45, 114, 142]
---

# Runbook

> Troubleshooting guide and operational procedures.

## Service Health Checks

Common checks:

```bash
cd compose/
docker compose ps
docker compose logs --tail=100 ui
```

Service health endpoints (where applicable):

- ui_iot: `http://ui:8080/health`
- ingest_iot: `http://ingest:8080/health`
- evaluator_iot: `http://evaluator:8080/health`
- provision_api: `http://api:8081/health`
- Prometheus: `http://prometheus:9090/-/healthy`
- Grafana: `http://grafana:3001/api/health`

## Log Inspection

```bash
docker compose logs -f ui
docker compose logs -f ingest
docker compose logs -f evaluator
docker compose logs -f ops_worker
docker compose logs -f keycloak
```

## Common Issues

### Keycloak

- Keycloak not starting: ensure Postgres is healthy and keycloak DB init ran; check `keycloak-db-init` logs.
- Login fails: verify realm import and redirect URIs in `compose/keycloak/realm-pulse.json`.

### PostgreSQL / PgBouncer

- Password auth failures: verify `.env` values (`POSTGRES_PASSWORD`, `PG_PASS`) match compose usage.
- Pool exhaustion: check Prometheus alert `DBPoolExhausted`; tune pool size or reduce concurrency.

### MQTT Broker

- TLS failures: verify `compose/mosquitto/certs` mounts and CA chain; check mosquitto logs.
- Topic access problems: confirm ACL rules and ingest-side topic validation.

### Ingestion Pipeline

- Backpressure: watch ingest queue depth metrics; tune `INGEST_WORKER_COUNT`, `INGEST_QUEUE_SIZE`, `BATCH_SIZE`, `FLUSH_INTERVAL_MS`.
- Quarantine spikes: inspect quarantine reasons (token invalid, site mismatch, payload too large, rate limit).

### Evaluator

- Falling behind: increase `POLL_SECONDS`, scale evaluator, or reduce rule/device cardinality.
- Too many heartbeat alerts: tune `HEARTBEAT_STALE_SECONDS` and device heartbeat cadence.

### Frontend

- 502 / blank page: check ui logs and Caddy routing; confirm SPA bundle is built and mounted.
- `ModuleNotFoundError` on ui startup: add missing `COPY <package> /app/<package>` in `services/ui_iot/Dockerfile`, rebuild ui.

### Migrations

- API errors after deploy: verify migrator ran and migrations are up-to-date; run `python db/migrate.py` against the target DB.

## Restart Procedures

```bash
docker compose restart ui
docker compose restart ingest evaluator ops_worker
```

Full restart:

```bash
docker compose down
docker compose up -d --build
```

## Performance Tuning

Common knobs:

- Ingest throughput: `INGEST_WORKER_COUNT`, `INGEST_QUEUE_SIZE`, `BATCH_SIZE`, `FLUSH_INTERVAL_MS`
- Evaluator cadence: `POLL_SECONDS`, `HEARTBEAT_STALE_SECONDS`
- DB pooling: PgBouncer pool sizing and max client connections

## Emergency Procedures

- Crash loops: identify service and root exception; fix config (env/volumes) and restart.
- DB unavailable: stop dependent services; restore DB; run migrations; bring services up in order.

## See Also

- [Deployment](deployment.md)
- [Database](database.md)
- [Monitoring](monitoring.md)

