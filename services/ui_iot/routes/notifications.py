import json
import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from dependencies import get_db_pool
from db.pool import tenant_connection
from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, inject_tenant_context, require_customer
from notifications.senders import send_pagerduty, send_slack, send_teams, send_webhook

logger = logging.getLogger(__name__)

REQUIRED_CONFIG_KEYS = {
    "slack": ["webhook_url"],
    "pagerduty": ["integration_key"],
    "teams": ["webhook_url"],
    "webhook": ["url"],
    "http": ["url"],
    "email": ["smtp", "recipients"],
    "snmp": ["host"],
    "mqtt": ["broker_host", "topic"],
}

MASKED_FIELDS = {
    "slack": ["webhook_url"],
    "pagerduty": ["integration_key"],
    "teams": ["webhook_url"],
    "webhook": ["secret"],
    "http": ["secret"],
    "email": ["smtp"],
    "snmp": ["community", "auth_password", "priv_password"],
    "mqtt": ["password"],
}


def validate_channel_config(channel_type: str, config: dict) -> None:
    required = REQUIRED_CONFIG_KEYS.get(channel_type, [])
    missing = [k for k in required if k not in (config or {})]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required config keys for {channel_type}: {missing}",
        )


def _masked_config(channel_type: str, config: dict) -> dict:
    out = dict(config or {})
    for key in MASKED_FIELDS.get(channel_type, []):
        if key in out and out[key] not in (None, "", {}):
            out[key] = "***"
    return out


class ChannelIn(BaseModel):
    name: str
    channel_type: Literal["slack", "pagerduty", "teams", "webhook", "http", "email", "snmp", "mqtt"]
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
    site_ids: Optional[list[str]] = None
    device_prefixes: Optional[list[str]] = None
    deliver_on: list[str] = ["OPEN"]
    throttle_minutes: int = 0
    priority: int = 100
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
        payload["config"] = _masked_config(payload["channel_type"], payload.get("config") or {})
        channels.append(payload)
    return {"channels": channels}


@router.post("/notification-channels", response_model=ChannelOut, status_code=201)
async def create_channel(body: ChannelIn, pool=Depends(get_db_pool)):
    validate_channel_config(body.channel_type, body.config)
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
    payload["config"] = _masked_config(payload["channel_type"], payload.get("config") or {})
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
    payload["config"] = _masked_config(payload["channel_type"], payload.get("config") or {})
    return payload


@router.put("/notification-channels/{channel_id}", response_model=ChannelOut)
async def update_channel(channel_id: int, body: ChannelIn, pool=Depends(get_db_pool)):
    validate_channel_config(body.channel_type, body.config)
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
    payload["config"] = _masked_config(payload["channel_type"], payload.get("config") or {})
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
    async with tenant_connection(pool, tenant_id) as conn:
        channel = await conn.fetchrow(
            """
            SELECT channel_id, tenant_id, name, channel_type, config, is_enabled
            FROM notification_channels
            WHERE tenant_id = $1 AND channel_id = $2
            """,
            tenant_id,
            channel_id,
        )
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    test_alert = {
        "alert_id": 0,
        "alert_type": "TEST",
        "severity": 3,
        "device_id": "test-device",
        "site_id": None,
        "message": "This is a test notification from OpsConductor-Pulse",
        "details": {},
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }
    ch = dict(channel)
    cfg = ch.get("config") or {}
    try:
        if ch["channel_type"] == "slack":
            await send_slack(cfg["webhook_url"], test_alert)
        elif ch["channel_type"] == "pagerduty":
            await send_pagerduty(cfg["integration_key"], test_alert)
        elif ch["channel_type"] == "teams":
            await send_teams(cfg["webhook_url"], test_alert)
        elif ch["channel_type"] in ("webhook", "http"):
            await send_webhook(
                cfg["url"],
                cfg.get("method", "POST"),
                cfg.get("headers", {}),
                cfg.get("secret"),
                test_alert,
            )
        elif ch["channel_type"] == "email":
            return {"status": "queued", "message": "Email test queued for immediate delivery"}
        elif ch["channel_type"] in ("snmp", "mqtt"):
            return {"status": "queued", "message": f"{ch['channel_type'].upper()} test queued for immediate delivery"}
        return {"status": "ok", "message": "Test notification sent successfully"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Test send failed: {str(exc)}")


@router.get("/notification-routing-rules")
async def list_routing_rules(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                   device_tag_val, site_ids, device_prefixes, deliver_on, throttle_minutes,
                   priority, is_enabled, created_at
            FROM notification_routing_rules
            WHERE tenant_id = $1
            ORDER BY priority ASC, created_at DESC
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
              (tenant_id, channel_id, min_severity, alert_type, device_tag_key, device_tag_val,
               site_ids, device_prefixes, deliver_on, throttle_minutes, priority, is_enabled)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::text[],$10,$11,$12)
            RETURNING rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                      device_tag_val, site_ids, device_prefixes, deliver_on, throttle_minutes,
                      priority, is_enabled, created_at
            """,
            tenant_id,
            body.channel_id,
            body.min_severity,
            body.alert_type,
            body.device_tag_key,
            body.device_tag_val,
            body.site_ids,
            body.device_prefixes,
            body.deliver_on,
            body.throttle_minutes,
            body.priority,
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
                device_tag_val = $7, site_ids = $8, device_prefixes = $9, deliver_on = $10::text[],
                throttle_minutes = $11, priority = $12, is_enabled = $13
            WHERE tenant_id = $1 AND rule_id = $2
            RETURNING rule_id, tenant_id, channel_id, min_severity, alert_type, device_tag_key,
                      device_tag_val, site_ids, device_prefixes, deliver_on, throttle_minutes,
                      priority, is_enabled, created_at
            """,
            tenant_id,
            rule_id,
            body.channel_id,
            body.min_severity,
            body.alert_type,
            body.device_tag_key,
            body.device_tag_val,
            body.site_ids,
            body.device_prefixes,
            body.deliver_on,
            body.throttle_minutes,
            body.priority,
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


@router.get("/notification-jobs")
async def list_notification_jobs(
    channel_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    conditions = ["tenant_id = $1"]
    params: list[object] = [tenant_id]
    if channel_id:
        params.append(channel_id)
        conditions.append(f"channel_id = ${len(params)}")
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    params.append(limit)
    where = " AND ".join(conditions)
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT job_id, tenant_id, alert_id, channel_id, rule_id, deliver_on_event,
                   status, attempts, next_run_at, last_error, payload_json, created_at, updated_at
            FROM notification_jobs
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
    return {"jobs": [dict(r) for r in rows]}
