from datetime import UTC, datetime, timedelta
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from dependencies import get_db_pool
from db.pool import tenant_connection
from middleware.auth import JWTBearer
from middleware.tenant import get_tenant_id, inject_tenant_context, require_customer
from oncall.resolver import get_current_responder, get_shift_end


class OncallLayerIn(BaseModel):
    name: str = "Layer 1"
    rotation_type: Literal["daily", "weekly", "custom"] = "weekly"
    shift_duration_hours: int = 168
    handoff_day: int = Field(default=1, ge=0, le=6)
    handoff_hour: int = Field(default=9, ge=0, le=23)
    responders: List[str] = []
    layer_order: int = 0


class OncallScheduleIn(BaseModel):
    name: str
    description: Optional[str] = None
    timezone: str = "UTC"
    layers: List[OncallLayerIn] = []


class OncallOverrideIn(BaseModel):
    layer_id: Optional[int] = None
    responder: str
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None


router = APIRouter(
    prefix="/customer",
    tags=["oncall"],
    dependencies=[Depends(JWTBearer()), Depends(inject_tenant_context), Depends(require_customer)],
)


async def _fetch_schedule(conn, tenant_id: str, schedule_id: int):
    schedule = await conn.fetchrow(
        """
        SELECT schedule_id, tenant_id, name, description, timezone, created_at, updated_at
        FROM oncall_schedules
        WHERE tenant_id = $1 AND schedule_id = $2
        """,
        tenant_id,
        schedule_id,
    )
    if not schedule:
        return None
    layers = await conn.fetch(
        """
        SELECT layer_id, schedule_id, name, rotation_type, shift_duration_hours, handoff_day,
               handoff_hour, responders, layer_order, created_at
        FROM oncall_layers
        WHERE schedule_id = $1
        ORDER BY layer_order, layer_id
        """,
        schedule_id,
    )
    payload = dict(schedule)
    payload["layers"] = [dict(layer) for layer in layers]
    return payload


@router.get("/oncall-schedules")
async def list_schedules(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT schedule_id
            FROM oncall_schedules
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            """,
            tenant_id,
        )
        schedules = []
        for row in rows:
            schedule = await _fetch_schedule(conn, tenant_id, row["schedule_id"])
            if schedule:
                schedules.append(schedule)
    return {"schedules": schedules}


@router.post("/oncall-schedules", status_code=201)
async def create_schedule(body: OncallScheduleIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO oncall_schedules (tenant_id, name, description, timezone)
            VALUES ($1, $2, $3, $4)
            RETURNING schedule_id
            """,
            tenant_id,
            body.name.strip(),
            body.description,
            body.timezone,
        )
        schedule_id = row["schedule_id"]
        for layer in body.layers:
            await conn.execute(
                """
                INSERT INTO oncall_layers
                  (schedule_id, name, rotation_type, shift_duration_hours, handoff_day, handoff_hour, responders, layer_order)
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
                """,
                schedule_id,
                layer.name,
                layer.rotation_type,
                layer.shift_duration_hours,
                layer.handoff_day,
                layer.handoff_hour,
                __import__("json").dumps(layer.responders),
                layer.layer_order,
            )
        schedule = await _fetch_schedule(conn, tenant_id, schedule_id)
    return schedule


@router.get("/oncall-schedules/{schedule_id}")
async def get_schedule(schedule_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        schedule = await _fetch_schedule(conn, tenant_id, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.put("/oncall-schedules/{schedule_id}")
async def update_schedule(schedule_id: int, body: OncallScheduleIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM oncall_schedules WHERE tenant_id = $1 AND schedule_id = $2",
            tenant_id,
            schedule_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Schedule not found")
        await conn.execute(
            """
            UPDATE oncall_schedules
            SET name = $3, description = $4, timezone = $5, updated_at = NOW()
            WHERE tenant_id = $1 AND schedule_id = $2
            """,
            tenant_id,
            schedule_id,
            body.name.strip(),
            body.description,
            body.timezone,
        )
        await conn.execute("DELETE FROM oncall_layers WHERE schedule_id = $1", schedule_id)
        for layer in body.layers:
            await conn.execute(
                """
                INSERT INTO oncall_layers
                  (schedule_id, name, rotation_type, shift_duration_hours, handoff_day, handoff_hour, responders, layer_order)
                VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
                """,
                schedule_id,
                layer.name,
                layer.rotation_type,
                layer.shift_duration_hours,
                layer.handoff_day,
                layer.handoff_hour,
                __import__("json").dumps(layer.responders),
                layer.layer_order,
            )
        schedule = await _fetch_schedule(conn, tenant_id, schedule_id)
    return schedule


@router.delete("/oncall-schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            "DELETE FROM oncall_schedules WHERE tenant_id = $1 AND schedule_id = $2",
            tenant_id,
            schedule_id,
        )
    if res.endswith("0"):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return Response(status_code=204)


@router.post("/oncall-schedules/{schedule_id}/layers", status_code=201)
async def create_layer(schedule_id: int, body: OncallLayerIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        ok = await conn.fetchval(
            "SELECT 1 FROM oncall_schedules WHERE tenant_id = $1 AND schedule_id = $2",
            tenant_id,
            schedule_id,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Schedule not found")
        row = await conn.fetchrow(
            """
            INSERT INTO oncall_layers
              (schedule_id, name, rotation_type, shift_duration_hours, handoff_day, handoff_hour, responders, layer_order)
            VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
            RETURNING layer_id, schedule_id, name, rotation_type, shift_duration_hours, handoff_day,
                      handoff_hour, responders, layer_order, created_at
            """,
            schedule_id,
            body.name,
            body.rotation_type,
            body.shift_duration_hours,
            body.handoff_day,
            body.handoff_hour,
            __import__("json").dumps(body.responders),
            body.layer_order,
        )
    return dict(row)


@router.put("/oncall-schedules/{schedule_id}/layers/{layer_id}")
async def update_layer(schedule_id: int, layer_id: int, body: OncallLayerIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE oncall_layers l
            SET name = $4, rotation_type = $5, shift_duration_hours = $6,
                handoff_day = $7, handoff_hour = $8, responders = $9::jsonb, layer_order = $10
            FROM oncall_schedules s
            WHERE l.layer_id = $1
              AND l.schedule_id = $2
              AND s.schedule_id = l.schedule_id
              AND s.tenant_id = $3
            RETURNING l.layer_id, l.schedule_id, l.name, l.rotation_type, l.shift_duration_hours,
                      l.handoff_day, l.handoff_hour, l.responders, l.layer_order, l.created_at
            """,
            layer_id,
            schedule_id,
            tenant_id,
            body.name,
            body.rotation_type,
            body.shift_duration_hours,
            body.handoff_day,
            body.handoff_hour,
            __import__("json").dumps(body.responders),
            body.layer_order,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Layer not found")
    return dict(row)


@router.delete("/oncall-schedules/{schedule_id}/layers/{layer_id}", status_code=204)
async def delete_layer(schedule_id: int, layer_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            """
            DELETE FROM oncall_layers l
            USING oncall_schedules s
            WHERE l.layer_id = $1
              AND l.schedule_id = $2
              AND s.schedule_id = l.schedule_id
              AND s.tenant_id = $3
            """,
            layer_id,
            schedule_id,
            tenant_id,
        )
    if res.endswith("0"):
        raise HTTPException(status_code=404, detail="Layer not found")
    return Response(status_code=204)


@router.get("/oncall-schedules/{schedule_id}/overrides")
async def list_overrides(schedule_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT o.override_id, o.layer_id, o.responder, o.start_at, o.end_at, o.reason, o.created_at
            FROM oncall_overrides o
            JOIN oncall_schedules s ON s.schedule_id = o.schedule_id
            WHERE s.tenant_id = $1 AND o.schedule_id = $2
            ORDER BY o.start_at
            """,
            tenant_id,
            schedule_id,
        )
    return {"overrides": [dict(row) for row in rows]}


@router.post("/oncall-schedules/{schedule_id}/overrides", status_code=201)
async def create_override(schedule_id: int, body: OncallOverrideIn, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        ok = await conn.fetchval(
            "SELECT 1 FROM oncall_schedules WHERE tenant_id = $1 AND schedule_id = $2",
            tenant_id,
            schedule_id,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Schedule not found")
        row = await conn.fetchrow(
            """
            INSERT INTO oncall_overrides (schedule_id, layer_id, responder, start_at, end_at, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING override_id, layer_id, responder, start_at, end_at, reason, created_at
            """,
            schedule_id,
            body.layer_id,
            body.responder,
            body.start_at,
            body.end_at,
            body.reason,
        )
    return dict(row)


@router.delete("/oncall-schedules/{schedule_id}/overrides/{override_id}", status_code=204)
async def delete_override(schedule_id: int, override_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            """
            DELETE FROM oncall_overrides o
            USING oncall_schedules s
            WHERE o.override_id = $1
              AND o.schedule_id = $2
              AND s.schedule_id = o.schedule_id
              AND s.tenant_id = $3
            """,
            override_id,
            schedule_id,
            tenant_id,
        )
    if res.endswith("0"):
        raise HTTPException(status_code=404, detail="Override not found")
    return Response(status_code=204)


@router.get("/oncall-schedules/{schedule_id}/current")
async def current_oncall(schedule_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    now = datetime.now(UTC)
    async with tenant_connection(pool, tenant_id) as conn:
        schedule = await _fetch_schedule(conn, tenant_id, schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        override = await conn.fetchrow(
            """
            SELECT responder, end_at
            FROM oncall_overrides
            WHERE schedule_id = $1
              AND start_at <= NOW()
              AND end_at > NOW()
            ORDER BY start_at DESC
            LIMIT 1
            """,
            schedule_id,
        )
        if override:
            return {
                "responder": override["responder"],
                "layer": "Override",
                "until": override["end_at"],
            }
        layers = schedule["layers"]
        if not layers:
            return {"responder": "", "layer": "", "until": now}
        top = layers[0]
        responder = get_current_responder(top, now)
        until = get_shift_end(top, now)
        return {"responder": responder, "layer": top["name"], "until": until}


@router.get("/oncall-schedules/{schedule_id}/timeline")
async def timeline(schedule_id: int, days: int = Query(14, ge=1, le=60), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    now = datetime.now(UTC)
    end = now + timedelta(days=days)
    async with tenant_connection(pool, tenant_id) as conn:
        schedule = await _fetch_schedule(conn, tenant_id, schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        layers = schedule["layers"]
        slots = []
        for layer in layers:
            shift_h = max(1, int(layer.get("shift_duration_hours") or 168))
            cursor = now
            while cursor < end:
                slot_end = min(cursor + timedelta(hours=shift_h), end)
                slots.append(
                    {
                        "start": cursor,
                        "end": slot_end,
                        "responder": get_current_responder(layer, cursor),
                        "layer_name": layer["name"],
                        "is_override": False,
                    }
                )
                cursor = slot_end
        overrides = await conn.fetch(
            """
            SELECT responder, start_at, end_at
            FROM oncall_overrides
            WHERE schedule_id = $1
              AND end_at > $2
              AND start_at < $3
            ORDER BY start_at
            """,
            schedule_id,
            now,
            end,
        )
    for override in overrides:
        slots.append(
            {
                "start": override["start_at"],
                "end": override["end_at"],
                "responder": override["responder"],
                "layer_name": "Override",
                "is_override": True,
            }
        )
    slots.sort(key=lambda item: item["start"])
    return {"slots": slots}
