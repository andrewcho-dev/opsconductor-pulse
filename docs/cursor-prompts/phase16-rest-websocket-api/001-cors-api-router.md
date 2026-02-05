# Task 001: CORS Middleware + API v2 Router Foundation

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

**THE PROBLEM**: The UI service only serves server-rendered HTML pages. External dashboards, mobile apps, and third-party integrations cannot consume device data programmatically. There is no CORS support, no clean REST API, and no WebSocket endpoint.

**Read first**:
- `services/ui_iot/app.py` — focus on: `app = FastAPI()` (line 31), router mounts (lines 35-36), existing imports (lines 1-18)
- `services/ui_iot/routes/customer.py` — focus on: router definition (lines 292-300), auth dependency pattern, `get_pool()` pattern (lines 91-103)
- `services/ui_iot/middleware/auth.py` — focus on: `JWTBearer` class (lines 102-119), `validate_token` function (lines 77-99)
- `services/ui_iot/middleware/tenant.py` — focus on: `inject_tenant_context`, `require_customer`, `get_tenant_id`

---

## Task

### 1.1 Add CORS middleware to app.py

**File**: `services/ui_iot/app.py`

Add import near the top with other imports (after the `from starlette.requests import Request` line):

```python
from starlette.middleware.cors import CORSMiddleware
```

Add env var after the existing env vars (after `PROVISION_ADMIN_KEY`, around line 29):

```python
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "*")
```

Add CORS middleware AFTER `app = FastAPI()` (after line 31) and BEFORE `app.mount("/static", ...)` (line 33):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 1.2 Create API v2 router file

**File**: `services/ui_iot/routes/api_v2.py` (NEW)

Create a new router file. This follows the same auth/pool pattern as customer.py but:
- Prefix is `/api/v2` instead of `/customer`
- All responses are JSON (no template rendering)
- Includes in-memory rate limiting
- Includes a `ws_router` for WebSocket (no HTTP auth deps — WebSocket handles auth manually)

```python
import os
import time
import logging
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

import asyncpg
import httpx

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, require_customer, get_tenant_id, get_user
from db.pool import tenant_connection

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))
API_RATE_WINDOW = int(os.getenv("API_RATE_WINDOW_SECONDS", "60"))


pool: asyncpg.Pool | None = None
_influx_client: httpx.AsyncClient | None = None


def _get_influx_client() -> httpx.AsyncClient:
    global _influx_client
    if _influx_client is None:
        _influx_client = httpx.AsyncClient(timeout=10.0)
    return _influx_client


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB,
            user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5,
        )
    return pool


# --- In-memory rate limiter ---
_rate_buckets: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(tenant_id: str) -> bool:
    """Return True if request is allowed, False if rate limit exceeded."""
    now = time.time()
    bucket = _rate_buckets[tenant_id]
    cutoff = now - API_RATE_WINDOW
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= API_RATE_LIMIT:
        return False
    bucket.append(now)
    return True


async def enforce_rate_limit():
    """FastAPI dependency that enforces per-tenant API rate limiting."""
    tenant_id = get_tenant_id()
    if not _check_rate_limit(tenant_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({API_RATE_LIMIT} requests per {API_RATE_WINDOW}s)",
        )


router = APIRouter(
    prefix="/api/v2",
    tags=["api-v2"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
        Depends(enforce_rate_limit),
    ],
)

# Separate router for WebSocket — no HTTP auth dependencies
# (WebSocket auth is handled inside the endpoint via query param token)
ws_router = APIRouter()
```

**Important**: The file creates TWO router objects:
- `router` — for authenticated REST endpoints (mounted with JWTBearer deps)
- `ws_router` — for WebSocket endpoint (no HTTP auth deps, auth done inside handler)

Both will be mounted in app.py. Task 4 adds the WebSocket endpoint to `ws_router`.

### 1.3 Add unauthenticated health endpoint

**File**: `services/ui_iot/app.py`

Add a health check endpoint that does NOT require auth. Place it after the `@app.post("/settings")` route (after line 180):

```python
@app.get("/api/v2/health")
async def api_v2_health():
    return {"status": "ok", "service": "pulse-ui", "api_version": "v2"}
```

### 1.4 Mount API v2 routers in app.py

**File**: `services/ui_iot/app.py`

Add import near the other router imports (near lines 16-17, after `from routes.operator import router as operator_router`):

```python
from routes.api_v2 import router as api_v2_router, ws_router as api_v2_ws_router
```

Add the router mounts after the existing router mounts (after `app.include_router(operator_router)`, line 36):

```python
app.include_router(api_v2_router)
app.include_router(api_v2_ws_router)
```

### 1.5 Add env vars to docker-compose

**File**: `compose/docker-compose.yml`

In the `ui` service environment section (after the `INFLUXDB_TOKEN` line, around line 198), add:

```yaml
      CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-*}"
      API_RATE_LIMIT: "${API_RATE_LIMIT:-100}"
      API_RATE_WINDOW_SECONDS: "${API_RATE_WINDOW_SECONDS:-60}"
      WS_POLL_SECONDS: "${WS_POLL_SECONDS:-5}"
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/app.py` | Add CORSMiddleware, health endpoint, mount api_v2 routers |
| CREATE | `services/ui_iot/routes/api_v2.py` | API v2 router with auth + rate limiting + ws_router stub |
| MODIFY | `compose/docker-compose.yml` | Add CORS, rate limit, WS env vars |

---

## Test

### Step 1: Run existing unit tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All existing tests must pass. The CORS middleware and new router don't affect existing functionality.

### Step 2: Verify code structure

Read the files and confirm:
- [ ] CORSMiddleware imported and added with configurable origins
- [ ] CORS_ALLOWED_ORIGINS env var defaults to `"*"`
- [ ] api_v2.py has `router` with prefix `/api/v2` and proper auth dependencies
- [ ] api_v2.py has `ws_router` with no dependencies (empty)
- [ ] Health endpoint at `/api/v2/health` returns JSON without auth
- [ ] Both routers imported and mounted in app.py
- [ ] In-memory rate limiter with `_check_rate_limit` function
- [ ] `enforce_rate_limit` dependency added to router
- [ ] Docker-compose has all 4 new env vars

---

## Acceptance Criteria

- [ ] CORSMiddleware configured with CORS_ALLOWED_ORIGINS env var
- [ ] API v2 router created with JWTBearer + tenant context + rate limiting
- [ ] Separate ws_router created for future WebSocket endpoint
- [ ] Health endpoint returns JSON at /api/v2/health without auth
- [ ] Both routers mounted in app.py
- [ ] All existing tests pass

---

## Commit

```
Add CORS middleware and API v2 router foundation

CORSMiddleware with configurable origins, API v2 router with
JWT auth, tenant scoping, and in-memory rate limiting.
Health check endpoint at /api/v2/health.

Phase 16 Task 1: CORS + API Router
```
