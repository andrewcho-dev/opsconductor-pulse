"""
Internal endpoints called by EMQX for MQTT authentication and authorization.
These are NOT intended for external clients.
"""

import os
import logging

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from db.pool import operator_connection
from dependencies import get_db_pool

logger = logging.getLogger("internal")

INTERNAL_AUTH_SECRET = os.getenv("MQTT_INTERNAL_AUTH_SECRET", "")

router = APIRouter(
    prefix="/api/v1/internal",
    tags=["internal"],
)


def _verify_internal(x_internal_auth: str) -> None:
    """Verify request comes from EMQX (shared secret)."""
    if not INTERNAL_AUTH_SECRET or x_internal_auth != INTERNAL_AUTH_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


class AuthRequest(BaseModel):
    username: str
    client_id: str | None = None
    peer_cert_cn: str | None = None


class AuthResponse(BaseModel):
    result: str  # "allow" | "deny" | "ignore"
    is_superuser: bool = False


class AclRequest(BaseModel):
    username: str
    topic: str
    action: str  # "publish" | "subscribe"
    client_id: str | None = None


class AclResponse(BaseModel):
    result: str  # "allow" | "deny"


@router.post("/mqtt-auth")
async def mqtt_authenticate(
    body: AuthRequest,
    x_internal_auth: str = Header(""),
):
    """
    Called by EMQX on CONNECT.

    Certificate-authenticated devices:
      - CN format: "{tenant_id}/{device_id}"
      - Validate active cert exists and device is not revoked

    Password-authenticated clients:
      - Built-in database handles service accounts
      - Return "ignore" to let EMQX check next auth provider
    """
    _verify_internal(x_internal_auth)

    cn = body.peer_cert_cn or body.username
    if cn and "/" in cn:
        parts = cn.split("/", 1)
        if len(parts) == 2:
            tenant_id, device_id = parts

            pool = await get_db_pool()
            async with operator_connection(pool) as conn:
                has_cert = await conn.fetchval(
                    """
                    SELECT 1 FROM device_certificates
                    WHERE tenant_id = $1
                      AND device_id = $2
                      AND status = 'ACTIVE'
                      AND not_after > now()
                    LIMIT 1
                    """,
                    tenant_id,
                    device_id,
                )

                if has_cert:
                    device_status = await conn.fetchval(
                        "SELECT status FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                        tenant_id,
                        device_id,
                    )
                    if device_status and device_status != "REVOKED":
                        return AuthResponse(result="allow")
                    logger.warning(
                        "mqtt_auth_denied_revoked",
                        extra={"tenant_id": tenant_id, "device_id": device_id},
                    )
                    return AuthResponse(result="deny")

            logger.warning("mqtt_auth_denied_no_cert", extra={"cn": cn})
            return AuthResponse(result="deny")

    return AuthResponse(result="ignore")


@router.post("/mqtt-acl")
async def mqtt_authorize(
    body: AclRequest,
    x_internal_auth: str = Header(""),
):
    """
    Called by EMQX on PUBLISH and SUBSCRIBE.

    Rules:
    - service_pulse: allow all
    - Certificate devices: only allow topics matching their tenant_id/device_id
    """
    _verify_internal(x_internal_auth)

    username = body.username

    if username == "service_pulse":
        return AclResponse(result="allow")

    if "/" in username:
        parts = username.split("/", 1)
        if len(parts) == 2:
            cert_tenant, cert_device = parts

            topic_parts = body.topic.split("/")
            if (
                len(topic_parts) >= 4
                and topic_parts[0] == "tenant"
                and topic_parts[2] == "device"
            ):
                topic_tenant = topic_parts[1]
                topic_device = topic_parts[3]
                if topic_tenant == cert_tenant and topic_device == cert_device:
                    return AclResponse(result="allow")

            logger.warning(
                "mqtt_acl_denied",
                extra={
                    "username": username,
                    "topic": body.topic,
                    "action": body.action,
                    "reason": "topic_tenant_device_mismatch",
                },
            )
            return AclResponse(result="deny")

    return AclResponse(result="deny")

