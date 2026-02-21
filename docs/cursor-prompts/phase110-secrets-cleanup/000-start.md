# Phase 110 — Secrets Extraction + .env Cleanup

## Goal

Remove all hardcoded credentials from the repository. Every secret must come
from environment variables with no hardcoded fallback values in
docker-compose.yml. The `.env` file must not contain real values and must
not be committed.

## What is hardcoded today (must fix)

| Location | Variable | Current value |
|----------|---------|--------------|
| docker-compose.yml | `POSTGRES_PASSWORD` | `iot_dev` |
| docker-compose.yml | `PG_PASS` (all services) | `iot_dev` |
| docker-compose.yml | `DATABASE_URL` | `postgresql://iot:iot_dev@...` |
| docker-compose.yml | `ADMIN_KEY` | `change-me-now` |
| docker-compose.yml | `PROVISION_ADMIN_KEY` | `change-me-now` |
| docker-compose.yml | `KEYCLOAK_ADMIN_PASSWORD` | `admin_dev` |
| docker-compose.yml | `KC_DB_PASSWORD` | `iot_dev` |
| docker-compose.yml | `KC_HOSTNAME` | `192.168.10.53` (hardcoded, not parameterised) |
| docker-compose.yml | `KEYCLOAK_PUBLIC_URL` default | `https://192.168.10.53` |
| compose/.env | `HOST_IP` | `192.168.10.53` |
| compose/.env | `KEYCLOAK_URL` | `https://192.168.10.53` |
| compose/.env | `UI_BASE_URL` | `https://192.168.10.53` |

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-env-template.md` | Create `.env.example`, scrub `.env`, add `.env` to `.gitignore` |
| `002-compose-secrets.md` | Replace all hardcoded secrets in docker-compose.yml with `${VAR}` references |
| `003-app-code-audit.md` | Fix `maintenance/log_cleanup.py` hardcoded DB URL; fix subscription-worker PgBouncer hostname |
| `004-verify.md` | Confirm no secrets in repo, docker compose config validates, commit |
