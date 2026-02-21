---
last-verified: 2026-02-20
sources:
  - compose/docker-compose.yml
  - compose/.env.example
  - README.md
phases: [142, 193, 195, 204]
---

# Getting Started

> Clone → configure → run → verify.

## Prerequisites

- Docker + Docker Compose v2
- Node.js 18+ and npm (frontend development)
- Python 3.10+ (tests and scripts)
- Git

## Clone & Configure

```bash
git clone <repo-url>
cd simcloud/compose
cp .env.example .env
```

Edit `compose/.env` and set strong values for secrets (DB passwords, Keycloak admin password, admin keys).

Before starting services, fill all required credential variables in `.env` (see `compose/.env.example`). Services now fail at startup if required credential values are missing.

Generate local MQTT TLS certificates before first `docker compose up`:

```bash
bash scripts/generate-dev-certs.sh
```

## Start the Platform

```bash
cd compose/
docker compose up -d --build
```

## Verify Everything is Running

```bash
docker compose ps
```

Access:

- App: `https://localhost` (accept self-signed certificate warning)
- Keycloak Admin: `https://localhost/admin` (credentials from your populated `.env`)
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`
- Provisioning API: `http://localhost:8081`

Default dev users (from `README.md`):

- `customer1 / test123`
- `operator1 / test123`

## Start the Device Simulator

```bash
cd compose/
docker compose --profile simulator up -d
```

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Vite dev server runs on `http://localhost:5173` and proxies API calls to the backend.

Optional frontend observability env var:

- `VITE_SENTRY_DSN=` (leave blank for local development)

## Running Tests Locally

```bash
pytest tests/unit/ -m unit -q
```

## Project Layout

- `compose/` — Docker Compose config (Caddy, Keycloak, Postgres, services, observability)
- `services/` — backend services (`ui_iot`, `ingest_iot`, `evaluator_iot`, etc.)
- `frontend/` — React SPA (Vite)
- `db/` — migrations + migration runner
- `docs/` — documentation hub
- `tests/` — unit/integration/e2e tests

## Common Tasks

- Rebuild backend after Python change: `cd compose && docker compose build ui && docker compose up -d ui`
- Build frontend: `cd frontend && npm run build`
- Apply migrations: `python db/migrate.py`

## See Also

- [Deployment](../operations/deployment.md)
- [Testing](testing.md)
- [Frontend](frontend.md)

