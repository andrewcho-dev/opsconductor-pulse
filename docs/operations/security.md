---
last-verified: 2026-02-20
sources:
  - services/ui_iot/middleware/auth.py
  - services/ui_iot/app.py
  - services/ui_iot/routes/api_v2.py
  - frontend/src/services/websocket/manager.ts
  - services/provision_api/app.py
  - db/migrations/117_operator_role_granularity.sql
  - compose/emqx/emqx.conf
  - compose/caddy/Caddyfile
phases: [36, 97, 110, 112, 113, 114, 115, 120, 131, 142, 161, 162, 165, 194, 197, 205, 209, 212]
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

### MQTT (EMQX)

EMQX config (`compose/emqx/emqx.conf`) enforces TLS on listeners:

- Internal TCP listener: 1883 (compose internal network)
- External TLS listener: 8883 (device mTLS)
- WebSocket listener: 9001

TLS uses CA + server cert/key mounted under `compose/mosquitto/certs/` (reused for EMQX via `/certs` mount).

EMQX dashboard is available on port 18083. Treat it as privileged access.

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

- `operator_read_connection()` uses `SET LOCAL ROLE pulse_operator_read` (BYPASSRLS) for read-only operator access.
- `operator_write_connection()` uses `SET LOCAL ROLE pulse_operator_write` for scoped operational writes.
- Legacy `operator_connection()` is deprecated and mapped to read-role behavior during transition.

### MQTT ACLs
EMQX enforces per-device topic ACLs at the broker level via internal HTTP endpoints in `ui_iot`:

- `/api/v1/internal/mqtt-auth`
- `/api/v1/internal/mqtt-acl`

These endpoints are protected by the `MQTT_INTERNAL_AUTH_SECRET` shared secret and are blocked from external access by Caddy (`/api/v1/internal/*` responds 404).

### NATS (Internal Bus)

Devices never connect directly to NATS. NATS JetStream is used for internal service-to-service messaging (ingest + route delivery).

In docker-compose the NATS server is only published on `127.0.0.1` for the host (and is otherwise internal to the compose network). For production/Kubernetes, enable NATS authentication/authorization per your environment requirements.

## API Security

### SSRF Protection

Webhook destinations are validated (production hardening) to prevent internal network access.

### CSRF Protection

Customer UI/API flows use cookie + header token conventions for CSRF protection in browser contexts.
The CSRF cookie is set as `HttpOnly` and `SameSite=Strict`, and the token value is
returned to the browser in the `X-CSRF-Token` response header for in-memory client use.

### CORS

`ui_iot` CORS uses explicit origins and an explicit request-header allowlist.
There is no wildcard default in compose for allowed origins.

### Rate Limiting

- Auth attempts are rate-limited per client IP.
- Some API routes are rate-limited (SlowAPI).
- Ingestion is rate-limited per tenant/device token bucket.
- Provision API admin endpoints enforce per-IP rate limiting (10 requests/minute).

### Stripe Webhook Security

Stripe webhooks are secured with layered controls:

- Signature verification is required for every webhook (`stripe.Webhook.construct_event` on raw request bytes).
- Missing/invalid signatures return HTTP 400 and are not processed.
- Event processing is idempotent using `stripe_events` keyed by Stripe `event.id`, enforced atomically via a single `INSERT ... ON CONFLICT DO NOTHING RETURNING event_id` (no pre-check SELECT, no race window).
- Only known billing event types are handled; unknown event types are acknowledged and ignored.
- Critical subscription state is re-fetched from Stripe API where needed instead of trusting webhook payload blindly.
- Logs avoid sensitive payment fields; use non-sensitive identifiers (event/subscription IDs).

### Provisioning Admin Key

- Provision API admin key comparison uses constant-time `secrets.compare_digest`.
- `ADMIN_KEY` must be at least 32 characters; short values fail startup.

## Audit Logging

- Auth successes/failures are recorded for security visibility.
- Operator endpoints should record access audit logs.
- Request-context audit events are buffered and flushed asynchronously.

## See Also

- [Tenant Isolation](../architecture/tenant-isolation.md)
- [Runbook](runbook.md)
- [Monitoring](monitoring.md)

