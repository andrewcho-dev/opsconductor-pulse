# Phase 103 — Wire JWKS Cache into JWT Validation

## Step 1: Find the current JWKS/JWT auth code

```bash
grep -rn "jwks\|JWKS\|jwt\|JWK" services/ui_iot/ --include="*.py" -l
```

Most likely in `services/ui_iot/auth.py` or `services/ui_iot/middleware/auth.py`.
Read whichever file contains the token validation logic.

## Step 2: Replace direct JWKS fetch with cache

Current pattern (typical):
```python
async def get_jwks():
    async with httpx.AsyncClient() as client:
        resp = await client.get(JWKS_URI)
        return resp.json()["keys"]
```

New pattern — use the module-level singleton:

```python
# At module level in auth.py:
from shared.jwks_cache import JwksCache
import os

_jwks_cache: JwksCache | None = None

def get_jwks_cache() -> JwksCache:
    global _jwks_cache
    if _jwks_cache is None:
        _jwks_cache = JwksCache(jwks_uri=os.environ["KEYCLOAK_JWKS_URI"])
    return _jwks_cache
```

Replace the JWKS fetch in token validation with:
```python
keys = await get_jwks_cache().get()
```

## Step 3: Start/stop cache in FastAPI lifespan

In `services/ui_iot/app.py`, find the startup/shutdown hooks.

If using `@app.on_event("startup")` / `@app.on_event("shutdown")`:
```python
from auth import get_jwks_cache   # adjust import path as needed

@app.on_event("startup")
async def startup():
    await get_jwks_cache().start()
    # ... other startup ...

@app.on_event("shutdown")
async def shutdown():
    await get_jwks_cache().stop()
```

If using lifespan context manager (newer FastAPI pattern):
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    await get_jwks_cache().start()
    yield
    await get_jwks_cache().stop()

app = FastAPI(lifespan=lifespan)
```

Use whichever pattern already exists in app.py — do not introduce a second startup mechanism.

## Step 4: Add KEYCLOAK_JWKS_URI to docker-compose.yml

Verify that `KEYCLOAK_JWKS_URI` is already set in the `iot-ui` service environment.
If it isn't, add it:

```yaml
services:
  iot-ui:
    environment:
      KEYCLOAK_JWKS_URI: http://keycloak:8080/realms/pulse/protocol/openid-connect/certs
```

Adjust the URL to match the existing `KEYCLOAK_URL` / realm name already in compose.

## Step 5: Verify no other direct JWKS fetches remain

```bash
grep -rn "openid-connect/certs\|jwks_uri\|get_jwks" services/ui_iot/ --include="*.py"
```

All JWKS fetches should now go through `get_jwks_cache().get()`.
