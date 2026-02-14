import json
import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from dependencies import get_db_pool
from db.pool import tenant_connection
from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, inject_tenant_context, require_customer
from notifications.dispatcher import dispatch_alert

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {"secret", "integration_key", "webhook_url"}


def _masked_config(config: dict) -> dict:
    out = {}
    for key, value in (config or {}).items():
        out[key] = "***" if key in SENSITIVE_KEYS and value else value
    return out


class ChannelIn(BaseModel):
    name: str
    channel_type: Literal["slack", "pagerduty", "teams", "webhook"]
    config: dict
    is_enabled: bool = True


class ChannelOut(ChannelIn):
    channel_id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class RoutingRuleIn(BaseModel):
    channel_id: int
    min_severity: Optional[int] = None
    alert_type: Optional[str] = None
    device_tag_key: Optional[str] = None
    device_tag_val: Optional[str] = None
    throttle_minutes: int = 0
    is_enabled: bool = True


class RoutingRuleOut(RoutingRuleIn):
    rule_id: int
    tenant_id: str
    created_at: datetime


router = APIRouter(
    prefix="/customer",
    tags=["notifications"],
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context), Depends(require_customer)],
)


@router.get("/notification-channels")
async def list_channels(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT channel_id, tenant_id, name, channel_type, config, is_enabled, created_at, updated_at
            FROM notification_channels
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
    channels = []
    for row in rows:
        payload = dict(row)
        payload["config"] = _masked_config(payload.get("config") or {})
        channels.append(payload)
    return {"channels": channels}


@router.post("/notification-channels", response_model=ChannelOut, status_code=201)
async def create_channel(body: ChannelIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO notification_channels (tenant_id, name, channel_type, config, is_enabled)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            RETURNING channel_id, tenant_id, name, channel_type, config, is_enabled, created_at, updated_at
            """,
            tenant_id,
            body.name.strip(),
            body.channel_type,
            json.dumps(body.config or {}),
            body.is_enabled,
        )
    payload = dict(row)
    payload["config"] = _masked_config(payload.get("config") or {})
    return payload


@router.get("/notification-channels/{channel_id}", response_model=ChannelOut)
async def get_channel(channel_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT channel_id, tenant_id, name, channel_type, config, is_enabled, created_at, updated_at
            FROM notification_channels
            WHERE tenant_id = $1 AND channel_id = $2
            """,
            tenant_id,
            channel_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    payload = dict(row)
    payload["config"] = _masked_config(payload.get("config") or {})
    return payload


@router.put("/notification-channels/{channel_id}", response_model=ChannelOut)
async def update_channel(channel_id: int, body: ChannelIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE notification_channels
            SET name = $3, channel_type = $4, config = $5::jsonb, is_enabled = $6, updated_at = NOW()
            WHERE tenant_id = $1 AND channel_id = $2
            RETURNING channel_id, tenant_id, name, channel_type, config, is_enabled, created_at, updated_at
            """,
            tenant_id,
            channel_id,
            body.name.strip(),
            body.channel_type,
            json.dumps(body.config or {}),
            body.is_enabled,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Channel not found")
    payload = dict(row)
    payload["config"] = _masked_config(payload.get("config") or {})
    return payload


@router.delete("/notification-channels/{channel_id}", status_code=204)
async def delete_channel(channel_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            "DELETE FROM notification_channels WHERE tenant_id = $1 AND channel_id = $2",
            tenant_id,
            channel_id,
        )
    if res.endswith("0"):
        raise HTTPException(status_code=404, detail="Channel not found")
    return Response(status_code=204)


@router.post("/notification-channels/{channel_id}/test")
async def test_channel(channel_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    alert = {
        "alert_id": 0,
        "tenant_id": tenant_id,
        "device_id": "test-device",
        "alert_type": "TEST",
        "severity": 3,
        "summary": "Test notification",
        "created_at": datetime.utcnow().isoformat(),
        "details": {},
    }
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await conn.execute(
                """
                INSERT INTO notification_routing_rules
                  (tenant_id, channel_id, min_severity, throttle_minutes, is_enabled)
                VALUES ($1, $2, NULL, 0, TRUE)
                ON CONFLICT DO NOTHING
                """,
                tenant_id,
                channel_id,
            )
        await dispatch_alert(pool, alert, tenant_id)
        return {"ok": True}
    except Exception as exc:
        logger.exception("Notification test failed")
        return {"ok": False, "error": str(exc)}


@router.get("/notification-routing-rules")
async def list_routing_rules(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                   device_tag_val, throttle_minutes, is_enabled, created_at
            FROM notification_routing_rules
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
    return {"rules": [dict(row) for row in rows]}


@router.post("/notification-routing-rules", response_model=RoutingRuleOut, status_code=201)
async def create_routing_rule(body: RoutingRuleIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO notification_routing_rules
              (tenant_id, channel_id, min_severity, alert_type, device_tag_key, device_tag_val, throttle_minutes, is_enabled)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                      device_tag_val, throttle_minutes, is_enabled, created_at
            """,
            tenant_id,
            body.channel_id,
            body.min_severity,
            body.alert_type,
            body.device_tag_key,
            body.device_tag_val,
            body.throttle_minutes,
            body.is_enabled,
        )
    return dict(row)


@router.put("/notification-routing-rules/{rule_id}", response_model=RoutingRuleOut)
async def update_routing_rule(rule_id: int, body: RoutingRuleIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE notification_routing_rules
            SET channel_id = $3, min_severity = $4, alert_type = $5, device_tag_key = $6,
                device_tag_val = $7, throttle_minutes = $8, is_enabled = $9
            WHERE tenant_id = $1 AND rule_id = $2
            RETURNING rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                      device_tag_val, throttle_minutes, is_enabled, created_at
            """,
            tenant_id,
            rule_id,
            body.channel_id,
            body.min_severity,
            body.alert_type,
            body.device_tag_key,
            body.device_tag_val,
            body.throttle_minutes,
            body.is_enabled,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return dict(row)


@router.delete("/notification-routing-rules/{rule_id}", status_code=204)
async def delete_routing_rule(rule_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            "DELETE FROM notification_routing_rules WHERE tenant_id = $1 AND rule_id = $2",
            tenant_id,
            rule_id,
        )
    if res.endswith("0"):
        raise HTTPException(status_code=404, detail="Routing rule not found")
    return Response(status_code=204)
