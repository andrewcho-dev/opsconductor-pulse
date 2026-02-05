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
