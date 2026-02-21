# Phase 50: Keycloak Resilience

## What This Phase Adds

Keycloak is a hard dependency for every authenticated request. If Keycloak is
temporarily unreachable (restart, network blip), currently:
- Token verification fails immediately
- All API requests return 401/500
- Background services that use service accounts may crash

This phase adds resilience patterns so the system degrades gracefully:

1. **JWKS key caching with TTL** — cache public keys locally, refresh only on 401 or TTL expiry (default 5 min). Eliminates per-request Keycloak calls.
2. **Retry with exponential backoff** — on JWKS fetch failure, retry up to 3 times before failing.
3. **Startup key pre-warm** — fetch JWKS on service startup so the first request doesn't add latency.
4. **Health endpoint Keycloak check** — `/healthz` reports Keycloak reachability as a non-fatal warning (not a hard failure).
5. **Service account token caching** — for internal service-to-service calls, cache the client_credentials token until near expiry.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | JWKS cache module in shared/ |
| 002 | Wire JWKS cache into ui_iot auth middleware |
| 003 | Health check Keycloak status |
| 004 | Unit tests |
| 005 | Verify |

## Key Files

- `services/shared/jwks_cache.py` — new module (prompt 001)
- `services/ui_iot/auth.py` or wherever token verification lives — prompt 002
- `services/ui_iot/routes/health.py` or `app.py` healthz route — prompt 003
- `tests/unit/test_jwks_cache.py` — prompt 004
