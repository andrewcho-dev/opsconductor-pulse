import sys
sys.path.insert(0, "/app")

import logging
import json
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from shared.rate_limiter import get_rate_limiter
from shared.sampled_logger import get_sampled_logger
from middleware.auth import JWTBearer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest/v1", tags=["ingest"])

# Phase 172: metric_key_map normalization cache (HTTP ingest path).
METRIC_MAP_CACHE_TTL = int(os.getenv("METRIC_MAP_CACHE_TTL", "300"))
METRIC_MAP_CACHE_SIZE = int(os.getenv("METRIC_MAP_CACHE_SIZE", "10000"))


class MetricKeyMapCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 10000):
        self._cache: dict[str, tuple[float, dict[str, str]]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size

    async def get(self, pool, tenant_id: str, device_id: str) -> dict[str, str]:
        cache_key = f"{tenant_id}:{device_id}"
        now = time.time()
        if cache_key in self._cache:
            ts, mapping = self._cache[cache_key]
            if now - ts < self._ttl:
                return mapping

        mapping = await self._load_from_db(pool, tenant_id, device_id)
        if len(self._cache) >= self._max_size:
            oldest = sorted(self._cache.items(), key=lambda x: x[1][0])[: max(1, self._max_size // 4)]
            for k, _ in oldest:
                self._cache.pop(k, None)
        self._cache[cache_key] = (now, mapping)
        return mapping

    async def _load_from_db(self, pool, tenant_id: str, device_id: str) -> dict[str, str]:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE pulse_app")
                await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)
                rows = await conn.fetch(
                    """
                    SELECT metric_key_map
                    FROM device_modules
                    WHERE tenant_id = $1
                      AND device_id = $2
                      AND status = 'active'
                      AND metric_key_map != '{}'::jsonb
                    """,
                    tenant_id,
                    device_id,
                )
        merged: dict[str, str] = {}
        for row in rows:
            mkm = row["metric_key_map"]
            if isinstance(mkm, str):
                try:
                    mkm = json.loads(mkm)
                except Exception:
                    mkm = {}
            if isinstance(mkm, dict):
                merged.update({str(k): str(v) for k, v in mkm.items()})
        return merged


metric_key_map_cache = MetricKeyMapCache(
    ttl_seconds=METRIC_MAP_CACHE_TTL,
    max_size=METRIC_MAP_CACHE_SIZE,
)


async def normalize_telemetry_keys(pool, tenant_id: str, device_id: str, metrics: dict) -> dict:
    if not metrics or not isinstance(metrics, dict):
        return metrics if isinstance(metrics, dict) else {}
    mapping = await metric_key_map_cache.get(pool, tenant_id, device_id)
    if not mapping:
        return metrics
    normalized: dict = {}
    for k, v in metrics.items():
        semantic_key = mapping.get(str(k), str(k))
        normalized[semantic_key] = v
    return normalized


class IngestPayload(BaseModel):
    version: str | None = None
    ts: str | None = None
    site_id: str
    seq: int = 0
    metrics: dict[str, float | int | bool] = {}


class BatchMessage(BaseModel):
    version: str | None = None
    tenant_id: str
    device_id: str
    msg_type: str
    provision_token: str
    ts: str | None = None
    site_id: str
    seq: int = 0
    metrics: dict[str, float | int | bool] = {}


class BatchRequest(BaseModel):
    messages: list[BatchMessage]


class BatchResultItem(BaseModel):
    index: int
    status: str  # "accepted" or "rejected"
    reason: str | None = None
    device_id: str | None = None


class BatchResponse(BaseModel):
    accepted: int
    rejected: int
    results: list[BatchResultItem]


@router.get("/metrics/rate-limits", dependencies=[Depends(JWTBearer())])
async def rate_limit_stats():
    """Return rate limiting statistics for monitoring."""
    rate_limiter = get_rate_limiter()
    return {
        "rate_limit_stats": rate_limiter.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/tenant/{tenant_id}/device/{device_id}/{msg_type}")
async def ingest_single(
    request: Request,
    tenant_id: str,
    device_id: str,
    msg_type: str,
    payload: IngestPayload,
    x_provision_token: str = Header(..., alias="X-Provision-Token"),
):
    """
    Ingest a single telemetry or heartbeat message via HTTP.

    Returns:
        202 Accepted on success
        400 Bad Request for invalid msg_type
        401 Unauthorized for invalid token
        403 Forbidden for revoked device
        429 Too Many Requests for rate limiting
    """
    if msg_type not in ("telemetry", "heartbeat"):
        raise HTTPException(status_code=400, detail="Invalid msg_type. Must be 'telemetry' or 'heartbeat'")

    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="DB not configured")

    # Build payload dict (fast validation only; ingest worker validates async)
    payload_dict = {
        "version": payload.version,
        "ts": payload.ts,
        "site_id": payload.site_id,
        "seq": payload.seq,
        "metrics": (
            await normalize_telemetry_keys(pool, tenant_id, device_id, payload.metrics)
            if msg_type == "telemetry"
            else payload.metrics
        ),
    }
    payload_dict["provision_token"] = x_provision_token

    if not hasattr(request.app.state, "get_nats"):
        raise HTTPException(status_code=503, detail="NATS not configured")
    try:
        nc = await request.app.state.get_nats()
    except Exception as e:
        logger.error("nats_connect_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Ingestion temporarily unavailable")
    if nc is None:
        raise HTTPException(status_code=503, detail="NATS unavailable")

    topic = f"tenant/{tenant_id}/device/{device_id}/{msg_type}"
    envelope = json.dumps(
        {
            "topic": topic,
            "tenant_id": tenant_id,
            "device_id": device_id,
            "msg_type": msg_type,
            "username": "",  # HTTP path has no MQTT username
            "payload": payload_dict,
            "ts": int(time.time() * 1000),
        },
        default=str,
    ).encode()

    try:
        js = nc.jetstream()
        await js.publish(
            f"telemetry.{tenant_id}",
            envelope,
            timeout=1.0,
        )
    except Exception as e:
        logger.error("nats_publish_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Ingestion temporarily unavailable")

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "device_id": device_id, "seq": payload.seq}
    )


@router.post("/batch")
async def ingest_batch(request: Request, batch: BatchRequest):
    """
    Ingest multiple messages in a single request.

    Max 100 messages per batch.
    Each message is validated independently.

    Returns:
        202 Accepted if any messages accepted
        400 Bad Request if all messages rejected or batch too large
    """
    if len(batch.messages) > 100:
        raise HTTPException(status_code=400, detail="Batch exceeds 100 message limit")

    if len(batch.messages) == 0:
        raise HTTPException(status_code=400, detail="Batch is empty")

    if not hasattr(request.app.state, "get_nats"):
        raise HTTPException(status_code=503, detail="NATS not configured")
    try:
        nc = await request.app.state.get_nats()
    except Exception as e:
        logger.error("nats_connect_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail="Ingestion temporarily unavailable")
    if nc is None:
        raise HTTPException(status_code=503, detail="NATS unavailable")

    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="DB not configured")

    results: list[BatchResultItem] = []
    accepted = 0
    rejected = 0

    for idx, msg in enumerate(batch.messages):
        if msg.msg_type not in ("telemetry", "heartbeat"):
            rejected += 1
            results.append(
                BatchResultItem(
                    index=idx,
                    status="rejected",
                    reason="INVALID_MSG_TYPE",
                    device_id=msg.device_id,
                )
            )
            continue

        topic = f"tenant/{msg.tenant_id}/device/{msg.device_id}/{msg.msg_type}"
        payload = msg.model_dump()
        if msg.msg_type == "telemetry":
            payload["metrics"] = await normalize_telemetry_keys(
                pool, msg.tenant_id, msg.device_id, payload.get("metrics", {}) or {}
            )
        envelope = json.dumps(
            {
                "topic": topic,
                "tenant_id": msg.tenant_id,
                "device_id": msg.device_id,
                "msg_type": msg.msg_type,
                "username": "",
                "payload": payload,
                "ts": int(time.time() * 1000),
            },
            default=str,
        ).encode()

        try:
            js = nc.jetstream()
            await js.publish(
                f"telemetry.{msg.tenant_id}",
                envelope,
                timeout=1.0,
            )
            accepted += 1
            results.append(
                BatchResultItem(index=idx, status="accepted", device_id=msg.device_id)
            )
        except Exception:
            rejected += 1
            results.append(
                BatchResultItem(
                    index=idx, status="rejected", reason="publish_failed", device_id=msg.device_id
                )
            )

    status_code = 202 if accepted > 0 else 400
    return JSONResponse(
        status_code=status_code,
        content=BatchResponse(accepted=accepted, rejected=rejected, results=results).model_dump()
    )
