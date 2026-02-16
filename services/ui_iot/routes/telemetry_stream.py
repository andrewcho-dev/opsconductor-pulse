"""Streaming telemetry endpoints: WebSocket and SSE."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from middleware.auth import JWTBearer, validate_token
from middleware.tenant import get_tenant_id, inject_tenant_context, require_customer
from telemetry_stream import MAX_CONNECTIONS_PER_TENANT, stream_manager

logger = logging.getLogger(__name__)

# WebSocket router -- no HTTP auth dependencies (auth via query param token)
ws_router = APIRouter()

# SSE router -- uses standard HTTP auth
sse_router = APIRouter(
    prefix="/api/v1/customer/telemetry",
    tags=["telemetry-stream"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

status_router = APIRouter(prefix="/api/v1", tags=["telemetry-stream"])


def _extract_tenant_from_token(payload: dict) -> str | None:
    """Extract tenant_id from validated JWT payload."""
    orgs = payload.get("organization", {}) or {}
    if isinstance(orgs, dict) and orgs:
        return next(iter(orgs.keys()))
    if isinstance(orgs, list):
        for org in orgs:
            if isinstance(org, str) and org:
                return org
    return payload.get("tenant_id")


def _validate_customer_role(payload: dict) -> bool:
    """Check that the token has a valid customer role."""
    realm_access = payload.get("realm_access", {}) or {}
    roles = realm_access.get("roles", []) or []
    valid_roles = ("customer", "tenant-admin", "operator", "operator-admin")
    return any(role in valid_roles for role in roles)


@ws_router.websocket("/api/v1/customer/telemetry/stream")
async def telemetry_websocket(
    websocket: WebSocket,
    token: str | None = None,
    device_id: str | None = None,
    metric: str | None = None,
):
    """WebSocket endpoint for real-time telemetry streaming.

    Auth: Pass JWT as query param: ws://host/api/v1/customer/telemetry/stream?token=JWT

    Query params (initial filters):
        device_id: comma-separated device IDs (optional)
        metric: comma-separated metric names (optional)
    """
    if not token:
        await websocket.close(code=4001, reason="Missing token parameter")
        return

    try:
        payload = await validate_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    tenant_id = _extract_tenant_from_token(payload)
    if not tenant_id:
        await websocket.close(code=4003, reason="No tenant_id in token")
        return

    if not _validate_customer_role(payload):
        await websocket.close(code=4003, reason="Unauthorized role")
        return

    device_ids = [d.strip() for d in device_id.split(",") if d.strip()] if device_id else None
    metric_names = [m.strip() for m in metric.split(",") if m.strip()] if metric else None

    try:
        sub = stream_manager.register(
            tenant_id=tenant_id,
            device_ids=device_ids,
            metric_names=metric_names,
        )
    except ConnectionError as exc:
        await websocket.close(code=4029, reason=str(exc))
        return

    await websocket.accept()

    await websocket.send_json(
        {
            "type": "connected",
            "tenant_id": tenant_id,
            "filters": {
                "device_ids": list(sub.device_ids),
                "metric_names": list(sub.metric_names),
            },
        }
    )

    async def sender():
        """Read from subscription queue and send to WebSocket."""
        try:
            while True:
                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=30.0)
                    await websocket.send_json(event)
                except asyncio.TimeoutError:
                    await websocket.send_json(
                        {"type": "ping", "ts": datetime.now(timezone.utc).isoformat()}
                    )
        except Exception:
            return

    async def receiver():
        """Read client messages to update filters."""
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "subscribe":
                    next_device_ids = set(sub.device_ids)
                    if "device_id" in data:
                        next_device_ids.add(data["device_id"])
                        stream_manager.update_filters(sub, device_ids=list(next_device_ids))
                        await websocket.send_json({"type": "subscribed", "device_id": data["device_id"]})
                    if "device_ids" in data and isinstance(data["device_ids"], list):
                        for did in data["device_ids"]:
                            next_device_ids.add(did)
                        stream_manager.update_filters(sub, device_ids=list(next_device_ids))
                        await websocket.send_json({"type": "subscribed", "device_ids": data["device_ids"]})

                elif action == "unsubscribe":
                    if "device_id" in data:
                        next_device_ids = set(sub.device_ids)
                        next_device_ids.discard(data["device_id"])
                        stream_manager.update_filters(sub, device_ids=list(next_device_ids))
                        await websocket.send_json(
                            {"type": "unsubscribed", "device_id": data["device_id"]}
                        )

                elif action == "set_metrics":
                    metrics = data.get("metrics", [])
                    stream_manager.update_filters(sub, metric_names=list(metrics) if metrics else [])
                    await websocket.send_json({"type": "metrics_updated", "metrics": list(sub.metric_names)})

                elif action == "clear_filters":
                    stream_manager.update_filters(sub, device_ids=[], metric_names=[])
                    await websocket.send_json({"type": "filters_cleared"})

                else:
                    await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})

        except WebSocketDisconnect:
            return
        except Exception:
            return

    sender_task = asyncio.create_task(sender())
    receiver_task = asyncio.create_task(receiver())

    try:
        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        stream_manager.unregister(sub)
        logger.info(
            "telemetry_stream_disconnected",
            extra={
                "tenant_id": tenant_id,
                "events_sent": sub.event_counter,
                "duration_s": int(asyncio.get_event_loop().time() - sub.connected_at),
            },
        )


@sse_router.get("/stream/sse")
async def telemetry_sse(
    request: Request,
    device_id: str | None = Query(None, description="Comma-separated device IDs"),
    metric: str | None = Query(None, description="Comma-separated metric names"),
):
    """Server-Sent Events endpoint for real-time telemetry streaming."""
    tenant_id = get_tenant_id()

    device_ids = [d.strip() for d in device_id.split(",") if d.strip()] if device_id else None
    metric_names = [m.strip() for m in metric.split(",") if m.strip()] if metric else None

    last_event_id = request.headers.get("Last-Event-ID")

    try:
        sub = stream_manager.register(
            tenant_id=tenant_id,
            device_ids=device_ids,
            metric_names=metric_names,
        )
    except ConnectionError as exc:
        raise HTTPException(429, str(exc))

    async def event_generator():
        event_id = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(sub.queue.get(), timeout=15.0)
                    event_id += 1
                    data = json.dumps(event)
                    yield f"id: {event_id}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
        finally:
            stream_manager.unregister(sub)
            logger.info(
                "telemetry_sse_disconnected",
                extra={"tenant_id": tenant_id, "events_sent": sub.event_counter},
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@status_router.get("/telemetry/stream/status")
async def stream_status():
    """Get streaming connection status (no auth required, for monitoring)."""
    return {
        "total_connections": stream_manager.connection_count,
        "max_per_tenant": MAX_CONNECTIONS_PER_TENANT,
    }

