# Prompt 002 — Wire JWKS Cache into Auth Middleware

Read `services/ui_iot/auth.py` (or wherever `verify_token` / JWKS fetching happens) fully.
Read `services/ui_iot/app.py` startup lifecycle.
Read `services/shared/jwks_cache.py` (just written).

## Changes

### In `services/ui_iot/app.py` startup:

On `startup` lifespan event, call:
```python
from shared.jwks_cache import init_jwks_cache
jwks_uri = os.environ["KEYCLOAK_JWKS_URI"]  # e.g. http://keycloak:8080/realms/pulse/protocol/openid-connect/certs
cache = init_jwks_cache(jwks_uri, ttl_seconds=int(os.environ.get("JWKS_TTL_SECONDS", "300")))
await cache.get_keys()  # pre-warm
```

### In auth middleware / `verify_token`:

Replace direct JWKS fetch with:
```python
from shared.jwks_cache import get_jwks_cache
keys = await get_jwks_cache().get_keys()
# attempt decode with keys
# if jose raises JWTError with "key not found" or similar, force refresh and retry once:
# keys = await get_jwks_cache().force_refresh()
```

Do NOT change the token decode logic — only replace the key-source.

### Environment Variable

Add `KEYCLOAK_JWKS_URI` to `services/ui_iot/.env.example` (not `.env`):
```
KEYCLOAK_JWKS_URI=http://keycloak:8080/realms/pulse/protocol/openid-connect/certs
JWKS_TTL_SECONDS=300
```

## Acceptance Criteria

- [ ] ui_iot pre-warms JWKS cache on startup
- [ ] Token verification uses cached keys, not per-request Keycloak call
- [ ] On key-not-found error, forces refresh and retries once
- [ ] `KEYCLOAK_JWKS_URI` documented in .env.example
- [ ] `pytest -m unit -v` passes
