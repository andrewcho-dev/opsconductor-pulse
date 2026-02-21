# Task 001: Widget System -- DB Migration, Backend CRUD, Frontend Widget Registry

**Commit message**: `feat(dashboards): add dashboard/widget CRUD API and widget registry`

---

## 1. Database Migration

Create file: `db/migrations/081_dashboards.sql`

```sql
-- Migration 081: Customizable Dashboards
-- Creates dashboards and dashboard_widgets tables with RLS policies.
-- Date: 2026-02-16

-- ============================================================
-- DASHBOARDS
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboards (
    id              SERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    user_id         VARCHAR(255),        -- NULL = shared dashboard, non-NULL = personal
    name            VARCHAR(100) NOT NULL,
    description     TEXT DEFAULT '',
    is_default      BOOLEAN NOT NULL DEFAULT false,
    layout          JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboards_tenant ON dashboards(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_tenant_user ON dashboards(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_dashboards_default ON dashboards(tenant_id, is_default) WHERE is_default = true;

ALTER TABLE dashboards ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboards FORCE ROW LEVEL SECURITY;

-- Tenant isolation: tenant users can see their own + shared dashboards
DROP POLICY IF EXISTS dashboards_tenant_isolation ON dashboards;
CREATE POLICY dashboards_tenant_isolation
    ON dashboards
    FOR ALL
    TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- ============================================================
-- DASHBOARD WIDGETS
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboard_widgets (
    id              SERIAL PRIMARY KEY,
    dashboard_id    INT NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    widget_type     VARCHAR(50) NOT NULL,
    title           VARCHAR(100) NOT NULL DEFAULT '',
    config          JSONB NOT NULL DEFAULT '{}',
    position        JSONB NOT NULL DEFAULT '{"x": 0, "y": 0, "w": 2, "h": 2}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_dashboard ON dashboard_widgets(dashboard_id);

-- RLS: widgets inherit access from their parent dashboard via join
ALTER TABLE dashboard_widgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_widgets FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dashboard_widgets_tenant_isolation ON dashboard_widgets;
CREATE POLICY dashboard_widgets_tenant_isolation
    ON dashboard_widgets
    FOR ALL
    TO pulse_app
    USING (
        EXISTS (
            SELECT 1 FROM dashboards d
            WHERE d.id = dashboard_widgets.dashboard_id
            AND d.tenant_id = current_setting('app.tenant_id', true)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM dashboards d
            WHERE d.id = dashboard_widgets.dashboard_id
            AND d.tenant_id = current_setting('app.tenant_id', true)
        )
    );

-- ============================================================
-- GRANTS
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboards TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboards TO pulse_operator;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard_widgets TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dashboard_widgets TO pulse_operator;
GRANT USAGE ON SEQUENCE dashboards_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dashboards_id_seq TO pulse_operator;
GRANT USAGE ON SEQUENCE dashboard_widgets_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dashboard_widgets_id_seq TO pulse_operator;

-- Add dashboard permissions to the permissions table (from migration 080)
INSERT INTO permissions (action, category, description) VALUES
    ('dashboard.write', 'dashboard', 'Create, edit, delete dashboards'),
    ('dashboard.share', 'dashboard', 'Share dashboards with team')
ON CONFLICT (action) DO NOTHING;

-- Grant dashboard.write to roles that already have dashboard.read
-- (Device Manager, Alert Manager, Integration Manager, Team Admin, Full Admin)
INSERT INTO role_permissions (role_id, permission_id)
SELECT rp.role_id, p.id
FROM role_permissions rp
JOIN permissions existing ON existing.id = rp.permission_id AND existing.action = 'dashboard.read'
JOIN permissions p ON p.action = 'dashboard.write'
ON CONFLICT DO NOTHING;
```

**Run**: `psql -U iot -d iotcloud -f db/migrations/081_dashboards.sql`

**Verify**: `psql -U iot -d iotcloud -c "\d dashboards"` and `\d dashboard_widgets` should show the tables.

---

## 2. Backend Routes

Create file: `services/ui_iot/routes/dashboards.py`

This is a NEW file. Follow the exact same patterns as `routes/customer.py`:
- Use `APIRouter` with prefix `/customer/dashboards`
- Dependencies: `JWTBearer()`, `inject_tenant_context`, `require_customer`
- Use `tenant_connection(pool, tenant_id)` for all DB access
- Use `get_tenant_id()` and `get_user()` from `middleware.tenant`
- Use `get_db_pool` from `dependencies`

```python
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, get_user, require_customer
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

router = APIRouter(
    prefix="/customer/dashboards",
    tags=["dashboards"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


# --- Pydantic Models ---

class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    is_default: bool = False


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_default: Optional[bool] = None


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


# --- Dashboard CRUD ---

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
        # Limit: max 20 dashboards per user
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM dashboards WHERE tenant_id = $1 AND user_id = $2",
            tenant_id,
            user_id,
        )
        if count >= 20:
            raise HTTPException(400, "Maximum 20 dashboards per user")

        # If setting as default, unset other defaults for this user
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
        params = []
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
                # Unset other defaults for this user
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


# --- Widget CRUD ---

@router.post("/{dashboard_id}/widgets", status_code=201)
async def add_widget(dashboard_id: int, data: WidgetCreate, pool=Depends(get_db_pool)):
    """Add a widget to a dashboard."""
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    if data.widget_type not in WIDGET_TYPES:
        raise HTTPException(400, f"Invalid widget_type. Must be one of: {', '.join(sorted(WIDGET_TYPES))}")

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
        # Only owner (or shared dashboard editors) can add widgets
        if dashboard["user_id"] is not None and dashboard["user_id"] != user_id:
            raise HTTPException(403, "Cannot add widgets to another user's dashboard")

        # Limit: max 30 widgets per dashboard
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
        params = []
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
```

### Register the router in app.py

Edit `services/ui_iot/app.py`:

1. Add import at the top with other route imports:
```python
from routes.dashboards import router as dashboards_router
```

2. Add `app.include_router(dashboards_router)` alongside the other `include_router` calls (after the `customer_router` line):
```python
app.include_router(customer_router)
app.include_router(dashboards_router)  # <-- ADD THIS LINE
```

---

## 3. Frontend: API Service

Create file: `frontend/src/services/api/dashboards.ts`

```typescript
import { apiGet, apiPost, apiPut, apiDelete } from "./client";

// --- Types ---

export interface DashboardSummary {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  is_shared: boolean;
  is_owner: boolean;
  widget_count: number;
  created_at: string;
  updated_at: string;
}

export interface WidgetPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DashboardWidget {
  id: number;
  widget_type: WidgetType;
  title: string;
  config: Record<string, unknown>;
  position: WidgetPosition;
  created_at: string;
  updated_at: string;
}

export interface Dashboard {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  is_shared: boolean;
  is_owner: boolean;
  layout: unknown[];
  widgets: DashboardWidget[];
  created_at: string;
  updated_at: string;
}

export type WidgetType =
  | "kpi_tile"
  | "line_chart"
  | "bar_chart"
  | "gauge"
  | "table"
  | "alert_feed"
  | "fleet_status"
  | "device_count"
  | "health_score";

export interface LayoutItem {
  widget_id: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

// --- API Functions ---

export async function fetchDashboards(): Promise<{ dashboards: DashboardSummary[]; total: number }> {
  return apiGet("/customer/dashboards");
}

export async function fetchDashboard(id: number): Promise<Dashboard> {
  return apiGet(`/customer/dashboards/${id}`);
}

export async function createDashboard(data: {
  name: string;
  description?: string;
  is_default?: boolean;
}): Promise<Dashboard> {
  return apiPost("/customer/dashboards", data);
}

export async function updateDashboard(
  id: number,
  data: { name?: string; description?: string; is_default?: boolean }
): Promise<Dashboard> {
  return apiPut(`/customer/dashboards/${id}`, data);
}

export async function deleteDashboard(id: number): Promise<void> {
  return apiDelete(`/customer/dashboards/${id}`);
}

export async function addWidget(
  dashboardId: number,
  data: {
    widget_type: WidgetType;
    title?: string;
    config?: Record<string, unknown>;
    position?: WidgetPosition;
  }
): Promise<DashboardWidget> {
  return apiPost(`/customer/dashboards/${dashboardId}/widgets`, data);
}

export async function updateWidget(
  dashboardId: number,
  widgetId: number,
  data: {
    title?: string;
    config?: Record<string, unknown>;
    position?: WidgetPosition;
  }
): Promise<DashboardWidget> {
  return apiPut(`/customer/dashboards/${dashboardId}/widgets/${widgetId}`, data);
}

export async function removeWidget(dashboardId: number, widgetId: number): Promise<void> {
  return apiDelete(`/customer/dashboards/${dashboardId}/widgets/${widgetId}`);
}

export async function batchUpdateLayout(
  dashboardId: number,
  layout: LayoutItem[]
): Promise<{ ok: boolean }> {
  return apiPut(`/customer/dashboards/${dashboardId}/layout`, { layout });
}
```

---

## 4. Frontend: Widget Registry

Create file: `frontend/src/features/dashboard/widgets/widget-registry.ts`

This maps widget_type strings to their React component, display metadata, and default config.

```typescript
import type { ComponentType } from "react";
import type { WidgetType } from "@/services/api/dashboards";

export interface WidgetDefinition {
  type: WidgetType;
  label: string;
  description: string;
  icon: string; // lucide icon name
  defaultTitle: string;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  maxSize: { w: number; h: number };
  defaultConfig: Record<string, unknown>;
  /** Lazy-loaded component. Receives { config, title } props */
  component: () => Promise<{ default: ComponentType<WidgetRendererProps> }>;
}

export interface WidgetRendererProps {
  config: Record<string, unknown>;
  title: string;
  widgetId: number;
}

export const WIDGET_REGISTRY: Record<WidgetType, WidgetDefinition> = {
  kpi_tile: {
    type: "kpi_tile",
    label: "KPI Tile",
    description: "Single metric value with trend indicator",
    icon: "Hash",
    defaultTitle: "KPI",
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 1, h: 1 },
    maxSize: { w: 4, h: 2 },
    defaultConfig: { metric: "device_count", aggregation: "count", time_range: "24h" },
    component: () => import("./renderers/KpiTileRenderer"),
  },
  line_chart: {
    type: "line_chart",
    label: "Line Chart",
    description: "Time-series line chart for metrics",
    icon: "TrendingUp",
    defaultTitle: "Metric Trend",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { metric: "temperature", time_range: "24h", devices: [] },
    component: () => import("./renderers/LineChartRenderer"),
  },
  bar_chart: {
    type: "bar_chart",
    label: "Bar Chart",
    description: "Comparison bar chart",
    icon: "BarChart3",
    defaultTitle: "Comparison",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 12, h: 6 },
    defaultConfig: { metric: "device_count", group_by: "site", time_range: "24h" },
    component: () => import("./renderers/BarChartRenderer"),
  },
  gauge: {
    type: "gauge",
    label: "Gauge",
    description: "Circular gauge for percentage metrics",
    icon: "Gauge",
    defaultTitle: "Fleet Uptime",
    defaultSize: { w: 2, h: 2 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 4, h: 4 },
    defaultConfig: { metric: "uptime_pct", min: 0, max: 100 },
    component: () => import("./renderers/GaugeRenderer"),
  },
  table: {
    type: "table",
    label: "Device Table",
    description: "Tabular device list with status",
    icon: "Table2",
    defaultTitle: "Devices",
    defaultSize: { w: 6, h: 3 },
    minSize: { w: 3, h: 2 },
    maxSize: { w: 12, h: 8 },
    defaultConfig: { limit: 10, sort_by: "last_seen", filter_status: "" },
    component: () => import("./renderers/TableRenderer"),
  },
  alert_feed: {
    type: "alert_feed",
    label: "Alert Feed",
    description: "Live stream of open alerts",
    icon: "Bell",
    defaultTitle: "Active Alerts",
    defaultSize: { w: 4, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 8 },
    defaultConfig: { severity_filter: "", max_items: 20 },
    component: () => import("./renderers/AlertFeedRenderer"),
  },
  fleet_status: {
    type: "fleet_status",
    label: "Fleet Status",
    description: "Device status donut chart",
    icon: "PieChart",
    defaultTitle: "Fleet Status",
    defaultSize: { w: 3, h: 3 },
    minSize: { w: 2, h: 2 },
    maxSize: { w: 6, h: 6 },
    defaultConfig: {},
    component: () => import("./renderers/FleetStatusRenderer"),
  },
  device_count: {
    type: "device_count",
    label: "Device Count",
    description: "Total device count with online/offline breakdown",
    icon: "Cpu",
    defaultTitle: "Device Count",
    defaultSize: { w: 2, h: 1 },
    minSize: { w: 1, h: 1 },
    maxSize: { w: 4, h: 2 },
    defaultConfig: {},
    component: () => import("./renderers/DeviceCountRenderer"),
  },
  health_score: {
    type: "health_score",
    label: "Health Score",
    description: "Fleet health overview with status indicators",
    icon: "Activity",
    defaultTitle: "Fleet Health",
    defaultSize: { w: 6, h: 2 },
    minSize: { w: 4, h: 2 },
    maxSize: { w: 12, h: 4 },
    defaultConfig: {},
    component: () => import("./renderers/HealthScoreRenderer"),
  },
};

export function getWidgetDefinition(type: WidgetType): WidgetDefinition | undefined {
  return WIDGET_REGISTRY[type];
}

export function getAllWidgetTypes(): WidgetDefinition[] {
  return Object.values(WIDGET_REGISTRY);
}
```

---

## 5. Frontend: Widget Renderer Components

Create the following renderer files under `frontend/src/features/dashboard/widgets/renderers/`. Each is a thin wrapper around the existing widget logic, accepting `WidgetRendererProps`.

### `renderers/KpiTileRenderer.tsx`

Renders a single metric value. Reuses patterns from `FleetKpiStrip.tsx` but for a single configurable metric.
- Read `config.metric` (string: `"device_count"`, `"alert_count"`, `"uptime_pct"`, etc.)
- Use `useQuery` to fetch the relevant data from existing API endpoints (`/customer/fleet-summary`, `/customer/alerts?status=OPEN&limit=1`)
- Render: large number with label, minimal card (no CardHeader since the grid item title handles that)

### `renderers/LineChartRenderer.tsx`

Renders a time-series line chart using `EChartWrapper`.
- Read `config.metric`, `config.time_range`, `config.devices` (optional array)
- Fetch telemetry data from existing `/customer/devices/{deviceId}/telemetry?range=...` or aggregate endpoint
- Render: `<EChartWrapper>` with line series
- Fallback: "No data" message if no devices selected

### `renderers/BarChartRenderer.tsx`

Renders a bar chart using `EChartWrapper`.
- Read `config.metric`, `config.group_by`, `config.time_range`
- Fetch aggregated data from existing fleet summary
- Render: `<EChartWrapper>` with bar series

### `renderers/GaugeRenderer.tsx`

Renders a circular gauge using `EChartWrapper`.
- Read `config.metric`, `config.min`, `config.max`
- Reuse patterns from `MetricGauge.tsx` in `lib/charts/`
- Render: ECharts gauge series

### `renderers/TableRenderer.tsx`

Wraps the existing `DeviceTableWidget` logic.
- Read `config.limit`, `config.sort_by`, `config.filter_status`
- Use `useDevices` hook with config params
- Render: same table layout as `DeviceTableWidget` but without Card wrapper (grid item provides that)

### `renderers/AlertFeedRenderer.tsx`

Wraps the existing `AlertStreamWidget` logic.
- Read `config.severity_filter`, `config.max_items`
- Use `useAlerts` hook
- Render: alert list without Card wrapper

### `renderers/FleetStatusRenderer.tsx`

Wraps the existing `DeviceStatusWidget` logic (pie/donut chart).
- No additional config needed
- Render: ECharts donut chart without Card wrapper

### `renderers/DeviceCountRenderer.tsx`

Simple device count display.
- Use `useQuery` with `fetchFleetSummary`
- Render: large number with online/offline breakdown text

### `renderers/HealthScoreRenderer.tsx`

Wraps the existing `FleetHealthWidget` logic.
- No additional config needed
- Render: health status grid without Card wrapper

**Important pattern for all renderers**:
- Export as `default` (for lazy loading via `import()`)
- Accept `{ config, title, widgetId }` props matching `WidgetRendererProps`
- Do NOT wrap in `<Card>` -- the grid layout wrapper will handle the card container
- Use `<Skeleton>` for loading states
- Use appropriate `useQuery` hooks with `refetchInterval: 30000`

### Create renderer index: `renderers/index.ts`

```typescript
// Re-export all renderers (for non-lazy usage if needed)
export { default as KpiTileRenderer } from "./KpiTileRenderer";
export { default as LineChartRenderer } from "./LineChartRenderer";
export { default as BarChartRenderer } from "./BarChartRenderer";
export { default as GaugeRenderer } from "./GaugeRenderer";
export { default as TableRenderer } from "./TableRenderer";
export { default as AlertFeedRenderer } from "./AlertFeedRenderer";
export { default as FleetStatusRenderer } from "./FleetStatusRenderer";
export { default as DeviceCountRenderer } from "./DeviceCountRenderer";
export { default as HealthScoreRenderer } from "./HealthScoreRenderer";
```

---

## 6. Frontend: Widget Wrapper Component

Create file: `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

This wraps each widget in a card with title, optional config button, and error boundary.

```typescript
import { Suspense, lazy, useMemo, memo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { getWidgetDefinition } from "./widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";
import type { WidgetRendererProps } from "./widget-registry";
import type { ComponentType } from "react";

interface WidgetContainerProps {
  widget: DashboardWidget;
  isEditing?: boolean;
  onConfigure?: (widgetId: number) => void;
  onRemove?: (widgetId: number) => void;
}

function WidgetContainerInner({ widget, isEditing, onConfigure, onRemove }: WidgetContainerProps) {
  const definition = getWidgetDefinition(widget.widget_type);

  const LazyComponent = useMemo(() => {
    if (!definition) return null;
    return lazy(definition.component as () => Promise<{ default: ComponentType<WidgetRendererProps> }>);
  }, [definition]);

  if (!definition || !LazyComponent) {
    return (
      <Card className="h-full">
        <CardContent className="flex items-center justify-center h-full">
          <p className="text-sm text-muted-foreground">Unknown widget: {widget.widget_type}</p>
        </CardContent>
      </Card>
    );
  }

  const displayTitle = widget.title || definition.defaultTitle;

  return (
    <Card className="h-full flex flex-col overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between py-2 px-3 shrink-0">
        <CardTitle className="text-sm font-medium truncate">{displayTitle}</CardTitle>
        {isEditing && (
          <div className="flex gap-1 shrink-0">
            {onConfigure && (
              <button
                onClick={() => onConfigure(widget.id)}
                className="rounded p-1 text-xs text-muted-foreground hover:bg-accent"
                title="Configure"
              >
                &#9881;
              </button>
            )}
            {onRemove && (
              <button
                onClick={() => onRemove(widget.id)}
                className="rounded p-1 text-xs text-destructive hover:bg-destructive/10"
                title="Remove"
              >
                &times;
              </button>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-auto p-2">
        <WidgetErrorBoundary widgetName={displayTitle}>
          <Suspense fallback={<Skeleton className="h-full w-full min-h-[80px]" />}>
            <LazyComponent
              config={widget.config}
              title={displayTitle}
              widgetId={widget.id}
            />
          </Suspense>
        </WidgetErrorBoundary>
      </CardContent>
    </Card>
  );
}

export const WidgetContainer = memo(WidgetContainerInner);
```

---

## Verification

1. **Migration**:
   ```bash
   psql -U iot -d iotcloud -f db/migrations/081_dashboards.sql
   psql -U iot -d iotcloud -c "SELECT * FROM dashboards LIMIT 0;"
   psql -U iot -d iotcloud -c "SELECT * FROM dashboard_widgets LIMIT 0;"
   ```

2. **Backend**: Start the service and test CRUD:
   ```bash
   # Create a dashboard
   curl -X POST http://localhost:8080/customer/dashboards \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"name": "My Dashboard", "description": "Test"}'

   # List dashboards
   curl http://localhost:8080/customer/dashboards \
     -H "Authorization: Bearer $TOKEN"

   # Add a widget
   curl -X POST http://localhost:8080/customer/dashboards/1/widgets \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"widget_type": "fleet_status", "title": "Fleet Overview"}'

   # Get dashboard with widgets
   curl http://localhost:8080/customer/dashboards/1 \
     -H "Authorization: Bearer $TOKEN"

   # Delete widget
   curl -X DELETE http://localhost:8080/customer/dashboards/1/widgets/1 \
     -H "Authorization: Bearer $TOKEN"
   ```

3. **Frontend**: TypeScript check:
   ```bash
   cd frontend && npx tsc --noEmit
   ```

4. **Frontend**: Verify widget registry imports resolve:
   - Each renderer file should exist and default-export a component
   - `WidgetContainer` should render without errors in isolation
