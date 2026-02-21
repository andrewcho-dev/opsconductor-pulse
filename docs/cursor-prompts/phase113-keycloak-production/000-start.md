# Phase 113 — Keycloak Production Mode

## Goal

Keycloak currently runs in `start-dev` mode which is explicitly not
production-safe. Switch to `start` mode with proper configuration:
- Production start mode (caches enabled, no dev UI shortcuts)
- Separate database from the application (currently shares `iotcloud`)
- SMTP configured for email flows (password reset, verification)
- Hostname fully parameterised — no hardcoded IPs anywhere
- Health check defined in docker-compose

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-keycloak-db.md` | Create dedicated Keycloak database in Postgres |
| `002-keycloak-config.md` | Switch to `start` mode; fix hostname; add health check |
| `003-smtp.md` | Configure SMTP for email flows |
| `004-verify.md` | Login works, realm imported, health check passes, commit |
