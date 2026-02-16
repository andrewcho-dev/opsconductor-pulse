import json
import logging
import re
from functools import lru_cache
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db.pool import tenant_connection
from dependencies import get_db_pool
from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, inject_tenant_context, require_customer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["message-routing"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class MessageRouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    topic_filter: str = Field(..., min_length=1, max_length=200)
    destination_type: Literal["webhook", "mqtt_republish", "postgresql"]
    destination_config: dict = Field(default_factory=dict)
    payload_filter: Optional[dict] = None
    is_enabled: bool = True


class MessageRouteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    topic_filter: Optional[str] = Field(default=None, min_length=1, max_length=200)
    destination_type: Optional[Literal["webhook", "mqtt_republish", "postgresql"]] = None
    destination_config: Optional[dict] = None
    payload_filter: Optional[dict] = None
    is_enabled: Optional[bool] = None


class TestRouteRequest(BaseModel):
    topic: str = "tenant/test/device/DEV-001/telemetry"
    payload: dict = Field(default_factory=lambda: {"metrics": {"temperature": 90}})


class ReplayBatchRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)


class PurgeRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1, le=365)


MQTT_TOPIC_PATTERN = re.compile(r"^[a-zA-Z0-9_/+#-]+$")


def validate_topic_filter(topic_filter: str) -> None:
    """Validate MQTT topic filter syntax."""
    if not MQTT_TOPIC_PATTERN.match(topic_filter):
        raise HTTPException(400, "Invalid topic filter: contains illegal characters")
    parts = topic_filter.split("/")
    for i, part in enumerate(parts):
        if part == "#" and i != len(parts) - 1:
            raise HTTPException(400, "Invalid topic filter: # wildcard must be last segment")
        if "+" in part and part != "+":
            raise HTTPException(400, "Invalid topic filter: + must occupy entire segment")
        if "#" in part and part != "#":
            raise HTTPException(400, "Invalid topic filter: # must occupy entire segment")


def validate_destination_config(destination_type: str, config: dict) -> None:
    """Validate destination_config has required keys."""
    if destination_type == "webhook":
        if "url" not in config:
            raise HTTPException(422, "webhook destination requires 'url' in destination_config")
    elif destination_type == "mqtt_republish":
        if "topic" not in config:
            raise HTTPException(422, "mqtt_republish destination requires 'topic' in destination_config")


@lru_cache(maxsize=1024)
def _compile_topic_regex(topic_filter: str) -> re.Pattern:
    parts = topic_filter.split("/")
    regex_parts: list[str] = []
    for part in parts:
        if part == "+":
            regex_parts.append("[^/]+")
        elif part == "#":
            regex_parts.append(".*")
            break
        else:
            regex_parts.append(re.escape(part))
    pattern = "^" + "/".join(regex_parts) + "$"
    return re.compile(pattern)


def mqtt_topic_matches(topic_filter: str, topic: str) -> bool:
    regex = _compile_topic_regex(topic_filter)
    return regex.match(topic) is not None


def evaluate_payload_filter(filter_spec: dict, payload: dict) -> bool:
    """Evaluate a simple payload filter against a message payload."""
    if not filter_spec:
        return True

    metrics = payload.get("metrics", {}) or {}

    for key, condition in filter_spec.items():
        value = metrics.get(key)
        if value is None:
            value = payload.get(key)
        if value is None:
            return False

        if isinstance(condition, dict):
            for op, threshold in condition.items():
                try:
                    value_num = float(value)
                    threshold_num = float(threshold)
                except (TypeError, ValueError):
                    return False

                if op == "$gt" and not (value_num > threshold_num):
                    return False
                elif op == "$gte" and not (value_num >= threshold_num):
                    return False
                elif op == "$lt" and not (value_num < threshold_num):
                    return False
                elif op == "$lte" and not (value_num <= threshold_num):
                    return False
                elif op == "$eq" and not (value_num == threshold_num):
                    return False
                elif op == "$ne" and not (value_num != threshold_num):
                    return False
        else:
            if str(value) != str(condition):
                return False

    return True


@router.get("/message-routes")
async def list_message_routes(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, name, topic_filter, destination_type,
                   destination_config, payload_filter, is_enabled, created_at, updated_at
            FROM message_routes
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id,
            limit,
            offset,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM message_routes WHERE tenant_id = $1",
            tenant_id,
        )
    return {
        "routes": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/message-routes", status_code=201)
async def create_message_route(body: MessageRouteCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    validate_topic_filter(body.topic_filter)
    validate_destination_config(body.destination_type, body.destination_config)

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO message_routes
                (tenant_id, name, topic_filter, destination_type, destination_config,
                 payload_filter, is_enabled)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)
            RETURNING id, tenant_id, name, topic_filter, destination_type,
                      destination_config, payload_filter, is_enabled, created_at, updated_at
            """,
            tenant_id,
            body.name.strip(),
            body.topic_filter,
            body.destination_type,
            json.dumps(body.destination_config),
            json.dumps(body.payload_filter) if body.payload_filter else None,
            body.is_enabled,
        )
    return dict(row)


@router.put("/message-routes/{route_id}")
async def update_message_route(route_id: int, body: MessageRouteUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    if body.topic_filter is not None:
        validate_topic_filter(body.topic_filter)
    if body.destination_type is not None and body.destination_config is not None:
        validate_destination_config(body.destination_type, body.destination_config)

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id,
            route_id,
        )
        if not existing:
            raise HTTPException(404, "Message route not found")

        updates: dict[str, object] = {}
        if body.name is not None:
            updates["name"] = body.name.strip()
        if body.topic_filter is not None:
            updates["topic_filter"] = body.topic_filter
        if body.destination_type is not None:
            updates["destination_type"] = body.destination_type
        if body.destination_config is not None:
            updates["destination_config"] = json.dumps(body.destination_config)
        if body.payload_filter is not None:
            updates["payload_filter"] = json.dumps(body.payload_filter)
        if body.is_enabled is not None:
            updates["is_enabled"] = body.is_enabled

        if not updates:
            return dict(existing)

        set_clauses = []
        params: list[object] = [tenant_id, route_id]
        for i, (col, val) in enumerate(updates.items(), start=3):
            suffix = "::jsonb" if col in ("destination_config", "payload_filter") else ""
            set_clauses.append(f"{col} = ${i}{suffix}")
            params.append(val)

        set_clauses.append("updated_at = NOW()")
        set_sql = ", ".join(set_clauses)

        row = await conn.fetchrow(
            f"""
            UPDATE message_routes
            SET {set_sql}
            WHERE tenant_id = $1 AND id = $2
            RETURNING id, tenant_id, name, topic_filter, destination_type,
                      destination_config, payload_filter, is_enabled, created_at, updated_at
            """,
            *params,
        )
    if not row:
        raise HTTPException(404, "Message route not found")
    return dict(row)


@router.delete("/message-routes/{route_id}", status_code=204)
async def delete_message_route(route_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            "DELETE FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id,
            route_id,
        )
    if res.endswith("0"):
        raise HTTPException(404, "Message route not found")
    from fastapi.responses import Response

    return Response(status_code=204)


@router.get("/dead-letter")
async def list_dead_letter(
    status: Optional[str] = Query(
        None,
        description="Filter by status: FAILED, REPLAYED, DISCARDED",
    ),
    route_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()

    conditions = ["d.tenant_id = $1"]
    params: list[object] = [tenant_id]

    if status:
        if status.upper() not in ("FAILED", "REPLAYED", "DISCARDED"):
            raise HTTPException(400, "Invalid status filter")
        params.append(status.upper())
        conditions.append(f"d.status = ${len(params)}")

    if route_id is not None:
        params.append(route_id)
        conditions.append(f"d.route_id = ${len(params)}")

    where_clause = " AND ".join(conditions)
    params.extend([limit, offset])

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT d.id, d.tenant_id, d.route_id, d.original_topic, d.payload,
                   d.destination_type, d.destination_config, d.error_message,
                   d.attempts, d.status, d.created_at, d.replayed_at,
                   mr.name AS route_name
            FROM dead_letter_messages d
            LEFT JOIN message_routes mr ON mr.id = d.route_id AND mr.tenant_id = d.tenant_id
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        count_params = params[:-2]  # Remove limit/offset
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM dead_letter_messages d WHERE {where_clause}",
            *count_params,
        )

    return {
        "messages": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/dead-letter/replay-batch")
async def replay_dead_letter_batch(body: ReplayBatchRequest, pool=Depends(get_db_pool)):
    """Replay multiple dead letter messages."""
    tenant_id = get_tenant_id()
    results: list[dict[str, object]] = []

    for dlq_id in body.ids:
        try:
            async with tenant_connection(pool, tenant_id) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, route_id, original_topic, payload, destination_type,
                           destination_config, attempts, status
                    FROM dead_letter_messages
                    WHERE tenant_id = $1 AND id = $2 AND status = 'FAILED'
                    """,
                    tenant_id,
                    dlq_id,
                )

            if not row:
                results.append(
                    {
                        "id": dlq_id,
                        "status": "SKIPPED",
                        "error": "Not found or not in FAILED status",
                    }
                )
                continue

            config = row["destination_config"] or {}
            if isinstance(config, str):
                config = json.loads(config)
            payload = row["payload"] or {}
            if isinstance(payload, str):
                payload = json.loads(payload)

            delivery_error: str | None = None
            try:
                if row["destination_type"] == "webhook":
                    url = config.get("url")
                    if not url:
                        raise Exception("No URL in destination config")
                    method = config.get("method", "POST").upper()
                    headers = {"Content-Type": "application/json"}
                    body_bytes = json.dumps(payload, default=str).encode()
                    secret = config.get("secret")
                    if secret:
                        import hashlib
                        import hmac as hmac_mod

                        sig = hmac_mod.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                        headers["X-Signature-256"] = f"sha256={sig}"

                    import httpx

                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.request(method, url, content=body_bytes, headers=headers)
                        if resp.status_code >= 400:
                            raise Exception(f"HTTP {resp.status_code}")
                else:
                    raise Exception(f"Replay not supported for {row['destination_type']}")
            except Exception as exc:
                delivery_error = str(exc)

            async with tenant_connection(pool, tenant_id) as conn:
                if delivery_error:
                    await conn.execute(
                        """
                        UPDATE dead_letter_messages
                        SET attempts = attempts + 1, error_message = $3
                        WHERE tenant_id = $1 AND id = $2
                        """,
                        tenant_id,
                        dlq_id,
                        delivery_error[:2000],
                    )
                    results.append({"id": dlq_id, "status": "FAILED", "error": delivery_error})
                else:
                    await conn.execute(
                        """
                        UPDATE dead_letter_messages
                        SET status = 'REPLAYED', replayed_at = NOW(), attempts = attempts + 1
                        WHERE tenant_id = $1 AND id = $2
                        """,
                        tenant_id,
                        dlq_id,
                    )
                    results.append({"id": dlq_id, "status": "REPLAYED"})

        except Exception as exc:
            results.append({"id": dlq_id, "status": "ERROR", "error": str(exc)})

    return {
        "results": results,
        "total": len(results),
        "replayed": sum(1 for r in results if r["status"] == "REPLAYED"),
        "failed": sum(1 for r in results if r["status"] in ("FAILED", "ERROR")),
    }


@router.delete("/dead-letter/purge")
async def purge_dead_letter(
    older_than_days: int = Query(default=30, ge=1, le=365),
    pool=Depends(get_db_pool),
):
    """Purge (hard delete) all FAILED messages older than N days."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        result = await conn.execute(
            """
            DELETE FROM dead_letter_messages
            WHERE tenant_id = $1
              AND status = 'FAILED'
              AND created_at < NOW() - INTERVAL '1 day' * $2
            """,
            tenant_id,
            older_than_days,
        )
    deleted = 0
    try:
        deleted = int(result.split()[-1])
    except (ValueError, IndexError):
        pass
    return {"purged": deleted, "older_than_days": older_than_days}


@router.post("/dead-letter/{dlq_id}/replay")
async def replay_dead_letter(dlq_id: int, pool=Depends(get_db_pool)):
    """Re-attempt delivery for a single dead letter message."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, route_id, original_topic, payload, destination_type,
                   destination_config, attempts, status
            FROM dead_letter_messages
            WHERE tenant_id = $1 AND id = $2
            """,
            tenant_id,
            dlq_id,
        )

    if not row:
        raise HTTPException(404, "Dead letter message not found")
    if row["status"] != "FAILED":
        raise HTTPException(400, f"Cannot replay message with status {row['status']}")

    config = row["destination_config"] or {}
    if isinstance(config, str):
        config = json.loads(config)
    payload = row["payload"] or {}
    if isinstance(payload, str):
        payload = json.loads(payload)

    delivery_error: str | None = None
    try:
        if row["destination_type"] == "webhook":
            url = config.get("url")
            if not url:
                raise Exception("No URL in destination config")
            method = config.get("method", "POST").upper()
            headers = {"Content-Type": "application/json"}
            body_bytes = json.dumps(payload, default=str).encode()
            secret = config.get("secret")
            if secret:
                import hashlib
                import hmac as hmac_mod

                sig = hmac_mod.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                headers["X-Signature-256"] = f"sha256={sig}"

            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.request(method, url, content=body_bytes, headers=headers)
                if resp.status_code >= 400:
                    raise Exception(f"Webhook returned HTTP {resp.status_code}")

        elif row["destination_type"] == "mqtt_republish":
            raise Exception(
                "MQTT republish replay not supported from API; message must be manually re-sent"
            )

    except Exception as exc:
        delivery_error = str(exc)

    async with tenant_connection(pool, tenant_id) as conn:
        if delivery_error:
            await conn.execute(
                """
                UPDATE dead_letter_messages
                SET attempts = attempts + 1,
                    error_message = $3
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                dlq_id,
                delivery_error[:2000],
            )
            raise HTTPException(502, f"Replay failed: {delivery_error}")
        else:
            await conn.execute(
                """
                UPDATE dead_letter_messages
                SET status = 'REPLAYED',
                    replayed_at = NOW(),
                    attempts = attempts + 1
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                dlq_id,
            )

    return {"id": dlq_id, "status": "REPLAYED", "message": "Message replayed successfully"}


@router.delete("/dead-letter/{dlq_id}")
async def discard_dead_letter(dlq_id: int, pool=Depends(get_db_pool)):
    """Mark a dead letter message as DISCARDED."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            """
            UPDATE dead_letter_messages
            SET status = 'DISCARDED'
            WHERE tenant_id = $1 AND id = $2 AND status = 'FAILED'
            """,
            tenant_id,
            dlq_id,
        )
    if res.endswith("0"):
        raise HTTPException(404, "Dead letter message not found or already processed")
    return {"id": dlq_id, "status": "DISCARDED"}


@router.post("/message-routes/{route_id}/test")
async def test_message_route(route_id: int, body: TestRouteRequest, pool=Depends(get_db_pool)):
    """Test a message route with a sample payload (dry-run delivery)."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        route = await conn.fetchrow(
            "SELECT * FROM message_routes WHERE tenant_id = $1 AND id = $2",
            tenant_id,
            route_id,
        )
    if not route:
        raise HTTPException(404, "Message route not found")

    matched = mqtt_topic_matches(route["topic_filter"], body.topic)

    filter_passed = True
    if matched and route["payload_filter"]:
        pf = route["payload_filter"]
        if isinstance(pf, str):
            pf = json.loads(pf)
        filter_passed = evaluate_payload_filter(pf, body.payload)

    result: dict[str, object] = {
        "route_id": route_id,
        "topic_matched": matched,
        "filter_passed": filter_passed,
        "would_deliver": matched and filter_passed,
        "destination_type": route["destination_type"],
    }

    # Optionally attempt actual delivery if would_deliver is true
    if matched and filter_passed and route["destination_type"] == "webhook":
        try:
            import httpx

            config = route["destination_config"] or {}
            url = config.get("url")
            if url:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json={"test": True, **body.payload})
                result["delivery_status"] = resp.status_code
                result["delivery_success"] = 200 <= resp.status_code < 300
        except Exception as exc:
            result["delivery_status"] = None
            result["delivery_error"] = str(exc)

    return result

