---
last-verified: 2026-02-19
sources:
  - compose/docker-compose.yml
  - compose/emqx/emqx.conf
  - compose/nats/init-streams.sh
phases: [45, 114, 142, 161, 162, 163, 164, 165]
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
- ops_worker: `http://ops_worker:8080/health`
- route_delivery: `http://route-delivery:8080/health`
- provision_api: `http://api:8081/health`
- EMQX (broker health): `http://mqtt:18083/api/v5/status`
- NATS (health): `http://nats:8222/healthz`
- MinIO (health): `http://minio:9000/minio/health/live`
- Prometheus: `http://prometheus:9090/-/healthy`
- Grafana: `http://grafana:3001/api/health`

## Log Inspection

```bash
docker compose logs -f ui
docker compose logs -f ingest
docker compose logs -f evaluator
docker compose logs -f ops_worker
docker compose logs -f route-delivery
docker compose logs -f mqtt
docker compose logs -f nats
docker compose logs -f minio
docker compose logs -f keycloak
```

## Common Issues

### Keycloak

- Keycloak not starting: ensure Postgres is healthy and keycloak DB init ran; check `keycloak-db-init` logs.
- Login fails: verify realm import and redirect URIs in `compose/keycloak/realm-pulse.json`.

### PostgreSQL / PgBouncer

- Password auth failures: verify `.env` values (`POSTGRES_PASSWORD`, `PG_PASS`) match compose usage.
- Pool exhaustion: check Prometheus alert `DBPoolExhausted`; tune pool size or reduce concurrency.

### EMQX (MQTT Broker)

- Dashboard not loading: verify EMQX is healthy and port `18083` is reachable.
- Device connect/auth failures: check `ui_iot` internal auth endpoints (`/api/v1/internal/mqtt-auth`, `/api/v1/internal/mqtt-acl`) and `MQTT_INTERNAL_AUTH_SECRET`.
- TLS failures (device mTLS): verify `compose/mosquitto/certs` mounts and CA chain; check EMQX logs.
  - Note: the internal compose listener on `1883` is plain TCP; external devices use `8883` mTLS.

### NATS JetStream

- NATS down: ingestion and async route delivery stop; after recovery, JetStream consumers resume from durable state.
- Consumer lag high: check `pulse_ingest_queue_depth` and `pulse_route_delivery_nats_pending`. Scale workers or tune batch settings.
- Streams/consumers missing: verify `nats-init` ran successfully (creates streams and consumers).

### Ingestion Pipeline

- Backpressure: watch ingest queue depth metrics; tune `INGEST_WORKER_COUNT`, `BATCH_SIZE`, `FLUSH_INTERVAL_MS`.
- Quarantine spikes: inspect quarantine reasons (token invalid, site mismatch, payload too large, rate limit).

### Route Delivery (Message Routes)

`route_delivery` handles message routes (webhook + MQTT republish) asynchronously via JetStream `ROUTES` stream.

- DLQ growing: check webhook endpoints for failures; inspect `dead_letter_messages` in PostgreSQL.
- High latency: check destination response times; tune `WEBHOOK_TIMEOUT_SECONDS`.

### Evaluator

- Falling behind: increase `POLL_SECONDS`, scale evaluator, or reduce rule/device cardinality.
- Too many heartbeat alerts: tune `HEARTBEAT_STALE_SECONDS` and device heartbeat cadence.

### Frontend

- 502 / blank page: check ui logs and Caddy routing; confirm SPA bundle is built and mounted.
- `ModuleNotFoundError` on ui startup: add missing `COPY <package> /app/<package>` in `services/ui_iot/Dockerfile`, rebuild ui.

### Migrations

- API errors after deploy: verify migrator ran and migrations are up-to-date; run `python db/migrate.py` against the target DB.

## Kubernetes Operations (Helm)

If running on Kubernetes (Phase 163 Helm chart):

- Pod not starting: check `kubectl describe pod ...` for image pull errors, env var config, and probe failures.
- HPA not scaling: confirm `metrics-server` is installed and HPA targets are configured.

See `docs/operations/kubernetes.md` for the full guide.

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

- Ingest throughput: `INGEST_WORKER_COUNT`, `BATCH_SIZE`, `FLUSH_INTERVAL_MS`
- Evaluator cadence: `POLL_SECONDS`, `HEARTBEAT_STALE_SECONDS`
- DB pooling: `PG_POOL_MIN`/`PG_POOL_MAX` per service + PgBouncer pool sizing and max client connections

## Emergency Procedures

- Crash loops: identify service and root exception; fix config (env/volumes) and restart.
- DB unavailable: stop dependent services; restore DB; run migrations; bring services up in order.

## See Also

- [Deployment](deployment.md)
- [Database](database.md)
- [Monitoring](monitoring.md)

