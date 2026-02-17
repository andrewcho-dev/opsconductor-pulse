---
last-verified: 2026-02-17
sources:
  - services/ui_iot/middleware/auth.py
  - compose/mosquitto/mosquitto.tls.conf
  - compose/mosquitto/acl.conf
  - compose/caddy/Caddyfile
phases: [36, 97, 110, 112, 113, 114, 115, 120, 131, 142]
---

# Security

> Secrets management, TLS, RBAC, and hardening.

## Authentication

- Keycloak OIDC/PKCE for browser login
- JWT bearer tokens for API access
- JWT validation uses Keycloak JWKS (cached) and verifies issuer/audience/expiry

## Secrets Management

Key secrets (configured via compose `.env`):

- Postgres passwords (`POSTGRES_PASSWORD`, `PG_PASS`)
- Keycloak admin credentials (`KEYCLOAK_ADMIN_PASSWORD`) and DB credentials
- MQTT admin/service password (`MQTT_ADMIN_PASSWORD`)
- Provisioning/admin keys (`ADMIN_KEY`, provisioning admin key)
- Stripe secrets (if enabled)
- SMTP credentials (if enabled)

Rotation guidance:

- Rotate secrets in `.env`, restart dependent services.
- For tokens/keys used by external clients (devices/webhooks), plan rotation windows and dual-acceptance where applicable.

## TLS

### HTTPS (Caddy)

Caddy terminates TLS on `:443` and routes:

- `/realms/*`, `/admin/*`, etc. → Keycloak
- everything else → `ui_iot`

### MQTT (Mosquitto)

Mosquitto config (`compose/mosquitto/mosquitto.tls.conf`) enforces TLS on listeners:

- Internal TLS listener: 1883
- External TLS listener: 8883
- WebSocket TLS listener: 9001

TLS uses CA + server cert/key mounted under `compose/mosquitto/certs/`.

### Device Certificates (X.509)

Device certificate lifecycle is managed by certificate endpoints and operational workers (CRL generation, expiry warnings) depending on deployment.

## Authorization

### Role-Based Access Control

Roles (Keycloak realm roles):

- customer plane: `customer`, `tenant-admin`
- operator plane: `operator`, `operator-admin`

### Row-Level Security (PostgreSQL)

Tenant isolation is enforced in DB via:

- `tenant_connection()` setting `SET LOCAL ROLE pulse_app` + `app.tenant_id`
- RLS policies that filter tenant-scoped tables by `app.tenant_id`

Operator bypass:

- `operator_connection()` uses `SET LOCAL ROLE pulse_operator` (BYPASSRLS)
- Operator access should be audited

### MQTT ACLs

`compose/mosquitto/acl.conf` provides coarse-grained topic ACLs:

- Service account has broad access.
- Device patterns allow read/write to allowed topic structures.
- Fine-grained tenant/device enforcement is implemented by the ingestion pipeline which validates topic/registry/cert state.

## API Security

### SSRF Protection

Webhook destinations are validated (production hardening) to prevent internal network access.

### CSRF Protection

Customer UI/API flows use cookie + header token conventions for CSRF protection in browser contexts.

### Rate Limiting

- Auth attempts are rate-limited per client IP.
- Some API routes are rate-limited (SlowAPI).
- Ingestion is rate-limited per tenant/device token bucket.

## Audit Logging

- Auth successes/failures are recorded for security visibility.
- Operator endpoints should record access audit logs.
- Request-context audit events are buffered and flushed asynchronously.

## See Also

- [Tenant Isolation](../architecture/tenant-isolation.md)
- [Runbook](runbook.md)
- [Monitoring](monitoring.md)

