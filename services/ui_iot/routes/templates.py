import json
import logging
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from db.pool import tenant_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/customer",
    tags=["templates"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    description: str | None = None
    category: str = Field(
        ...,
        pattern=r"^(gateway|edge_device|standalone_sensor|controller|expansion_module)$",
    )
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    firmware_version_pattern: str | None = None
    transport_defaults: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    image_url: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(
        default=None,
        pattern=r"^(gateway|edge_device|standalone_sensor|controller|expansion_module)$",
    )
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    firmware_version_pattern: str | None = None
    transport_defaults: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    image_url: str | None = None


class TemplateMetricCreate(BaseModel):
    metric_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    display_name: str = Field(..., min_length=1, max_length=200)
    data_type: str = Field(..., pattern=r"^(float|integer|boolean|string|enum)$")
    unit: str | None = Field(default=None, max_length=50)
    min_value: float | None = None
    max_value: float | None = None
    precision_digits: int = Field(default=2, ge=0, le=10)
    is_required: bool = False
    description: str | None = None
    enum_values: Any | None = None
    sort_order: int = Field(default=0)


class TemplateMetricUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    data_type: str | None = Field(default=None, pattern=r"^(float|integer|boolean|string|enum)$")
    unit: str | None = Field(default=None, max_length=50)
    min_value: float | None = None
    max_value: float | None = None
    precision_digits: int | None = Field(default=None, ge=0, le=10)
    is_required: bool | None = None
    description: str | None = None
    enum_values: Any | None = None
    sort_order: int | None = None


class TemplateCommandCreate(BaseModel):
    command_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    parameters_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    sort_order: int = Field(default=0)


class TemplateCommandUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    parameters_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    sort_order: int | None = None


class TemplateSlotCreate(BaseModel):
    slot_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    display_name: str = Field(..., min_length=1, max_length=200)
    slot_type: str = Field(..., pattern=r"^(expansion|sensor|accessory)$")
    interface_type: str = Field(
        ...,
        pattern=r"^(analog|rs485|i2c|spi|1-wire|fsk|ble|lora|gpio|usb)$",
    )
    max_devices: int | None = Field(default=1, ge=0)
    compatible_templates: list[int] | None = None
    is_required: bool = False
    description: str | None = None
    sort_order: int = Field(default=0)


class TemplateSlotUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    slot_type: str | None = Field(default=None, pattern=r"^(expansion|sensor|accessory)$")
    interface_type: str | None = Field(
        default=None,
        pattern=r"^(analog|rs485|i2c|spi|1-wire|fsk|ble|lora|gpio|usb)$",
    )
    max_devices: int | None = Field(default=None, ge=0)
    compatible_templates: list[int] | None = None
    is_required: bool | None = None
    description: str | None = None
    sort_order: int | None = None


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return dict(row)


async def _get_editable_template(conn, template_id: int, tenant_id: str):
    """Fetch template and verify it's editable by the current tenant."""
    row = await conn.fetchrow("SELECT * FROM device_templates WHERE id = $1", template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    if row["is_locked"]:
        raise HTTPException(status_code=403, detail="Cannot modify a locked system template")
    if row["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot modify another tenant's template")
    return row


@router.get("/templates")
async def list_templates(
    category: str | None = Query(default=None),
    source: str | None = Query(default=None),
    search: str | None = Query(default=None),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    where = ["(tenant_id IS NULL OR tenant_id = $1)"]
    params: list[Any] = [tenant_id]
    idx = 2

    if category:
        where.append(f"category = ${idx}")
        params.append(category)
        idx += 1
    if source:
        where.append(f"source = ${idx}")
        params.append(source)
        idx += 1
    if search:
        where.append(f"(name ILIKE ${idx} OR slug ILIKE ${idx} OR COALESCE(manufacturer,'') ILIKE ${idx} OR COALESCE(model,'') ILIKE ${idx})")
        params.append(f"%{search}%")
        idx += 1

    where_clause = " AND ".join(where)
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, tenant_id, name, slug, description, category,
                       manufacturer, model, firmware_version_pattern,
                       is_locked, source, transport_defaults, metadata,
                       image_url, created_at, updated_at
                FROM device_templates
                WHERE {where_clause}
                ORDER BY (tenant_id IS NULL) DESC, name ASC
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to list templates")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"templates": [_row_to_dict(r) for r in rows]}


@router.get("/templates/{template_id}")
async def get_template(template_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            tpl = await conn.fetchrow("SELECT * FROM device_templates WHERE id = $1", template_id)
            if not tpl:
                raise HTTPException(status_code=404, detail="Template not found")

            metrics = await conn.fetch(
                "SELECT * FROM template_metrics WHERE template_id = $1 ORDER BY sort_order, id",
                template_id,
            )
            commands = await conn.fetch(
                "SELECT * FROM template_commands WHERE template_id = $1 ORDER BY sort_order, id",
                template_id,
            )
            slots = await conn.fetch(
                "SELECT * FROM template_slots WHERE template_id = $1 ORDER BY sort_order, id",
                template_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch template")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        **_row_to_dict(tpl),
        "metrics": [_row_to_dict(r) for r in metrics],
        "commands": [_row_to_dict(r) for r in commands],
        "slots": [_row_to_dict(r) for r in slots],
    }


@router.post("/templates", status_code=201)
async def create_template(body: TemplateCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO device_templates
                    (tenant_id, name, slug, description, category,
                     manufacturer, model, firmware_version_pattern,
                     is_locked, source, transport_defaults, metadata, image_url)
                VALUES
                    ($1,$2,$3,$4,$5,$6,$7,$8,false,'tenant',$9::jsonb,$10::jsonb,$11)
                RETURNING *
                """,
                tenant_id,
                body.name,
                body.slug,
                body.description,
                body.category,
                body.manufacturer,
                body.model,
                body.firmware_version_pattern,
                json.dumps(body.transport_defaults) if body.transport_defaults is not None else None,
                json.dumps(body.metadata),
                body.image_url,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Template slug already exists")
    except Exception:
        logger.exception("Failed to create template")
        raise HTTPException(status_code=500, detail="Internal server error")

    return _row_to_dict(row)


@router.put("/templates/{template_id}")
async def update_template(template_id: int, body: TemplateUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets: list[str] = []
    params: list[Any] = [template_id]
    idx = 2

    def add_set(col: str, val: Any, cast: str | None = None):
        nonlocal idx
        if cast:
            sets.append(f"{col} = ${idx}::{cast}")
        else:
            sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    if "name" in updates:
        add_set("name", updates["name"])
    if "description" in updates:
        add_set("description", updates["description"])
    if "category" in updates:
        add_set("category", updates["category"])
    if "manufacturer" in updates:
        add_set("manufacturer", updates["manufacturer"])
    if "model" in updates:
        add_set("model", updates["model"])
    if "firmware_version_pattern" in updates:
        add_set("firmware_version_pattern", updates["firmware_version_pattern"])
    if "transport_defaults" in updates:
        add_set(
            "transport_defaults",
            json.dumps(updates["transport_defaults"]) if updates["transport_defaults"] is not None else None,
            "jsonb",
        )
    if "metadata" in updates:
        add_set(
            "metadata",
            json.dumps(updates["metadata"]) if updates["metadata"] is not None else None,
            "jsonb",
        )
    if "image_url" in updates:
        add_set("image_url", updates["image_url"])

    sets.append("updated_at = now()")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            row = await conn.fetchrow(
                f"UPDATE device_templates SET {', '.join(sets)} WHERE id = $1 RETURNING *",
                *params,
            )
    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Template slug already exists")
    except Exception:
        logger.exception("Failed to update template")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return _row_to_dict(row)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            in_use = await conn.fetchval(
                "SELECT COUNT(*) FROM device_registry WHERE template_id = $1",
                template_id,
            )
            if in_use and int(in_use) > 0:
                raise HTTPException(status_code=409, detail="Template is in use by devices")
            deleted = await conn.fetchval(
                "DELETE FROM device_templates WHERE id = $1 RETURNING 1",
                template_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete template")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")
    return Response(status_code=204)


@router.post("/templates/{template_id}/clone", status_code=201)
async def clone_template(template_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            src = await conn.fetchrow("SELECT * FROM device_templates WHERE id = $1", template_id)
            if not src:
                raise HTTPException(status_code=404, detail="Template not found")

            base_slug = str(src["slug"])
            slug = f"{base_slug}-copy"
            for i in range(1, 20):
                exists = await conn.fetchval(
                    "SELECT 1 FROM device_templates WHERE tenant_id = $1 AND slug = $2",
                    tenant_id,
                    slug,
                )
                if not exists:
                    break
                slug = f"{base_slug}-copy{i}"

            new_tpl = await conn.fetchrow(
                """
                INSERT INTO device_templates
                    (tenant_id, name, slug, description, category,
                     manufacturer, model, firmware_version_pattern,
                     is_locked, source, transport_defaults, metadata, image_url)
                VALUES
                    ($1,$2,$3,$4,$5,$6,$7,$8,false,'tenant',$9::jsonb,$10::jsonb,$11)
                RETURNING *
                """,
                tenant_id,
                f"{src['name']} (Copy)",
                slug,
                src["description"],
                src["category"],
                src["manufacturer"],
                src["model"],
                src["firmware_version_pattern"],
                json.dumps(src["transport_defaults"]) if src["transport_defaults"] is not None else None,
                json.dumps(src["metadata"] or {}),
                src["image_url"],
            )
            new_id = int(new_tpl["id"])

            # Copy sub-resources
            await conn.execute(
                """
                INSERT INTO template_metrics
                    (template_id, metric_key, display_name, data_type, unit,
                     min_value, max_value, precision_digits, is_required,
                     description, enum_values, sort_order)
                SELECT $1, metric_key, display_name, data_type, unit,
                       min_value, max_value, precision_digits, is_required,
                       description, enum_values, sort_order
                FROM template_metrics
                WHERE template_id = $2
                """,
                new_id,
                template_id,
            )
            await conn.execute(
                """
                INSERT INTO template_commands
                    (template_id, command_key, display_name, description,
                     parameters_schema, response_schema, sort_order)
                SELECT $1, command_key, display_name, description,
                       parameters_schema, response_schema, sort_order
                FROM template_commands
                WHERE template_id = $2
                """,
                new_id,
                template_id,
            )
            await conn.execute(
                """
                INSERT INTO template_slots
                    (template_id, slot_key, display_name, slot_type, interface_type,
                     max_devices, compatible_templates, is_required, description, sort_order)
                SELECT $1, slot_key, display_name, slot_type, interface_type,
                       max_devices, compatible_templates, is_required, description, sort_order
                FROM template_slots
                WHERE template_id = $2
                """,
                new_id,
                template_id,
            )

            metrics = await conn.fetch(
                "SELECT * FROM template_metrics WHERE template_id = $1 ORDER BY sort_order, id",
                new_id,
            )
            commands = await conn.fetch(
                "SELECT * FROM template_commands WHERE template_id = $1 ORDER BY sort_order, id",
                new_id,
            )
            slots = await conn.fetch(
                "SELECT * FROM template_slots WHERE template_id = $1 ORDER BY sort_order, id",
                new_id,
            )
    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Template slug already exists")
    except Exception:
        logger.exception("Failed to clone template")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        **_row_to_dict(new_tpl),
        "metrics": [_row_to_dict(r) for r in metrics],
        "commands": [_row_to_dict(r) for r in commands],
        "slots": [_row_to_dict(r) for r in slots],
    }


async def _ensure_metric_belongs(conn, template_id: int, metric_id: int) -> asyncpg.Record:
    row = await conn.fetchrow(
        "SELECT * FROM template_metrics WHERE id = $1 AND template_id = $2",
        metric_id,
        template_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Metric not found")
    return row


async def _ensure_command_belongs(conn, template_id: int, command_id: int) -> asyncpg.Record:
    row = await conn.fetchrow(
        "SELECT * FROM template_commands WHERE id = $1 AND template_id = $2",
        command_id,
        template_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    return row


async def _ensure_slot_belongs(conn, template_id: int, slot_id: int) -> asyncpg.Record:
    row = await conn.fetchrow(
        "SELECT * FROM template_slots WHERE id = $1 AND template_id = $2",
        slot_id,
        template_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Slot not found")
    return row


@router.post("/templates/{template_id}/metrics", status_code=201)
async def create_template_metric(template_id: int, body: TemplateMetricCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            row = await conn.fetchrow(
                """
                INSERT INTO template_metrics
                    (template_id, metric_key, display_name, data_type, unit,
                     min_value, max_value, precision_digits, is_required,
                     description, enum_values, sort_order)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12)
                RETURNING *
                """,
                template_id,
                body.metric_key,
                body.display_name,
                body.data_type,
                body.unit,
                body.min_value,
                body.max_value,
                body.precision_digits,
                body.is_required,
                body.description,
                json.dumps(body.enum_values) if body.enum_values is not None else None,
                body.sort_order,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Metric key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create template metric")
        raise HTTPException(status_code=500, detail="Internal server error")
    return _row_to_dict(row)


@router.put("/templates/{template_id}/metrics/{metric_id}")
async def update_template_metric(
    template_id: int,
    metric_id: int,
    body: TemplateMetricUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets: list[str] = []
    params: list[Any] = [metric_id, template_id]
    idx = 3

    def add_set(col: str, val: Any, cast: str | None = None):
        nonlocal idx
        if cast:
            sets.append(f"{col} = ${idx}::{cast}")
        else:
            sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    for col in ("display_name", "data_type", "unit", "min_value", "max_value", "precision_digits", "is_required", "description", "sort_order"):
        if col in updates:
            add_set(col, updates[col])
    if "enum_values" in updates:
        add_set(
            "enum_values",
            json.dumps(updates["enum_values"]) if updates["enum_values"] is not None else None,
            "jsonb",
        )

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            await _ensure_metric_belongs(conn, template_id, metric_id)
            row = await conn.fetchrow(
                f"""
                UPDATE template_metrics
                SET {", ".join(sets)}
                WHERE id = $1 AND template_id = $2
                RETURNING *
                """,
                *params,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Metric key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update template metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Metric not found")
    return _row_to_dict(row)


@router.delete("/templates/{template_id}/metrics/{metric_id}", status_code=204)
async def delete_template_metric(template_id: int, metric_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            deleted = await conn.fetchval(
                "DELETE FROM template_metrics WHERE id = $1 AND template_id = $2 RETURNING 1",
                metric_id,
                template_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete template metric")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not deleted:
        raise HTTPException(status_code=404, detail="Metric not found")
    return Response(status_code=204)


@router.post("/templates/{template_id}/commands", status_code=201)
async def create_template_command(template_id: int, body: TemplateCommandCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            row = await conn.fetchrow(
                """
                INSERT INTO template_commands
                    (template_id, command_key, display_name, description,
                     parameters_schema, response_schema, sort_order)
                VALUES ($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7)
                RETURNING *
                """,
                template_id,
                body.command_key,
                body.display_name,
                body.description,
                json.dumps(body.parameters_schema) if body.parameters_schema is not None else None,
                json.dumps(body.response_schema) if body.response_schema is not None else None,
                body.sort_order,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Command key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create template command")
        raise HTTPException(status_code=500, detail="Internal server error")
    return _row_to_dict(row)


@router.put("/templates/{template_id}/commands/{command_id}")
async def update_template_command(
    template_id: int,
    command_id: int,
    body: TemplateCommandUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets: list[str] = []
    params: list[Any] = [command_id, template_id]
    idx = 3

    def add_set(col: str, val: Any, cast: str | None = None):
        nonlocal idx
        if cast:
            sets.append(f"{col} = ${idx}::{cast}")
        else:
            sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    for col in ("display_name", "description", "sort_order"):
        if col in updates:
            add_set(col, updates[col])
    if "parameters_schema" in updates:
        add_set(
            "parameters_schema",
            json.dumps(updates["parameters_schema"]) if updates["parameters_schema"] is not None else None,
            "jsonb",
        )
    if "response_schema" in updates:
        add_set(
            "response_schema",
            json.dumps(updates["response_schema"]) if updates["response_schema"] is not None else None,
            "jsonb",
        )

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            await _ensure_command_belongs(conn, template_id, command_id)
            row = await conn.fetchrow(
                f"""
                UPDATE template_commands
                SET {", ".join(sets)}
                WHERE id = $1 AND template_id = $2
                RETURNING *
                """,
                *params,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Command key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update template command")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    return _row_to_dict(row)


@router.delete("/templates/{template_id}/commands/{command_id}", status_code=204)
async def delete_template_command(template_id: int, command_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            deleted = await conn.fetchval(
                "DELETE FROM template_commands WHERE id = $1 AND template_id = $2 RETURNING 1",
                command_id,
                template_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete template command")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not deleted:
        raise HTTPException(status_code=404, detail="Command not found")
    return Response(status_code=204)


@router.post("/templates/{template_id}/slots", status_code=201)
async def create_template_slot(template_id: int, body: TemplateSlotCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            row = await conn.fetchrow(
                """
                INSERT INTO template_slots
                    (template_id, slot_key, display_name, slot_type, interface_type,
                     max_devices, compatible_templates, is_required, description, sort_order)
                VALUES ($1,$2,$3,$4,$5,$6,$7::int[],$8,$9,$10)
                RETURNING *
                """,
                template_id,
                body.slot_key,
                body.display_name,
                body.slot_type,
                body.interface_type,
                body.max_devices,
                body.compatible_templates,
                body.is_required,
                body.description,
                body.sort_order,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Slot key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create template slot")
        raise HTTPException(status_code=500, detail="Internal server error")
    return _row_to_dict(row)


@router.put("/templates/{template_id}/slots/{slot_id}")
async def update_template_slot(
    template_id: int,
    slot_id: int,
    body: TemplateSlotUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets: list[str] = []
    params: list[Any] = [slot_id, template_id]
    idx = 3

    def add_set(col: str, val: Any, cast: str | None = None):
        nonlocal idx
        if cast:
            sets.append(f"{col} = ${idx}::{cast}")
        else:
            sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    for col in ("display_name", "slot_type", "interface_type", "max_devices", "is_required", "description", "sort_order"):
        if col in updates:
            add_set(col, updates[col])
    if "compatible_templates" in updates:
        add_set("compatible_templates", updates["compatible_templates"], "int[]")

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            await _ensure_slot_belongs(conn, template_id, slot_id)
            row = await conn.fetchrow(
                f"""
                UPDATE template_slots
                SET {", ".join(sets)}
                WHERE id = $1 AND template_id = $2
                RETURNING *
                """,
                *params,
            )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Slot key already exists on template")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update template slot")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Slot not found")
    return _row_to_dict(row)


@router.delete("/templates/{template_id}/slots/{slot_id}", status_code=204)
async def delete_template_slot(template_id: int, slot_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await _get_editable_template(conn, template_id, tenant_id)
            deleted = await conn.fetchval(
                "DELETE FROM template_slots WHERE id = $1 AND template_id = $2 RETURNING 1",
                slot_id,
                template_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete template slot")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not deleted:
        raise HTTPException(status_code=404, detail="Slot not found")
    return Response(status_code=204)

