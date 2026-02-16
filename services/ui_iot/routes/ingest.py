import sys
sys.path.insert(0, "/app")

import logging
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from shared.ingest_core import (
    validate_and_prepare,
    IngestResult,
    sha256_hex,
    parse_ts,
    TelemetryRecord,
)
from shared.rate_limiter import get_rate_limiter
from shared.sampled_logger import get_sampled_logger
from middleware.auth import JWTBearer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest/v1", tags=["ingest"])

# Cache for known (tenant_id, device_id) to avoid DB hit on every request
_known_device_cache: set = set()
_known_device_cache_time: float = 0
KNOWN_DEVICE_CACHE_TTL = 60


def get_client_ip(request: Request) -> str:
    """Extract client IP, handling X-Forwarded-For and X-Real-IP."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    if request.scope.get("client"):
        return request.scope["client"][0]
    return "unknown"


async def is_known_device(pool, tenant_id: str, device_id: str) -> bool:
    """Check if device is registered (with 60s TTL cache)."""
    global _known_device_cache, _known_device_cache_time
    now = time.time()
    if now - _known_device_cache_time > KNOWN_DEVICE_CACHE_TTL:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT tenant_id, device_id FROM device_registry"
                )
            _known_device_cache = {(r["tenant_id"], r["device_id"]) for r in rows}
            _known_device_cache_time = now
        except Exception as e:
            logger.warning("Failed to refresh known-device cache: %s", e)
    return (tenant_id, device_id) in _known_device_cache


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

    # Rate limiting (per-device, per-IP, global)
    pool = await request.app.state.get_pool()
    client_ip = get_client_ip(request)
    known = await is_known_device(pool, tenant_id, device_id)
    rate_limiter = get_rate_limiter()
    allowed, reason, status_code = rate_limiter.check_all(
        device_id=device_id, ip=client_ip, is_known_device=known
    )
    if not allowed:
        event_type = "rate_limited_known" if known else "rate_limited_unknown"
        get_sampled_logger().log(
            event_type,
            f"Rate limited: {reason}",
            extra={"device_id": device_id, "ip": client_ip},
        )
        raise HTTPException(
            status_code=status_code,
            detail=reason or "rate_limited",
        )

    # Get shared state
    auth_cache = request.app.state.auth_cache
    batch_writer = request.app.state.batch_writer
    rate_buckets = request.app.state.rate_buckets

    # Build payload dict
    payload_dict = {
        "version": payload.version,
        "ts": payload.ts,
        "site_id": payload.site_id,
        "seq": payload.seq,
        "metrics": payload.metrics,
    }

    result = await validate_and_prepare(
        pool=pool,
        auth_cache=auth_cache,
        rate_buckets=rate_buckets,
        tenant_id=tenant_id,
        device_id=device_id,
        site_id=payload.site_id,
        msg_type=msg_type,
        provision_token=x_provision_token,
        payload=payload_dict,
        max_payload_bytes=request.app.state.max_payload_bytes,
        rps=request.app.state.rps,
        burst=request.app.state.burst,
        require_token=request.app.state.require_token,
    )

    if not result.success:
        reason = result.reason
        if reason == "UNREGISTERED_DEVICE":
            get_sampled_logger().log(
                "unknown_device",
                f"Unknown device: tenant_id={tenant_id} device_id={device_id}",
                extra={"tenant_id": tenant_id, "device_id": device_id},
            )
        elif reason in ("TOKEN_INVALID", "TOKEN_MISSING", "TOKEN_NOT_SET_IN_REGISTRY"):
            get_sampled_logger().log(
                "auth_failure",
                f"Auth failure: {reason} device_id={device_id}",
                extra={"reason": reason, "device_id": device_id},
            )
        elif reason in ("PAYLOAD_TOO_LARGE", "SITE_MISMATCH"):
            get_sampled_logger().log(
                "validation_error",
                f"Validation error: {reason}",
                extra={"reason": reason, "device_id": device_id},
            )
        status_map = {
            "RATE_LIMITED": 429,
            "TOKEN_INVALID": 401,
            "TOKEN_MISSING": 401,
            "TOKEN_NOT_SET_IN_REGISTRY": 401,
            "DEVICE_REVOKED": 403,
            "UNREGISTERED_DEVICE": 403,
            "PAYLOAD_TOO_LARGE": 400,
            "SITE_MISMATCH": 400,
        }
        status = status_map.get(reason, 400)
        raise HTTPException(status_code=status, detail=reason)

    event_ts = parse_ts(payload.ts) or datetime.now(timezone.utc)
    record = TelemetryRecord(
        time=event_ts,
        tenant_id=tenant_id,
        device_id=device_id,
        site_id=payload.site_id,
        msg_type=msg_type,
        seq=payload.seq,
        metrics=payload.metrics,
    )
    await batch_writer.add(record)

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

    # Rate limiting: global and per-IP (batch treated as single request)
    pool = await request.app.state.get_pool()
    client_ip = get_client_ip(request)
    rate_limiter = get_rate_limiter()
    allowed, reason, status_code = rate_limiter.check_all(
        device_id=None, ip=client_ip, is_known_device=False
    )
    if not allowed:
        get_sampled_logger().log(
            "rate_limited_unknown",
            f"Rate limited batch: {reason}",
            extra={"ip": client_ip},
        )
        raise HTTPException(status_code=status_code, detail=reason or "rate_limited")

    # Get shared state
    auth_cache = request.app.state.auth_cache
    batch_writer = request.app.state.batch_writer
    rate_buckets = request.app.state.rate_buckets

    results = []
    accepted = 0
    rejected = 0

    for idx, msg in enumerate(batch.messages):
        # Validate msg_type
        if msg.msg_type not in ("telemetry", "heartbeat"):
            results.append(BatchResultItem(
                index=idx,
                status="rejected",
                reason="INVALID_MSG_TYPE",
                device_id=msg.device_id
            ))
            rejected += 1
            continue

        # Build payload dict
        payload_dict = {
            "version": msg.version,
            "ts": msg.ts,
            "site_id": msg.site_id,
            "seq": msg.seq,
            "metrics": msg.metrics,
        }

        result = await validate_and_prepare(
            pool=pool,
            auth_cache=auth_cache,
            rate_buckets=rate_buckets,
            tenant_id=msg.tenant_id,
            device_id=msg.device_id,
            site_id=msg.site_id,
            msg_type=msg.msg_type,
            provision_token=msg.provision_token,
            payload=payload_dict,
            max_payload_bytes=request.app.state.max_payload_bytes,
            rps=request.app.state.rps,
            burst=request.app.state.burst,
            require_token=request.app.state.require_token,
        )

        if result.success:
            event_ts = parse_ts(msg.ts) or datetime.now(timezone.utc)
            record = TelemetryRecord(
                time=event_ts,
                tenant_id=msg.tenant_id,
                device_id=msg.device_id,
                site_id=msg.site_id,
                msg_type=msg.msg_type,
                seq=msg.seq,
                metrics=msg.metrics,
            )
            await batch_writer.add(record)
            results.append(BatchResultItem(
                index=idx,
                status="accepted",
                device_id=msg.device_id
            ))
            accepted += 1
        else:
            results.append(BatchResultItem(
                index=idx,
                status="rejected",
                reason=result.reason,
                device_id=msg.device_id
            ))
            rejected += 1

    status_code = 202 if accepted > 0 else 400
    return JSONResponse(
        status_code=status_code,
        content=BatchResponse(accepted=accepted, rejected=rejected, results=results).model_dump()
    )
