---
last-verified: 2026-02-17
sources:
  - compose/keycloak/realm-pulse.json
  - compose/docker-compose.yml
  - services/ui_iot/services/keycloak_admin.py
phases: [4, 36, 97, 142]
---

# keycloak

> Identity provider configuration (OIDC/PKCE, roles, organizations).

## Overview

Keycloak provides authentication and authorization for:

- Browser SPA login (OIDC + PKCE)
- API JWT bearer tokens validated by `ui_iot`
- Operator vs customer role separation
- Organization/tenant membership claims

Realm: `pulse`

## Architecture

Key elements:

- Realm roles: `customer`, `tenant-admin`, `operator`, `operator-admin`
- SPA client is configured as a public OIDC client with PKCE enabled
- `ui_iot` validates JWT tokens using Keycloak JWKS and caches keys
- `ui_iot` contains an admin API client (`keycloak_admin.py`) for user management workflows

## Configuration

Keycloak itself is configured via compose environment and realm export. `ui_iot` also reads Keycloak-related env vars.

Keycloak admin client (`services/ui_iot/services/keycloak_admin.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_INTERNAL_URL` | `http://pulse-keycloak:8080` | Internal Keycloak base URL used by backend services. |
| `KEYCLOAK_REALM` | `pulse` | Realm name. |
| `KEYCLOAK_ADMIN_USERNAME` | `admin` | Admin username for Keycloak REST admin API. |
| `KEYCLOAK_ADMIN_PASSWORD` | empty | Admin password for Keycloak REST admin API. |

JWT validation in `ui_iot` (see auth middleware) additionally uses:

- `KEYCLOAK_PUBLIC_URL`, `KEYCLOAK_INTERNAL_URL`, `KEYCLOAK_REALM`
- `JWT_AUDIENCE`, `KEYCLOAK_JWKS_URI`, `JWKS_TTL_SECONDS`

## Health & Metrics

- Keycloak health is checked via the reverse proxy and internal health checks in compose.

## Dependencies

- PostgreSQL database (Keycloak DB in compose)
- Caddy reverse proxy (exposes Keycloak paths under HTTPS)

## Troubleshooting

- Login failures: verify realm import (`realm-pulse.json`) and client redirect URIs.
- JWKS issues in `ui_iot`: confirm Keycloak URLs and realm name; check JWKS cache TTL.
- Admin API failures: confirm `KEYCLOAK_ADMIN_PASSWORD` is set and internal URL is reachable from `ui_iot`.

## See Also

- [Tenant Isolation](../architecture/tenant-isolation.md)
- [Security](../operations/security.md)
- [Service: ui-iot](ui-iot.md)

