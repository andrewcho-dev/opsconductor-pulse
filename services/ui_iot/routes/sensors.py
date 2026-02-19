import logging
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
    "1h": "1 hour",
    "6h": "6 hours",
    "24h": "1 day",
    "7d": "7 days",
    "30d": "30 days",
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


class SensorCreate(BaseModel):
    metric_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    sensor_type: str = Field(..., min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int = Field(default=1, ge=0, le=6)


class SensorUpdate(BaseModel):
    sensor_type: str | None = Field(default=None, min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=20)
    min_range: float | None = None
    max_range: float | None = None
    precision_digits: int | None = Field(default=None, ge=0, le=6)
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")


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
    sensor_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
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

            where_clauses: list[str] = ["tenant_id = $1", "device_id = $2"]
            args: list[Any] = [tenant_id, device_id]
            arg_idx = 3
            if sensor_type:
                where_clauses.append(f"sensor_type = ${arg_idx}")
                args.append(sensor_type)
                arg_idx += 1
            if status:
                where_clauses.append(f"status = ${arg_idx}")
                args.append(status)
                arg_idx += 1

            rows = await conn.fetch(
                f"""
                SELECT
                    sensor_id,
                    metric_name,
                    sensor_type,
                    label,
                    unit,
                    min_range,
                    max_range,
                    precision_digits,
                    status,
                    auto_discovered,
                    last_value,
                    last_seen_at,
                    created_at
                FROM sensors
                WHERE {' AND '.join(where_clauses)}
                ORDER BY metric_name
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
        "sensors": [dict(r) for r in rows],
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
            where_clauses: list[str] = ["tenant_id = $1"]
            args: list[Any] = [tenant_id]
            arg_idx = 2

            if sensor_type:
                where_clauses.append(f"sensor_type = ${arg_idx}")
                args.append(sensor_type)
                arg_idx += 1
            if status:
                where_clauses.append(f"status = ${arg_idx}")
                args.append(status)
                arg_idx += 1
            if device_id:
                where_clauses.append(f"device_id = ${arg_idx}")
                args.append(device_id)
                arg_idx += 1

            where_sql = " AND ".join(where_clauses)

            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM sensors WHERE {where_sql}",
                *args,
            )
            rows = await conn.fetch(
                f"""
                SELECT
                    sensor_id,
                    device_id,
                    metric_name,
                    sensor_type,
                    label,
                    unit,
                    min_range,
                    max_range,
                    precision_digits,
                    status,
                    auto_discovered,
                    last_value,
                    last_seen_at,
                    created_at
                FROM sensors
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
async def create_sensor(device_id: str, payload: SensorCreate, pool=Depends(get_db_pool)):
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

            result = await check_sensor_limit(conn, tenant_id, device_id)
            if not result["allowed"]:
                raise HTTPException(status_code=result["status_code"], detail=result["message"])

            dup = await conn.fetchval(
                """
                SELECT 1
                FROM sensors
                WHERE tenant_id = $1 AND device_id = $2 AND metric_name = $3
                """,
                tenant_id,
                device_id,
                payload.metric_name,
            )
            if dup:
                raise HTTPException(
                    status_code=409,
                    detail=f"Sensor with metric_name '{payload.metric_name}' already exists on this device",
                )

            row = await conn.fetchrow(
                """
                INSERT INTO sensors (
                    tenant_id,
                    device_id,
                    metric_name,
                    sensor_type,
                    label,
                    unit,
                    min_range,
                    max_range,
                    precision_digits,
                    status,
                    auto_discovered
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'active',false)
                RETURNING
                    sensor_id,
                    device_id,
                    metric_name,
                    sensor_type,
                    label,
                    unit,
                    min_range,
                    max_range,
                    precision_digits,
                    status,
                    auto_discovered,
                    last_value,
                    last_seen_at,
                    created_at
                """,
                tenant_id,
                device_id,
                payload.metric_name,
                payload.sensor_type,
                payload.label,
                payload.unit,
                payload.min_range,
                payload.max_range,
                payload.precision_digits,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return dict(row)


@router.put("/sensors/{sensor_id}")
async def update_sensor(sensor_id: int, payload: SensorUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            existing = await conn.fetchrow(
                "SELECT sensor_id FROM sensors WHERE tenant_id = $1 AND sensor_id = $2",
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
                UPDATE sensors
                SET {', '.join(set_parts)}
                WHERE tenant_id = $1 AND sensor_id = $2
                RETURNING
                    sensor_id,
                    device_id,
                    metric_name,
                    sensor_type,
                    label,
                    unit,
                    min_range,
                    max_range,
                    precision_digits,
                    status,
                    auto_discovered,
                    last_value,
                    last_seen_at,
                    created_at,
                    updated_at
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
async def get_device_connection(device_id: str, pool=Depends(get_db_pool)):
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

    if not row:
        return {"device_id": device_id, "connection": None}
    return dict(row)


@router.put("/devices/{device_id}/connection")
async def upsert_device_connection(
    device_id: str,
    payload: ConnectionUpsert,
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

    return dict(row)


@router.delete("/devices/{device_id}/connection", status_code=204)
async def delete_device_connection(device_id: str, pool=Depends(get_db_pool)):
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
                  AND time > now() - $3::INTERVAL
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
                "DELETE FROM sensors WHERE tenant_id = $1 AND sensor_id = $2 RETURNING sensor_id",
                tenant_id,
                sensor_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Sensor not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete sensor")
        raise HTTPException(status_code=500, detail="Internal server error")

    return Response(status_code=204)

