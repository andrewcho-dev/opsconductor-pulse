import json
import logging
from datetime import timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from middleware.entitlements import check_sensor_limit, get_device_usage
from db.pool import tenant_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)

HEALTH_RANGES = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


router = APIRouter(
    prefix="/api/v1/customer",
    tags=["sensors"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class DeviceSensorCreate(BaseModel):
    metric_key: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    display_name: str = Field(..., min_length=1, max_length=200)
    template_metric_id: int | None = None
    device_module_id: int | None = None
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int = Field(default=2, ge=0, le=6)


class DeviceSensorUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int | None = Field(default=None, ge=0, le=6)
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")


class ConnectionUpsert(BaseModel):
    connection_type: str = Field(
        default="cellular",
        pattern=r"^(cellular|ethernet|wifi|lora|satellite|other)$",
    )
    carrier_name: str | None = Field(default=None, max_length=100)
    carrier_account_id: str | None = Field(default=None, max_length=100)
    plan_name: str | None = Field(default=None, max_length=100)
    apn: str | None = Field(default=None, max_length=100)
    sim_iccid: str | None = Field(default=None, max_length=30)
    sim_status: str | None = Field(
        default=None,
        pattern=r"^(active|suspended|deactivated|ready|unknown)$",
    )
    data_limit_mb: int | None = Field(default=None, ge=0)
    billing_cycle_start: int | None = Field(default=None, ge=1, le=28)
    ip_address: str | None = Field(default=None, max_length=45)
    msisdn: str | None = Field(default=None, max_length=20)


def _serialize_time(value):
    if value is None:
        return None
    try:
        iso = value.isoformat()
        return iso.replace("+00:00", "Z")
    except Exception:
        return str(value)


def _serialize_health_row(row) -> dict[str, Any]:
    data = dict(row)
    data["time"] = _serialize_time(data.get("time"))
    return data


@router.get("/devices/{device_id}/sensors")
async def list_device_sensors(
    device_id: str,
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            where_clauses: list[str] = ["ds.tenant_id = $1", "ds.device_id = $2"]
            args: list[Any] = [tenant_id, device_id]
            arg_idx = 3
            if status:
                where_clauses.append(f"ds.status = ${arg_idx}")
                args.append(status)
                arg_idx += 1
            if source:
                where_clauses.append(f"ds.source = ${arg_idx}")
                args.append(source)
                arg_idx += 1

            rows = await conn.fetch(
                f"""
                SELECT
                    ds.id,
                    ds.metric_key,
                    ds.display_name,
                    ds.source,
                    tm.id AS template_metric_id,
                    tm.display_name AS template_metric_display_name,
                    dm.id AS module_id,
                    dm.label AS module_label,
                    ds.unit,
                    ds.min_range,
                    ds.max_range,
                    ds.precision_digits,
                    ds.status,
                    ds.last_value,
                    ds.last_value_text,
                    ds.last_seen_at
                FROM device_sensors ds
                LEFT JOIN template_metrics tm ON tm.id = ds.template_metric_id
                LEFT JOIN device_modules dm ON dm.id = ds.device_module_id
                WHERE {' AND '.join(where_clauses)}
                ORDER BY ds.metric_key
                """,
                *args,
            )

            usage = await get_device_usage(conn, tenant_id, device_id)
            sensor_limit = (usage.get("limits") or {}).get("sensors")

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list device sensors")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "device_id": device_id,
        "sensors": [
            {
                "id": r["id"],
                "metric_key": r["metric_key"],
                "display_name": r["display_name"],
                "source": r["source"],
                "template_metric": (
                    {"id": r["template_metric_id"], "display_name": r["template_metric_display_name"]}
                    if r["template_metric_id"]
                    else None
                ),
                "module": ({"id": r["module_id"], "label": r["module_label"]} if r["module_id"] else None),
                "unit": r["unit"],
                "min_range": r["min_range"],
                "max_range": r["max_range"],
                "precision_digits": r["precision_digits"],
                "status": r["status"],
                "last_value": r["last_value"],
                "last_value_text": r["last_value_text"],
                "last_seen_at": _serialize_time(r["last_seen_at"]),
            }
            for r in rows
        ],
        "total": len(rows),
        "sensor_limit": sensor_limit,
    }


@router.get("/sensors")
async def list_sensors(
    sensor_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            where_clauses: list[str] = ["ds.tenant_id = $1"]
            args: list[Any] = [tenant_id]
            arg_idx = 2

            if sensor_type:
                # Backward compat: sensor_type derives from template metric data_type when available.
                where_clauses.append(f"COALESCE(tm.data_type, 'unknown') = ${arg_idx}")
                args.append(sensor_type)
                arg_idx += 1
            if status:
                # Backward compat: translate legacy disabled -> inactive
                if status == "disabled":
                    where_clauses.append("ds.status = 'inactive'")
                else:
                    where_clauses.append(f"ds.status = ${arg_idx}")
                    args.append(status)
                    arg_idx += 1
            if device_id:
                where_clauses.append(f"ds.device_id = ${arg_idx}")
                args.append(device_id)
                arg_idx += 1

            where_sql = " AND ".join(where_clauses)

            total = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM device_sensors ds
                LEFT JOIN template_metrics tm ON tm.id = ds.template_metric_id
                WHERE {where_sql}
                """,
                *args,
            )
            rows = await conn.fetch(
                f"""
                SELECT
                    ds.id AS sensor_id,
                    ds.device_id,
                    ds.metric_key AS metric_name,
                    COALESCE(tm.data_type, 'unknown') AS sensor_type,
                    ds.display_name AS label,
                    ds.unit,
                    ds.min_range,
                    ds.max_range,
                    ds.precision_digits,
                    CASE WHEN ds.status = 'active' THEN 'active' ELSE 'disabled' END AS status,
                    (ds.source <> 'required') AS auto_discovered,
                    ds.last_value,
                    ds.last_seen_at,
                    ds.created_at
                FROM device_sensors ds
                LEFT JOIN template_metrics tm ON tm.id = ds.template_metric_id
                WHERE {where_sql}
                ORDER BY device_id, metric_name
                LIMIT {limit} OFFSET {offset}
                """,
                *args,
            )

    except Exception:
        logger.exception("Failed to list sensors")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"sensors": [dict(r) for r in rows], "total": int(total or 0), "limit": limit, "offset": offset}


@router.post("/devices/{device_id}/sensors", status_code=201)
async def create_device_sensor(device_id: str, body: DeviceSensorCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            device_row = await conn.fetchrow(
                "SELECT template_id FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not device_row:
                raise HTTPException(status_code=404, detail="Device not found")

            # Enforce sensor limit based on plan limits, but count device_sensors.
            usage = await get_device_usage(conn, tenant_id, device_id)
            sensor_limit = (usage.get("limits") or {}).get("sensors")
            current_count = await conn.fetchval(
                "SELECT COUNT(*) FROM device_sensors WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if sensor_limit is not None and int(current_count or 0) >= int(sensor_limit):
                raise HTTPException(status_code=403, detail="Sensor limit reached for this device plan")

            if body.template_metric_id is not None:
                if device_row["template_id"] is None:
                    raise HTTPException(status_code=400, detail="Device has no template; cannot use template_metric_id")
                owns = await conn.fetchval(
                    """
                    SELECT 1
                    FROM template_metrics tm
                    WHERE tm.id = $1 AND tm.template_id = $2
                    """,
                    body.template_metric_id,
                    device_row["template_id"],
                )
                if not owns:
                    raise HTTPException(status_code=400, detail="template_metric_id does not belong to device template")

            if body.device_module_id is not None:
                module_ok = await conn.fetchval(
                    """
                    SELECT 1
                    FROM device_modules dm
                    WHERE dm.id = $1 AND dm.tenant_id = $2 AND dm.device_id = $3
                    """,
                    body.device_module_id,
                    tenant_id,
                    device_id,
                )
                if not module_ok:
                    raise HTTPException(status_code=400, detail="device_module_id does not belong to this device")

            source = "optional" if body.template_metric_id is not None else "unmodeled"

            row = await conn.fetchrow(
                """
                INSERT INTO device_sensors (
                    tenant_id, device_id, metric_key, display_name,
                    template_metric_id, device_module_id,
                    unit, min_range, max_range, precision_digits,
                    status, source
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,'active',$11)
                RETURNING *
                """,
                tenant_id,
                device_id,
                body.metric_key,
                body.display_name,
                body.template_metric_id,
                body.device_module_id,
                body.unit,
                body.min_range,
                body.max_range,
                body.precision_digits,
                source,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return dict(row)


@router.put("/devices/{device_id}/sensors/{sensor_id}")
async def update_device_sensor(
    device_id: str,
    sensor_id: int,
    body: DeviceSensorUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates: dict[str, Any] = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in updates.items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts: list[str] = []
    args: list[Any] = [tenant_id, device_id, sensor_id]
    arg_idx = 4
    for key, value in updates.items():
        set_parts.append(f"{key} = ${arg_idx}")
        args.append(value)
        arg_idx += 1
    set_parts.append("updated_at = now()")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM device_sensors WHERE tenant_id = $1 AND device_id = $2 AND id = $3",
                tenant_id,
                device_id,
                sensor_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Sensor not found")

            row = await conn.fetchrow(
                f"""
                UPDATE device_sensors
                SET {', '.join(set_parts)}
                WHERE tenant_id = $1 AND device_id = $2 AND id = $3
                RETURNING *
                """,
                *args,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return dict(row)


@router.delete("/devices/{device_id}/sensors/{sensor_id}", status_code=204)
async def delete_device_sensor(device_id: str, sensor_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                "SELECT id, source FROM device_sensors WHERE tenant_id = $1 AND device_id = $2 AND id = $3",
                tenant_id,
                device_id,
                sensor_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Sensor not found")
            if row["source"] == "required":
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete a required sensor. Deactivate it instead.",
                )
            await conn.execute(
                "DELETE FROM device_sensors WHERE tenant_id = $1 AND device_id = $2 AND id = $3",
                tenant_id,
                device_id,
                sensor_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete device sensor")
        raise HTTPException(status_code=500, detail="Internal server error")
    return Response(status_code=204)


@router.put("/sensors/{sensor_id}")
async def update_sensor(sensor_id: int, payload: DeviceSensorUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            existing = await conn.fetchrow(
                "SELECT tenant_id, device_id, id FROM device_sensors WHERE tenant_id = $1 AND id = $2",
                tenant_id,
                sensor_id,
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Sensor not found")

            updates: dict[str, Any] = payload.model_dump(exclude_unset=True)
            # Remove explicit None values (treat as "not provided")
            updates = {k: v for k, v in updates.items() if v is not None}
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")

            set_parts: list[str] = []
            args: list[Any] = [tenant_id, sensor_id]
            arg_idx = 3
            for key, value in updates.items():
                set_parts.append(f"{key} = ${arg_idx}")
                args.append(value)
                arg_idx += 1

            row = await conn.fetchrow(
                f"""
                UPDATE device_sensors
                SET {', '.join(set_parts)}
                WHERE tenant_id = $1 AND id = $2
                RETURNING *
                """,
                *args,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return dict(row)


@router.get("/devices/{device_id}/connection")
async def get_device_connection(device_id: str, response: Response, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            row = await conn.fetchrow(
                """
                SELECT
                    device_id,
                    connection_type,
                    carrier_name,
                    carrier_account_id,
                    plan_name,
                    apn,
                    sim_iccid,
                    sim_status,
                    data_limit_mb,
                    data_used_mb,
                    data_used_updated_at,
                    billing_cycle_start,
                    ip_address::text AS ip_address,
                    msisdn,
                    network_status,
                    last_network_attach,
                    last_network_detach,
                    created_at,
                    updated_at
                FROM device_connections
                WHERE tenant_id = $1 AND device_id = $2
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch device connection")
        raise HTTPException(status_code=500, detail="Internal server error")

    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = f'</api/v1/customer/devices/{device_id}/transports>; rel="successor-version"'

    if not row:
        return {"device_id": device_id, "connection": None}
    return dict(row)


@router.put("/devices/{device_id}/connection")
async def upsert_device_connection(
    device_id: str,
    payload: ConnectionUpsert,
    response: Response,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            provided = payload.model_dump(exclude_unset=True)
            # Always upsert connection_type (even if not explicitly provided)
            provided["connection_type"] = payload.connection_type

            columns: list[str] = ["tenant_id", "device_id"]
            values_sql: list[str] = ["$1", "$2"]
            update_sql: list[str] = ["updated_at = now()"]
            args: list[Any] = [tenant_id, device_id]
            arg_idx = 3

            for key, value in provided.items():
                if key == "connection_type":
                    columns.append("connection_type")
                    values_sql.append(f"${arg_idx}")
                    update_sql.append("connection_type = EXCLUDED.connection_type")
                    args.append(value)
                    arg_idx += 1
                    continue

                # Optional fields: only include if explicitly provided
                columns.append(key)
                if key == "ip_address":
                    values_sql.append(f"${arg_idx}::inet")
                else:
                    values_sql.append(f"${arg_idx}")
                update_sql.append(f"{key} = EXCLUDED.{key}")
                args.append(value)
                arg_idx += 1

            row = await conn.fetchrow(
                f"""
                INSERT INTO device_connections ({', '.join(columns)})
                VALUES ({', '.join(values_sql)})
                ON CONFLICT (tenant_id, device_id)
                DO UPDATE SET {', '.join(update_sql)}
                RETURNING
                    device_id,
                    connection_type,
                    carrier_name,
                    carrier_account_id,
                    plan_name,
                    apn,
                    sim_iccid,
                    sim_status,
                    data_limit_mb,
                    data_used_mb,
                    data_used_updated_at,
                    billing_cycle_start,
                    ip_address::text AS ip_address,
                    msisdn,
                    network_status,
                    last_network_attach,
                    last_network_detach,
                    created_at,
                    updated_at
                """,
                *args,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to upsert device connection")
        raise HTTPException(status_code=500, detail="Internal server error")

    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = f'</api/v1/customer/devices/{device_id}/transports>; rel="successor-version"'
    return dict(row)


@router.delete("/devices/{device_id}/connection", status_code=204)
async def delete_device_connection(device_id: str, response: Response, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                "DELETE FROM device_connections WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete device connection")
        raise HTTPException(status_code=500, detail="Internal server error")

    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-06-01"
    response.headers["Link"] = f'</api/v1/customer/devices/{device_id}/transports>; rel="successor-version"'
    return Response(status_code=204)


# ── Device Transports (Phase 169) ─────────────────────────────────────────────


class TransportCreate(BaseModel):
    ingestion_protocol: str = Field(
        ...,
        pattern=r"^(mqtt_direct|http_api|lorawan|gateway_proxy|modbus_rtu)$",
    )
    physical_connectivity: str | None = Field(
        default=None,
        pattern=r"^(cellular|ethernet|wifi|satellite|lora|other)$",
    )
    protocol_config: dict[str, Any] = Field(default_factory=dict)
    connectivity_config: dict[str, Any] = Field(default_factory=dict)
    carrier_integration_id: int | None = None
    is_primary: bool = True
    status: str = Field(default="active", pattern=r"^(active|inactive|failover)$")


class TransportUpdate(BaseModel):
    physical_connectivity: str | None = Field(
        default=None,
        pattern=r"^(cellular|ethernet|wifi|satellite|lora|other)$",
    )
    protocol_config: dict[str, Any] | None = None
    connectivity_config: dict[str, Any] | None = None
    carrier_integration_id: int | None = None
    is_primary: bool | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|failover)$")


@router.get("/devices/{device_id}/transports")
async def list_device_transports(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            rows = await conn.fetch(
                """
                SELECT
                    t.id,
                    t.ingestion_protocol,
                    t.physical_connectivity,
                    t.protocol_config,
                    t.connectivity_config,
                    t.carrier_integration_id,
                    ci.display_name AS carrier_display_name,
                    ci.carrier_name AS carrier_name,
                    t.is_primary,
                    t.status,
                    t.last_connected_at,
                    t.created_at,
                    t.updated_at
                FROM device_transports t
                LEFT JOIN carrier_integrations ci
                  ON ci.id = t.carrier_integration_id
                 AND ci.tenant_id = t.tenant_id
                WHERE t.tenant_id = $1 AND t.device_id = $2
                ORDER BY t.is_primary DESC, t.id ASC
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list device transports")
        raise HTTPException(status_code=500, detail="Internal server error")

    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "ingestion_protocol": r["ingestion_protocol"],
                "physical_connectivity": r["physical_connectivity"],
                "protocol_config": r["protocol_config"] if isinstance(r["protocol_config"], dict) else {},
                "connectivity_config": r["connectivity_config"] if isinstance(r["connectivity_config"], dict) else {},
                "carrier_integration_id": r["carrier_integration_id"],
                "carrier": (
                    {"display_name": r["carrier_display_name"], "carrier_name": r["carrier_name"]}
                    if r["carrier_integration_id"]
                    else None
                ),
                "is_primary": r["is_primary"],
                "status": r["status"],
                "last_connected_at": _serialize_time(r["last_connected_at"]),
                "created_at": _serialize_time(r["created_at"]),
                "updated_at": _serialize_time(r["updated_at"]),
            }
        )
    return {"device_id": device_id, "transports": items, "total": len(items)}


@router.post("/devices/{device_id}/transports", status_code=201)
async def create_device_transport(device_id: str, body: TransportCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            if body.carrier_integration_id is not None:
                carrier_ok = await conn.fetchval(
                    "SELECT 1 FROM carrier_integrations WHERE tenant_id = $1 AND id = $2",
                    tenant_id,
                    body.carrier_integration_id,
                )
                if not carrier_ok:
                    raise HTTPException(status_code=404, detail="Carrier integration not found")

            row = await conn.fetchrow(
                """
                INSERT INTO device_transports (
                    tenant_id, device_id, ingestion_protocol, physical_connectivity,
                    protocol_config, connectivity_config, carrier_integration_id,
                    is_primary, status
                )
                VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,$8,$9)
                RETURNING *
                """,
                tenant_id,
                device_id,
                body.ingestion_protocol,
                body.physical_connectivity,
                json.dumps(body.protocol_config),
                json.dumps(body.connectivity_config),
                body.carrier_integration_id,
                body.is_primary,
                body.status,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create device transport")
        raise HTTPException(status_code=500, detail="Internal server error")

    return dict(row)


@router.put("/devices/{device_id}/transports/{transport_id}")
async def update_device_transport(
    device_id: str,
    transport_id: int,
    body: TransportUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates: dict[str, Any] = body.model_dump(exclude_unset=True)
    updates = {k: v for k, v in updates.items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets: list[str] = []
    args: list[Any] = [tenant_id, device_id, transport_id]
    idx = 4

    def add_set(col: str, val: Any, cast: str | None = None):
        nonlocal idx
        if cast:
            sets.append(f"{col} = ${idx}::{cast}")
        else:
            sets.append(f"{col} = ${idx}")
        args.append(val)
        idx += 1

    if "physical_connectivity" in updates:
        add_set("physical_connectivity", updates["physical_connectivity"])
    if "carrier_integration_id" in updates:
        add_set("carrier_integration_id", updates["carrier_integration_id"])
    if "is_primary" in updates:
        add_set("is_primary", updates["is_primary"])
    if "status" in updates:
        add_set("status", updates["status"])
    if "protocol_config" in updates:
        add_set("protocol_config", json.dumps(updates["protocol_config"] or {}), "jsonb")
    if "connectivity_config" in updates:
        add_set("connectivity_config", json.dumps(updates["connectivity_config"] or {}), "jsonb")

    sets.append("updated_at = now()")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            if "carrier_integration_id" in updates and updates["carrier_integration_id"] is not None:
                carrier_ok = await conn.fetchval(
                    "SELECT 1 FROM carrier_integrations WHERE tenant_id = $1 AND id = $2",
                    tenant_id,
                    updates["carrier_integration_id"],
                )
                if not carrier_ok:
                    raise HTTPException(status_code=404, detail="Carrier integration not found")

            row = await conn.fetchrow(
                f"""
                UPDATE device_transports
                SET {", ".join(sets)}
                WHERE tenant_id = $1 AND device_id = $2 AND id = $3
                RETURNING *
                """,
                *args,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device transport")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Transport not found")
    return dict(row)


@router.delete("/devices/{device_id}/transports/{transport_id}", status_code=204)
async def delete_device_transport(device_id: str, transport_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                "DELETE FROM device_transports WHERE tenant_id = $1 AND device_id = $2 AND id = $3 RETURNING id",
                tenant_id,
                device_id,
                transport_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Transport not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete device transport")
        raise HTTPException(status_code=500, detail="Internal server error")
    return Response(status_code=204)


@router.get("/devices/{device_id}/health")
async def get_device_health(
    device_id: str,
    range: str = Query(default="24h"),
    limit: int = Query(default=100, ge=1, le=1000),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    interval = HEALTH_RANGES.get(range)
    if interval is None:
        raise HTTPException(status_code=400, detail="Invalid range")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            rows = await conn.fetch(
                """
                SELECT
                    time, rssi, rsrp, rsrq, sinr, signal_quality, network_type, cell_id,
                    battery_pct, battery_voltage, power_source, charging,
                    cpu_temp_c, memory_used_pct, storage_used_pct, uptime_seconds, reboot_count, error_count,
                    data_tx_bytes, data_rx_bytes, data_session_bytes,
                    gps_lat, gps_lon, gps_accuracy_m, gps_fix
                FROM device_health_telemetry
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND time > now() - $3::interval
                ORDER BY time DESC
                LIMIT $4
                """,
                tenant_id,
                device_id,
                interval,
                limit,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch device health telemetry")
        raise HTTPException(status_code=500, detail="Internal server error")

    points = [_serialize_health_row(r) for r in rows]
    latest = points[0] if points else None
    return {
        "device_id": device_id,
        "range": range,
        "data_points": points,
        "total": len(points),
        "latest": latest,
    }


@router.get("/devices/{device_id}/health/latest")
async def get_device_health_latest(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            row = await conn.fetchrow(
                """
                SELECT
                    time, rssi, rsrp, rsrq, sinr, signal_quality, network_type, cell_id,
                    battery_pct, battery_voltage, power_source, charging,
                    cpu_temp_c, memory_used_pct, storage_used_pct, uptime_seconds, reboot_count, error_count,
                    data_tx_bytes, data_rx_bytes, data_session_bytes,
                    gps_lat, gps_lon, gps_accuracy_m, gps_fix
                FROM device_health_telemetry
                WHERE tenant_id = $1 AND device_id = $2
                ORDER BY time DESC
                LIMIT 1
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch latest device health telemetry")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="No health telemetry found")
    return _serialize_health_row(row)


@router.delete("/sensors/{sensor_id}", status_code=204)
async def delete_sensor(sensor_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                "SELECT id, source FROM device_sensors WHERE tenant_id = $1 AND id = $2",
                tenant_id,
                sensor_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Sensor not found")
            if row["source"] == "required":
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete a required sensor. Deactivate it instead.",
                )
            await conn.execute(
                "DELETE FROM device_sensors WHERE tenant_id = $1 AND id = $2",
                tenant_id,
                sensor_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return Response(status_code=204)

