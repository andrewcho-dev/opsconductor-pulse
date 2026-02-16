import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from middleware.auth import JWTBearer
from middleware.tenant import (
    inject_tenant_context,
    get_tenant_id,
    get_user,
    require_customer,
)
from db.pool import tenant_connection
from dependencies import get_db_pool

logger = logging.getLogger(__name__)

# Valid widget types
WIDGET_TYPES = {
    "kpi_tile",
    "line_chart",
    "bar_chart",
    "gauge",
    "table",
    "alert_feed",
    "fleet_status",
    "device_count",
    "health_score",
}

# Default dashboard template widgets
DEFAULT_CUSTOMER_WIDGETS = [
    {
        "widget_type": "fleet_status",
        "title": "Fleet Status",
        "config": {},
        "position": {"x": 0, "y": 0, "w": 3, "h": 3},
    },
    {
        "widget_type": "device_count",
        "title": "Total Devices",
        "config": {},
        "position": {"x": 3, "y": 0, "w": 2, "h": 1},
    },
    {
        "widget_type": "kpi_tile",
        "title": "Open Alerts",
        "config": {"metric": "alert_count", "aggregation": "count", "time_range": "24h"},
        "position": {"x": 5, "y": 0, "w": 2, "h": 1},
    },
    {
        "widget_type": "kpi_tile",
        "title": "Fleet Uptime",
        "config": {"metric": "uptime_pct", "aggregation": "avg", "time_range": "24h"},
        "position": {"x": 7, "y": 0, "w": 2, "h": 1},
    },
    {
        "widget_type": "alert_feed",
        "title": "Active Alerts",
        "config": {"severity_filter": "", "max_items": 20},
        "position": {"x": 3, "y": 1, "w": 4, "h": 3},
    },
    {
        "widget_type": "table",
        "title": "Recent Devices",
        "config": {"limit": 10, "sort_by": "last_seen", "filter_status": ""},
        "position": {"x": 7, "y": 1, "w": 5, "h": 3},
    },
    {
        "widget_type": "health_score",
        "title": "Fleet Health",
        "config": {},
        "position": {"x": 0, "y": 3, "w": 6, "h": 2},
    },
]

DEFAULT_OPERATOR_WIDGETS = [
    {
        "widget_type": "kpi_tile",
        "title": "Total Tenants",
        "config": {"metric": "tenant_count", "aggregation": "count"},
        "position": {"x": 0, "y": 0, "w": 2, "h": 1},
    },
    {
        "widget_type": "kpi_tile",
        "title": "Total Devices",
        "config": {"metric": "device_count", "aggregation": "count"},
        "position": {"x": 2, "y": 0, "w": 2, "h": 1},
    },
    {
        "widget_type": "health_score",
        "title": "System Health",
        "config": {},
        "position": {"x": 0, "y": 1, "w": 6, "h": 2},
    },
    {
        "widget_type": "alert_feed",
        "title": "System Alerts",
        "config": {"severity_filter": "", "max_items": 30},
        "position": {"x": 6, "y": 0, "w": 6, "h": 3},
    },
]

router = APIRouter(
    prefix="/customer/dashboards",
    tags=["dashboards"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_default: Optional[bool] = None


class DashboardShareUpdate(BaseModel):
    shared: bool


class WidgetCreate(BaseModel):
    widget_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(default="", max_length=100)
    config: dict = Field(default_factory=dict)
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 2, "h": 2})


class WidgetUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    config: Optional[dict] = None
    position: Optional[dict] = None


class LayoutItem(BaseModel):
    widget_id: int
    x: int
    y: int
    w: int
    h: int


class LayoutBatchUpdate(BaseModel):
    layout: list[LayoutItem]


@router.get("")
async def list_dashboards(pool=Depends(get_db_pool)):
    """List user's personal dashboards + shared dashboards for this tenant."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, user_id, name, description, is_default,
                   created_at, updated_at,
                   (SELECT COUNT(*) FROM dashboard_widgets dw WHERE dw.dashboard_id = d.id) AS widget_count
            FROM dashboards d
            WHERE d.tenant_id = $1
              AND (d.user_id = $2 OR d.user_id IS NULL)
            ORDER BY d.is_default DESC, d.updated_at DESC
            """,
            tenant_id,
            user_id,
        )

    return {
        "dashboards": [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "is_default": r["is_default"],
                "is_shared": r["user_id"] is None,
                "is_owner": r["user_id"] == user_id,
                "widget_count": r["widget_count"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post("", status_code=201)
async def create_dashboard(data: DashboardCreate, pool=Depends(get_db_pool)):
    """Create a new personal dashboard."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM dashboards WHERE tenant_id = $1 AND user_id = $2",
            tenant_id,
            user_id,
        )
        if count >= 20:
            raise HTTPException(400, "Maximum 20 dashboards per user")

        if data.is_default:
            await conn.execute(
                """
                UPDATE dashboards SET is_default = false, updated_at = NOW()
                WHERE tenant_id = $1 AND user_id = $2 AND is_default = true
                """,
                tenant_id,
                user_id,
            )

        row = await conn.fetchrow(
            """
            INSERT INTO dashboards (tenant_id, user_id, name, description, is_default)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, description, is_default, created_at
            """,
            tenant_id,
            user_id,
            data.name.strip(),
            data.description.strip(),
            data.is_default,
        )

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "is_default": row["is_default"],
        "is_shared": False,
        "is_owner": True,
        "widgets": [],
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/{dashboard_id}")
async def get_dashboard(dashboard_id: int, pool=Depends(get_db_pool)):
    """Get a dashboard with all its widgets."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        dashboard = await conn.fetchrow(
            """
            SELECT id, tenant_id, user_id, name, description, is_default, layout,
                   created_at, updated_at
            FROM dashboards
            WHERE id = $1 AND tenant_id = $2
              AND (user_id = $3 OR user_id IS NULL)
            """,
            dashboard_id,
            tenant_id,
            user_id,
        )
        if not dashboard:
            raise HTTPException(404, "Dashboard not found")

        widgets = await conn.fetch(
            """
            SELECT id, widget_type, title, config, position, created_at, updated_at
            FROM dashboard_widgets
            WHERE dashboard_id = $1
            ORDER BY id
            """,
            dashboard_id,
        )

    return {
        "id": dashboard["id"],
        "name": dashboard["name"],
        "description": dashboard["description"],
        "is_default": dashboard["is_default"],
        "is_shared": dashboard["user_id"] is None,
        "is_owner": dashboard["user_id"] == user_id,
        "layout": dashboard["layout"],
        "widgets": [
            {
                "id": w["id"],
                "widget_type": w["widget_type"],
                "title": w["title"],
                "config": w["config"],
                "position": w["position"],
                "created_at": w["created_at"].isoformat() if w["created_at"] else None,
                "updated_at": w["updated_at"].isoformat() if w["updated_at"] else None,
            }
            for w in widgets
        ],
        "created_at": dashboard["created_at"].isoformat() if dashboard["created_at"] else None,
        "updated_at": dashboard["updated_at"].isoformat() if dashboard["updated_at"] else None,
    }


@router.put("/{dashboard_id}")
async def update_dashboard(dashboard_id: int, data: DashboardUpdate, pool=Depends(get_db_pool)):
    """Update dashboard name/description. Only owner can update."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            "SELECT id, user_id FROM dashboards WHERE id = $1 AND tenant_id = $2",
            dashboard_id,
            tenant_id,
        )
        if not existing:
            raise HTTPException(404, "Dashboard not found")
        if existing["user_id"] is not None and existing["user_id"] != user_id:
            raise HTTPException(403, "Only the owner can update this dashboard")

        sets = []
        params: list[object] = []
        idx = 1

        if data.name is not None:
            sets.append(f"name = ${idx}")
            params.append(data.name.strip())
            idx += 1
        if data.description is not None:
            sets.append(f"description = ${idx}")
            params.append(data.description.strip())
            idx += 1
        if data.is_default is not None:
            if data.is_default:
                await conn.execute(
                    """
                    UPDATE dashboards SET is_default = false, updated_at = NOW()
                    WHERE tenant_id = $1 AND user_id = $2 AND is_default = true AND id != $3
                    """,
                    tenant_id,
                    user_id,
                    dashboard_id,
                )
            sets.append(f"is_default = ${idx}")
            params.append(data.is_default)
            idx += 1

        if not sets:
            raise HTTPException(400, "No fields to update")

        sets.append("updated_at = NOW()")
        params.append(dashboard_id)
        params.append(tenant_id)

        query = f"""
            UPDATE dashboards SET {', '.join(sets)}
            WHERE id = ${idx} AND tenant_id = ${idx + 1}
            RETURNING id, name, description, is_default, updated_at
        """
        row = await conn.fetchrow(query, *params)

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "is_default": row["is_default"],
        "updated_at": row["updated_at"].isoformat(),
    }


@router.put("/{dashboard_id}/share")
async def toggle_share(
    dashboard_id: int, data: DashboardShareUpdate, pool=Depends(get_db_pool)
):
    """Share or unshare a dashboard. Only the owner can share.
    When shared, user_id is set to NULL (visible to all tenant members).
    When unshared, user_id is set back to the current user.
    """
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            "SELECT id, user_id FROM dashboards WHERE id = $1 AND tenant_id = $2",
            dashboard_id,
            tenant_id,
        )
        if not existing:
            raise HTTPException(404, "Dashboard not found")

        # Only the original owner can share/unshare
        # Simplified: allow share if user_id matches or if user_id is NULL (already shared).
        if existing["user_id"] is not None and existing["user_id"] != user_id:
            raise HTTPException(403, "Only the owner can share/unshare this dashboard")

        new_user_id = None if data.shared else user_id

        await conn.execute(
            "UPDATE dashboards SET user_id = $1, updated_at = NOW() WHERE id = $2 AND tenant_id = $3",
            new_user_id,
            dashboard_id,
            tenant_id,
        )

    return {"id": dashboard_id, "is_shared": data.shared}


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: int, pool=Depends(get_db_pool)):
    """Delete a dashboard. Only the owner can delete. Cascade deletes widgets."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            "SELECT id, user_id FROM dashboards WHERE id = $1 AND tenant_id = $2",
            dashboard_id,
            tenant_id,
        )
        if not existing:
            raise HTTPException(404, "Dashboard not found")
        if existing["user_id"] is not None and existing["user_id"] != user_id:
            raise HTTPException(403, "Only the owner can delete this dashboard")

        await conn.execute(
            "DELETE FROM dashboards WHERE id = $1 AND tenant_id = $2",
            dashboard_id,
            tenant_id,
        )

    return None


@router.post("/{dashboard_id}/widgets", status_code=201)
async def add_widget(dashboard_id: int, data: WidgetCreate, pool=Depends(get_db_pool)):
    """Add a widget to a dashboard."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    if data.widget_type not in WIDGET_TYPES:
        raise HTTPException(
            400,
            f"Invalid widget_type. Must be one of: {', '.join(sorted(WIDGET_TYPES))}",
        )

    async with tenant_connection(pool, tenant_id) as conn:
        dashboard = await conn.fetchrow(
            """
            SELECT id, user_id FROM dashboards
            WHERE id = $1 AND tenant_id = $2
              AND (user_id = $3 OR user_id IS NULL)
            """,
            dashboard_id,
            tenant_id,
            user_id,
        )
        if not dashboard:
            raise HTTPException(404, "Dashboard not found")
        if dashboard["user_id"] is not None and dashboard["user_id"] != user_id:
            raise HTTPException(403, "Cannot add widgets to another user's dashboard")

        widget_count = await conn.fetchval(
            "SELECT COUNT(*) FROM dashboard_widgets WHERE dashboard_id = $1",
            dashboard_id,
        )
        if widget_count >= 30:
            raise HTTPException(400, "Maximum 30 widgets per dashboard")

        row = await conn.fetchrow(
            """
            INSERT INTO dashboard_widgets (dashboard_id, widget_type, title, config, position)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, widget_type, title, config, position, created_at
            """,
            dashboard_id,
            data.widget_type,
            data.title.strip(),
            data.config,
            data.position,
        )

    return {
        "id": row["id"],
        "widget_type": row["widget_type"],
        "title": row["title"],
        "config": row["config"],
        "position": row["position"],
        "created_at": row["created_at"].isoformat(),
    }


@router.put("/{dashboard_id}/widgets/{widget_id}")
async def update_widget(
    dashboard_id: int, widget_id: int, data: WidgetUpdate, pool=Depends(get_db_pool)
):
    """Update a widget's title, config, or position."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        dashboard = await conn.fetchrow(
            """
            SELECT id, user_id FROM dashboards
            WHERE id = $1 AND tenant_id = $2
              AND (user_id = $3 OR user_id IS NULL)
            """,
            dashboard_id,
            tenant_id,
            user_id,
        )
        if not dashboard:
            raise HTTPException(404, "Dashboard not found")

        widget = await conn.fetchrow(
            "SELECT id FROM dashboard_widgets WHERE id = $1 AND dashboard_id = $2",
            widget_id,
            dashboard_id,
        )
        if not widget:
            raise HTTPException(404, "Widget not found")

        sets = []
        params: list[object] = []
        idx = 1

        if data.title is not None:
            sets.append(f"title = ${idx}")
            params.append(data.title.strip())
            idx += 1
        if data.config is not None:
            sets.append(f"config = ${idx}")
            params.append(data.config)
            idx += 1
        if data.position is not None:
            sets.append(f"position = ${idx}")
            params.append(data.position)
            idx += 1

        if not sets:
            raise HTTPException(400, "No fields to update")

        sets.append("updated_at = NOW()")
        params.append(widget_id)
        params.append(dashboard_id)

        query = f"""
            UPDATE dashboard_widgets SET {', '.join(sets)}
            WHERE id = ${idx} AND dashboard_id = ${idx + 1}
            RETURNING id, widget_type, title, config, position, updated_at
        """
        row = await conn.fetchrow(query, *params)

    return {
        "id": row["id"],
        "widget_type": row["widget_type"],
        "title": row["title"],
        "config": row["config"],
        "position": row["position"],
        "updated_at": row["updated_at"].isoformat(),
    }


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def remove_widget(dashboard_id: int, widget_id: int, pool=Depends(get_db_pool)):
    """Remove a widget from a dashboard."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        dashboard = await conn.fetchrow(
            """
            SELECT id, user_id FROM dashboards
            WHERE id = $1 AND tenant_id = $2
              AND (user_id = $3 OR user_id IS NULL)
            """,
            dashboard_id,
            tenant_id,
            user_id,
        )
        if not dashboard:
            raise HTTPException(404, "Dashboard not found")

        result = await conn.execute(
            "DELETE FROM dashboard_widgets WHERE id = $1 AND dashboard_id = $2",
            widget_id,
            dashboard_id,
        )
        if result == "DELETE 0":
            raise HTTPException(404, "Widget not found")

    return None


@router.put("/{dashboard_id}/layout")
async def batch_update_layout(
    dashboard_id: int, data: LayoutBatchUpdate, pool=Depends(get_db_pool)
):
    """Batch update all widget positions (called after drag-drop save)."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    async with tenant_connection(pool, tenant_id) as conn:
        dashboard = await conn.fetchrow(
            """
            SELECT id, user_id FROM dashboards
            WHERE id = $1 AND tenant_id = $2
              AND (user_id = $3 OR user_id IS NULL)
            """,
            dashboard_id,
            tenant_id,
            user_id,
        )
        if not dashboard:
            raise HTTPException(404, "Dashboard not found")

        for item in data.layout:
            await conn.execute(
                """
                UPDATE dashboard_widgets
                SET position = $1, updated_at = NOW()
                WHERE id = $2 AND dashboard_id = $3
                """,
                {"x": item.x, "y": item.y, "w": item.w, "h": item.h},
                item.widget_id,
                dashboard_id,
            )

        await conn.execute(
            "UPDATE dashboards SET updated_at = NOW() WHERE id = $1",
            dashboard_id,
        )

    return {"ok": True}


@router.post("/bootstrap", status_code=201)
async def bootstrap_default_dashboard(pool=Depends(get_db_pool)):
    """Create a default dashboard for the current user if they have none.
    Called by the frontend on first visit.
    Returns the existing default if one already exists (idempotent).
    """
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    realm_access = user.get("realm_access", {}) or {}
    roles = set(realm_access.get("roles", []) or [])
    is_operator = "operator" in roles or "operator-admin" in roles

    async with tenant_connection(pool, tenant_id) as conn:
        existing = await conn.fetchrow(
            """
            SELECT id FROM dashboards
            WHERE tenant_id = $1 AND user_id = $2
            LIMIT 1
            """,
            tenant_id,
            user_id,
        )
        if existing:
            return {"id": existing["id"], "created": False}

        shared = await conn.fetchrow(
            """
            SELECT id FROM dashboards
            WHERE tenant_id = $1 AND user_id IS NULL
            LIMIT 1
            """,
            tenant_id,
        )
        if shared:
            return {"id": shared["id"], "created": False}

        template_widgets = DEFAULT_OPERATOR_WIDGETS if is_operator else DEFAULT_CUSTOMER_WIDGETS
        dashboard_name = "Operator Overview" if is_operator else "Fleet Overview"

        row = await conn.fetchrow(
            """
            INSERT INTO dashboards (tenant_id, user_id, name, description, is_default)
            VALUES ($1, $2, $3, $4, true)
            RETURNING id
            """,
            tenant_id,
            user_id,
            dashboard_name,
            "Default dashboard created automatically",
        )
        dashboard_id = row["id"]

        for widget in template_widgets:
            await conn.execute(
                """
                INSERT INTO dashboard_widgets (dashboard_id, widget_type, title, config, position)
                VALUES ($1, $2, $3, $4, $5)
                """,
                dashboard_id,
                widget["widget_type"],
                widget["title"],
                widget["config"],
                widget["position"],
            )

    return {"id": dashboard_id, "created": True}

