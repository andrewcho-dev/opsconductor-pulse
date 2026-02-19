---
last-verified: 2026-02-19
sources:
  - compose/docker-compose.yml
  - compose/.env
  - compose/.env.example
  - compose/caddy/Caddyfile
phases: [114, 115, 139, 142, 161, 162, 163, 164]
---

# Deployment

> Docker Compose setup, environment configuration, and production checklist.

## Quick Start

```bash
cd compose/
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Access:

- App (Caddy): `https://localhost`
- Keycloak admin: `https://localhost/admin`
- Provisioning API: `http://localhost:8081`
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`

## Docker Compose Services

Key services in `compose/docker-compose.yml`:

- Edge: `caddy`, `mqtt` (EMQX)
- Identity: `keycloak`, `keycloak-db-init`
- Data: `postgres` (TimescaleDB), `pgbouncer`, `migrator`
- Messaging: `nats` (JetStream), `nats-exporter`, `mqtt-nats-bridge`, `route-delivery`
- Core services: `ui`, `ingest`, `evaluator`, `ops_worker`, `subscription-worker`, `api` (provision_api)
- Observability: `prometheus`, `grafana`
- Object storage (local dev): `minio`, `minio-init`
- Dev helper: `mailpit` (profile `dev`)
- Simulator: `device_sim` (profile `simulator`)

## Environment Variables

Source of truth for required `.env` keys is `compose/.env.example`.

| Variable | Purpose / Notes |
|----------|------------------|
| `HOST_IP` | Host address used in some configs. |
| `KEYCLOAK_URL` | Public Keycloak URL (also used by backend for issuer). |
| `UI_BASE_URL` | Base UI URL used by backend for links. |
| `POSTGRES_PASSWORD` | PostgreSQL password for the `iot` role (DB container). |
| `PG_PASS` | Application DB password (used in service DSNs / PgBouncer config). |
| `ADMIN_KEY` | Admin key for `ui_iot` privileged endpoints (where applicable). |
| `PROVISION_ADMIN_KEY` | Admin key for provisioning API admin endpoints. |
| `KEYCLOAK_ADMIN_USERNAME` | Keycloak admin username. |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password. |
| `KC_DB_PASSWORD` | Keycloak DB password (Keycloak service). |
| `KC_DB_USER_PASSWORD` | Password for Keycloak DB user in Postgres. |
| `KC_HOSTNAME` | Keycloak hostname config. |
| `MQTT_ADMIN_PASSWORD` | MQTT broker admin/service account password. |
| `SMTP_HOST` | SMTP host (Keycloak email flows; optional). |
| `SMTP_PORT` | SMTP port. |
| `SMTP_USERNAME` | SMTP user. |
| `SMTP_PASSWORD` | SMTP password. |
| `SMTP_FROM` | SMTP from address. |
| `SMTP_FROM_DISPLAY_NAME` | Display name for from header. |
| `SMTP_SSL` | SSL/TLS behavior flag. |
| `SMTP_STARTTLS` | STARTTLS behavior flag. |
| `LOG_LEVEL` | Log verbosity. |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (billing UI). |
| `STRIPE_SECRET_KEY` | Stripe secret key (server-side). |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret (server-side). |
| `PROMETHEUS_PORT` | Prometheus external port (default 9090). |
| `GRAFANA_PORT` | Grafana external port (default 3001). |
| `GRAFANA_ADMIN_USER` | Grafana admin user. |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password. |
| `MINIO_ROOT_USER` | MinIO root user (local dev). |
| `MINIO_ROOT_PASSWORD` | MinIO root password (local dev). |
| `S3_PUBLIC_ENDPOINT` | Base URL used for browser downloads (pre-signed URL rewrite in local dev). |
| `S3_ENDPOINT` | Internal S3 endpoint (MinIO in compose). |
| `S3_BUCKET` | Export bucket name (default `exports`). |
| `S3_ACCESS_KEY` | S3 access key (MinIO root user in local dev). |
| `S3_SECRET_KEY` | S3 secret key (MinIO root password in local dev). |
| `S3_REGION` | S3 region (default `us-east-1`). |

## TLS Configuration

## Kubernetes (Helm)

The Kubernetes deployment artifacts live under `helm/pulse/`. Docker Compose is still the recommended local dev environment.

```bash
helm dependency update helm/pulse
helm upgrade --install pulse helm/pulse \
  --namespace pulse --create-namespace \
  -f helm/pulse/values.yaml
```

See:

- `docs/operations/kubernetes.md`
- `docs/operations/managed-postgres.md`

Caddy terminates TLS for both the UI/API and Keycloak using an internal/self-signed CA by default.

- HTTPS listener: `:443`
- HTTP listener: `:80` redirects to HTTPS
- Routing rules are defined in `compose/caddy/Caddyfile`

## Profiles

- `--profile simulator` enables device simulator
- `--profile dev` enables dev-only helpers (e.g. Mailpit)

Examples:

```bash
docker compose --profile simulator up -d --build
docker compose --profile dev up -d
```

## Data Persistence

Compose mounts persist data via volumes/bind mounts:

- Postgres data: `../data/postgres` (bind mount)
- Mosquitto data/passwd: named volumes
- Prometheus/Grafana data: named volumes
- MinIO data: named volume (`minio-data`)

## Rebuilding After Changes

Backend changes:

```bash
cd compose/
docker compose build ui && docker compose up -d ui
```

Frontend changes:

```bash
cd frontend
npm run build
cd ../compose
docker compose restart ui
```

## Production Checklist

- Replace default secrets: `PG_PASS`, `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`, `ADMIN_KEY`, provisioning admin key(s)
- Set explicit CORS origins for production domains
- Set `ENV=PROD` where applicable
- Use real TLS certificates (replace internal CA strategy if required)
- Configure real SMTP (for Keycloak email flows and subscription notifications)
- Establish backup/restore strategy for Postgres (including retention policies for hypertables)
- Lock down exposed ports (publish only intended services)

## Post-Deployment Verification

From the sanity checklist (phases 80–83), verify core UX and health:

- UI loads at `https://localhost/app/` and login works for customer/operator users
- Sidebar groups render and persist collapsed state
- Dashboard widgets render and update timestamps
- Alerts inbox: tabs, bulk actions, silence options, expand detail panel
- Devices split-pane layout and detail tabs render correctly
- No console errors in browser

## See Also

- [Runbook](runbook.md)
- [Monitoring](monitoring.md)
- [Security](security.md)
- [Getting Started](../development/getting-started.md)

