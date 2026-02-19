"""Carrier integration routes (MVNO/IoT connectivity platforms)."""

import json
import logging
from typing import Any, Literal

import asyncpg
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from routes.customer import (  # noqa: F401
    JWTBearer,
    inject_tenant_context,
    require_customer,
    get_tenant_id,
    get_db_pool,
    tenant_connection,
)
from middleware.permissions import require_permission
from middleware.entitlements import check_account_feature
from middleware.tenant import is_operator
from services.carrier_service import get_carrier_provider

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["carrier"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value)
    if len(v) <= 4:
        return "****"
    return f"...{v[-4:]}"


def _carrier_call_error(e: Exception) -> HTTPException:
    if isinstance(e, httpx.HTTPStatusError):
        return HTTPException(502, f"Carrier API error: {e.response.status_code}")
    if isinstance(e, httpx.RequestError):
        return HTTPException(502, f"Failed to reach carrier API: {str(e)}")
    logger.exception("Carrier API call failed")
    return HTTPException(500, "Internal error during carrier API call")


class CarrierIntegrationCreate(BaseModel):
    carrier_name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True
    api_key: str | None = None
    api_secret: str | None = None
    api_base_url: str | None = None
    account_id: str | None = None
    sync_enabled: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)
    config: dict[str, Any] = Field(default_factory=dict)


class CarrierIntegrationUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_base_url: str | None = None
    account_id: str | None = None
    sync_enabled: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    config: dict[str, Any] | None = None


class CarrierLinkRequest(BaseModel):
    carrier_integration_id: int
    carrier_device_id: str = Field(..., min_length=1, max_length=200)


class ProvisionRequest(BaseModel):
    carrier_integration_id: int
    iccid: str = Field(..., min_length=15, max_length=22)
    plan_id: int | None = None


@router.get("/carrier/integrations")
async def list_carrier_integrations(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT id, carrier_name, display_name, enabled,
                       account_id, sync_enabled, sync_interval_minutes,
                       last_sync_at, last_sync_status, last_sync_error,
                       api_key, created_at
                FROM carrier_integrations
                WHERE tenant_id = $1
                ORDER BY id
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to list carrier integrations")
        raise HTTPException(status_code=500, detail="Internal server error")

    integrations = []
    for r in rows:
        integrations.append(
            {
                "id": r["id"],
                "carrier_name": r["carrier_name"],
                "display_name": r["display_name"],
                "enabled": r["enabled"],
                "account_id": r["account_id"],
                "sync_enabled": r["sync_enabled"],
                "sync_interval_minutes": r["sync_interval_minutes"],
                "last_sync_at": r["last_sync_at"],
                "last_sync_status": r["last_sync_status"],
                "last_sync_error": r["last_sync_error"],
                "api_key_masked": _mask_secret(r["api_key"]),
                "created_at": r["created_at"],
            }
        )
    return {"integrations": integrations}


@router.get("/carrier/integrations/{integration_id}/plans")
async def list_carrier_plans(integration_id: int, pool=Depends(get_db_pool)):
    """List available data plans from the carrier for this integration."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        integration = await _load_integration(conn, tenant_id, integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            plans = await provider.list_plans()
        except NotImplementedError:
            return {"plans": [], "note": "Plan listing not supported for this carrier"}
        except Exception as e:
            raise _carrier_call_error(e)

    return {"plans": plans, "carrier_name": integration.get("carrier_name")}


@router.post(
    "/carrier/integrations",
    dependencies=[require_permission("carrier.integrations.write")],
)
async def create_carrier_integration(body: CarrierIntegrationCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    if not is_operator():
        async with tenant_connection(pool, tenant_id) as conn:
            gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
            if not gate["allowed"]:
                raise HTTPException(status_code=403, detail=gate["message"])
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO carrier_integrations
                    (tenant_id, carrier_name, display_name, enabled,
                     api_key, api_secret, api_base_url, account_id,
                     config, sync_enabled, sync_interval_minutes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11)
                RETURNING id, carrier_name, display_name, enabled,
                          account_id, sync_enabled, sync_interval_minutes,
                          last_sync_at, last_sync_status, last_sync_error,
                          api_key, created_at
                """,
                tenant_id,
                body.carrier_name,
                body.display_name,
                body.enabled,
                body.api_key,
                body.api_secret,
                body.api_base_url,
                body.account_id,
                json.dumps(body.config),
                body.sync_enabled,
                body.sync_interval_minutes,
            )
    except Exception:
        logger.exception("Failed to create carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "id": row["id"],
        "carrier_name": row["carrier_name"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
        "account_id": row["account_id"],
        "sync_enabled": row["sync_enabled"],
        "sync_interval_minutes": row["sync_interval_minutes"],
        "last_sync_at": row["last_sync_at"],
        "last_sync_status": row["last_sync_status"],
        "last_sync_error": row["last_sync_error"],
        "api_key_masked": _mask_secret(row["api_key"]),
        "created_at": row["created_at"],
    }


@router.put(
    "/carrier/integrations/{integration_id}",
    dependencies=[require_permission("carrier.integrations.write")],
)
async def update_carrier_integration(
    integration_id: int, body: CarrierIntegrationUpdate, pool=Depends(get_db_pool)
):
    tenant_id = get_tenant_id()
    if not is_operator():
        async with tenant_connection(pool, tenant_id) as conn:
            gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
            if not gate["allowed"]:
                raise HTTPException(status_code=403, detail=gate["message"])
    sets: list[str] = []
    params: list[Any] = [tenant_id, integration_id]
    idx = 3

    def add_set(col: str, val: Any):
        nonlocal idx
        sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    if body.display_name is not None:
        add_set("display_name", body.display_name)
    if body.enabled is not None:
        add_set("enabled", body.enabled)
    if body.api_key is not None:
        add_set("api_key", body.api_key)
    if body.api_secret is not None:
        add_set("api_secret", body.api_secret)
    if body.api_base_url is not None:
        add_set("api_base_url", body.api_base_url)
    if body.account_id is not None:
        add_set("account_id", body.account_id)
    if body.sync_enabled is not None:
        add_set("sync_enabled", body.sync_enabled)
    if body.sync_interval_minutes is not None:
        add_set("sync_interval_minutes", body.sync_interval_minutes)
    if body.config is not None:
        sets.append(f"config = ${idx}::jsonb")
        params.append(json.dumps(body.config))
        idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets.append("updated_at = now()")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE carrier_integrations
                SET {", ".join(sets)}
                WHERE tenant_id = $1 AND id = $2
                RETURNING id, carrier_name, display_name, enabled,
                          account_id, sync_enabled, sync_interval_minutes,
                          last_sync_at, last_sync_status, last_sync_error,
                          api_key, created_at
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    return {
        "id": row["id"],
        "carrier_name": row["carrier_name"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
        "account_id": row["account_id"],
        "sync_enabled": row["sync_enabled"],
        "sync_interval_minutes": row["sync_interval_minutes"],
        "last_sync_at": row["last_sync_at"],
        "last_sync_status": row["last_sync_status"],
        "last_sync_error": row["last_sync_error"],
        "api_key_masked": _mask_secret(row["api_key"]),
        "created_at": row["created_at"],
    }


@router.delete(
    "/carrier/integrations/{integration_id}",
    dependencies=[require_permission("carrier.integrations.write")],
)
async def delete_carrier_integration(integration_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    if not is_operator():
        async with tenant_connection(pool, tenant_id) as conn:
            gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
            if not gate["allowed"]:
                raise HTTPException(status_code=403, detail=gate["message"])
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            async with conn.transaction():
                # Unlink devices first
                try:
                    await conn.execute(
                        """
                        UPDATE device_connections
                        SET carrier_integration_id = NULL, updated_at = now()
                        WHERE tenant_id = $1 AND carrier_integration_id = $2
                        """,
                        tenant_id,
                        integration_id,
                    )
                except asyncpg.UndefinedColumnError:
                    raise HTTPException(
                        status_code=400,
                        detail="carrier link columns not available; apply migration 106 first",
                    )

                deleted = await conn.fetchval(
                    """
                    DELETE FROM carrier_integrations
                    WHERE tenant_id = $1 AND id = $2
                    RETURNING 1
                    """,
                    tenant_id,
                    integration_id,
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"deleted": True, "id": integration_id}


async def _load_carrier_link(conn: asyncpg.Connection, tenant_id: str, device_id: str) -> dict[str, Any]:
    try:
        row = await conn.fetchrow(
            """
            SELECT carrier_integration_id, carrier_device_id
            FROM device_connections
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
    except asyncpg.UndefinedColumnError:
        raise HTTPException(
            status_code=400,
            detail="carrier link columns not available; apply migration 106 first",
        )
    return dict(row) if row else {}


async def _load_integration(conn: asyncpg.Connection, tenant_id: str, integration_id: int) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT *
        FROM carrier_integrations
        WHERE tenant_id = $1 AND id = $2
        """,
        tenant_id,
        integration_id,
    )
    return dict(row) if row else None


@router.get("/devices/{device_id}/carrier/status")
async def get_carrier_status(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        link = await _load_carrier_link(conn, tenant_id, device_id)
        integration_id = link.get("carrier_integration_id")
        carrier_device_id = link.get("carrier_device_id")
        if not integration_id or not carrier_device_id:
            return {"linked": False}

        integration = await _load_integration(conn, tenant_id, int(integration_id))
        if not integration:
            return {"linked": False}

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            info = await provider.get_device_info(str(carrier_device_id))
        except Exception as e:
            raise _carrier_call_error(e)

        return {
            "linked": True,
            "carrier_name": integration.get("carrier_name"),
            "device_info": {
                "carrier_device_id": info.carrier_device_id,
                "iccid": info.iccid,
                "sim_status": info.sim_status,
                "network_status": info.network_status,
                "ip_address": info.ip_address,
                "network_type": info.network_type,
                "last_connection": info.last_connection,
                "signal_strength": info.signal_strength,
            },
        }


@router.get("/devices/{device_id}/carrier/usage")
async def get_carrier_usage(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        link = await _load_carrier_link(conn, tenant_id, device_id)
        integration_id = link.get("carrier_integration_id")
        carrier_device_id = link.get("carrier_device_id")
        if not integration_id or not carrier_device_id:
            return {"linked": False}

        integration = await _load_integration(conn, tenant_id, int(integration_id))
        if not integration:
            return {"linked": False}

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            usage = await provider.get_usage(str(carrier_device_id))
        except Exception as e:
            raise _carrier_call_error(e)

        used_mb = usage.data_used_bytes / (1024 * 1024) if usage.data_used_bytes else 0.0
        limit_mb = (
            usage.data_limit_bytes / (1024 * 1024) if usage.data_limit_bytes else None
        )
        usage_pct = (used_mb / limit_mb) * 100 if limit_mb else None

        return {
            "linked": True,
            "carrier_name": integration.get("carrier_name"),
            "usage": {
                "data_used_bytes": int(usage.data_used_bytes or 0),
                "data_limit_bytes": int(usage.data_limit_bytes) if usage.data_limit_bytes else None,
                "data_used_mb": round(used_mb, 1),
                "data_limit_mb": int(limit_mb) if limit_mb is not None else None,
                "usage_pct": round(usage_pct, 1) if usage_pct is not None else None,
                "billing_cycle_start": usage.billing_cycle_start,
                "billing_cycle_end": usage.billing_cycle_end,
                "sms_count": int(usage.sms_count or 0),
            },
        }


@router.post(
    "/devices/{device_id}/carrier/actions/{action}",
    dependencies=[require_permission("carrier.actions.execute")],
)
async def carrier_action(
    request: Request,
    device_id: str,
    action: Literal["activate", "suspend", "deactivate", "reboot"],
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        link = await _load_carrier_link(conn, tenant_id, device_id)
        integration_id = link.get("carrier_integration_id")
        carrier_device_id = link.get("carrier_device_id")
        if not integration_id or not carrier_device_id:
            raise HTTPException(status_code=400, detail="Device is not linked to a carrier integration")

        integration = await _load_integration(conn, tenant_id, int(integration_id))
        if not integration:
            raise HTTPException(status_code=400, detail="Carrier integration not found")

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        if action == "deactivate":
            logger.warning("DESTRUCTIVE carrier action requested: deactivate (tenant=%s device=%s)", tenant_id, device_id)

        try:
            if action == "activate":
                ok = await provider.activate_sim(str(carrier_device_id))
            elif action == "suspend":
                ok = await provider.suspend_sim(str(carrier_device_id))
            elif action == "deactivate":
                ok = await provider.deactivate_sim(str(carrier_device_id))
            else:  # reboot
                ok = await provider.send_sms(str(carrier_device_id), "REBOOT")
        except Exception as e:
            raise _carrier_call_error(e)

        audit = getattr(request.app.state, "audit", None)
        if audit:
            try:
                audit.config_changed(
                    tenant_id,
                    "carrier_action",
                    device_id,
                    "execute",
                    f"{integration.get('carrier_name')}:{action}",
                    details={"action": action, "device_id": device_id},
                )
            except Exception:
                # Best-effort; don't fail request due to audit logging.
                logger.debug("Carrier action audit logging failed", exc_info=True)

        return {"action": action, "success": bool(ok), "carrier_name": integration.get("carrier_name")}


@router.get("/devices/{device_id}/carrier/diagnostics")
async def get_carrier_diagnostics(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        link = await _load_carrier_link(conn, tenant_id, device_id)
        integration_id = link.get("carrier_integration_id")
        carrier_device_id = link.get("carrier_device_id")
        if not integration_id or not carrier_device_id:
            return {"linked": False}

        integration = await _load_integration(conn, tenant_id, int(integration_id))
        if not integration:
            return {"linked": False}

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            diagnostics = await provider.get_network_diagnostics(str(carrier_device_id))
        except Exception as e:
            raise _carrier_call_error(e)

        return {
            "linked": True,
            "carrier_name": integration.get("carrier_name"),
            "carrier_device_id": carrier_device_id,
            "diagnostics": diagnostics,
        }


@router.post(
    "/devices/{device_id}/carrier/link",
    dependencies=[require_permission("carrier.links.write")],
)
async def link_device_to_carrier(device_id: str, body: CarrierLinkRequest, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            # Validate integration exists for tenant
            integration = await _load_integration(conn, tenant_id, body.carrier_integration_id)
            if not integration:
                raise HTTPException(status_code=400, detail="Invalid carrier_integration_id")

            try:
                await conn.execute(
                    """
                    INSERT INTO device_connections (tenant_id, device_id, carrier_integration_id, carrier_device_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (tenant_id, device_id)
                    DO UPDATE SET
                        carrier_integration_id = EXCLUDED.carrier_integration_id,
                        carrier_device_id = EXCLUDED.carrier_device_id,
                        updated_at = now()
                    """,
                    tenant_id,
                    device_id,
                    body.carrier_integration_id,
                    body.carrier_device_id,
                )
            except asyncpg.UndefinedColumnError:
                raise HTTPException(
                    status_code=400,
                    detail="carrier link columns not available; apply migration 106 first",
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to link device to carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"linked": True, "device_id": device_id, "carrier_integration_id": body.carrier_integration_id}


@router.post(
    "/devices/{device_id}/carrier/provision",
    dependencies=[require_permission("carrier.links.write")],
)
async def provision_device_sim(device_id: str, body: ProvisionRequest, pool=Depends(get_db_pool)):
    """Claim a new SIM from the carrier and link it to this device."""
    tenant_id = get_tenant_id()
    if not is_operator():
        async with tenant_connection(pool, tenant_id) as conn:
            gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
            if not gate["allowed"]:
                raise HTTPException(status_code=403, detail=gate["message"])

    async with tenant_connection(pool, tenant_id) as conn:
        integration = await _load_integration(conn, tenant_id, body.carrier_integration_id)
        if not integration:
            raise HTTPException(status_code=400, detail="Invalid carrier_integration_id")

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            claim_result = await provider.claim_sim(body.iccid, body.plan_id)
        except Exception as e:
            raise _carrier_call_error(e)

        carrier_device_id = str(
            claim_result.get("id")
            or claim_result.get("device_id")
            or claim_result.get("deviceid")
            or ""
        )
        if not carrier_device_id:
            raise HTTPException(
                status_code=502,
                detail="Carrier claim succeeded but no device ID returned",
            )

        try:
            await conn.execute(
                """
                INSERT INTO device_connections (tenant_id, device_id, carrier_integration_id, carrier_device_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, device_id)
                DO UPDATE SET
                    carrier_integration_id = EXCLUDED.carrier_integration_id,
                    carrier_device_id = EXCLUDED.carrier_device_id,
                    updated_at = now()
                """,
                tenant_id,
                device_id,
                body.carrier_integration_id,
                carrier_device_id,
            )
        except asyncpg.UndefinedColumnError:
            raise HTTPException(
                status_code=400,
                detail="carrier link columns not available; apply migration 106 first",
            )

    return {
        "provisioned": True,
        "device_id": device_id,
        "carrier_device_id": carrier_device_id,
        "carrier_integration_id": body.carrier_integration_id,
        "iccid": body.iccid,
        "claim_result": claim_result,
    }

