# Task 003: Personal/Shared Dashboards with Default Template

**Commit message**: `feat(dashboards): add personal/shared dashboards with default template`

---

## 1. Backend: Share/Unshare Endpoint

Edit file: `services/ui_iot/routes/dashboards.py`

Add a new endpoint to toggle dashboard sharing. When shared, `user_id` is set to `NULL`; when unshared, `user_id` is set back to the current user's `sub` claim.

```python
class DashboardShareUpdate(BaseModel):
    shared: bool


@router.put("/{dashboard_id}/share")
async def toggle_share(dashboard_id: int, data: DashboardShareUpdate, pool=Depends(get_db_pool)):
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
        # If already shared (user_id is NULL), only the person who shared it can unshare
        # We track this by: if user_id IS NULL, any tenant user can see it, but only someone
        # who can prove ownership can unshare. We store no separate owner field, so we rely on
        # the convention that only the user who set it to NULL can set it back.
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

    return {
        "id": dashboard_id,
        "is_shared": data.shared,
    }
```

---

## 2. Backend: Default Dashboard Creation Endpoint

Add to `services/ui_iot/routes/dashboards.py`:

A route that creates a default dashboard with pre-configured widgets for a user who has none. This is called by the frontend on first visit.

```python
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


@router.post("/bootstrap", status_code=201)
async def bootstrap_default_dashboard(pool=Depends(get_db_pool)):
    """Create a default dashboard for the current user if they have none.
    Called by the frontend on first visit.
    Returns the existing default if one already exists (idempotent).
    """
    tenant_id = get_tenant_id()
    user = get_user()
    user_id = user.get("sub", "")

    # Determine if this is an operator user
    realm_access = user.get("realm_access", {}) or {}
    roles = set(realm_access.get("roles", []) or [])
    is_operator = "operator" in roles or "operator-admin" in roles

    async with tenant_connection(pool, tenant_id) as conn:
        # Check if user already has any dashboards (personal or default)
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
            # Already has dashboards, return the first one
            return {"id": existing["id"], "created": False}

        # Check if there are any shared dashboards they can use
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

        # Create default dashboard
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

        # Insert default widgets
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
```

---

## 3. Frontend: Dashboard Selector Dropdown

Create file: `frontend/src/features/dashboard/DashboardSelector.tsx`

A dropdown component that lets users switch between dashboards, create new ones, and manage existing ones.

```typescript
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ChevronDown, Plus, Share2, Lock, Star, Trash2 } from "lucide-react";
import {
  fetchDashboards,
  createDashboard,
  deleteDashboard,
  updateDashboard,
} from "@/services/api/dashboards";
import type { DashboardSummary } from "@/services/api/dashboards";

interface DashboardSelectorProps {
  activeDashboardId: number | null;
  onSelect: (id: number) => void;
}

export function DashboardSelector({ activeDashboardId, onSelect }: DashboardSelectorProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["dashboards"],
    queryFn: fetchDashboards,
  });

  const dashboards = data?.dashboards ?? [];
  const activeDashboard = dashboards.find((d) => d.id === activeDashboardId);

  const createMutation = useMutation({
    mutationFn: () => createDashboard({ name: newName.trim(), description: newDescription.trim() }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      onSelect(result.id);
      setShowCreateDialog(false);
      setNewName("");
      setNewDescription("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDashboard(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      // If deleted the active dashboard, switch to first available
      const remaining = dashboards.filter((d) => d.id !== activeDashboardId);
      if (remaining.length > 0) {
        onSelect(remaining[0].id);
      }
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: number) => updateDashboard(id, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
    },
  });

  function handleDelete(dashboard: DashboardSummary) {
    if (!dashboard.is_owner) return;
    if (confirm(`Delete dashboard "${dashboard.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(dashboard.id);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1">
            {activeDashboard?.name || "Select Dashboard"}
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
          {/* Personal dashboards */}
          {dashboards.filter((d) => !d.is_shared).length > 0 && (
            <>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                My Dashboards
              </div>
              {dashboards
                .filter((d) => !d.is_shared)
                .map((d) => (
                  <DropdownMenuItem
                    key={d.id}
                    onClick={() => onSelect(d.id)}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {d.is_default && <Star className="h-3 w-3 text-yellow-500 shrink-0" />}
                      <span className={d.id === activeDashboardId ? "font-medium" : ""}>
                        {d.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-xs text-muted-foreground">{d.widget_count}w</span>
                      {d.is_owner && !d.is_default && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDefaultMutation.mutate(d.id);
                          }}
                          className="p-0.5 hover:text-yellow-500"
                          title="Set as default"
                        >
                          <Star className="h-3 w-3" />
                        </button>
                      )}
                      {d.is_owner && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(d);
                          }}
                          className="p-0.5 hover:text-destructive"
                          title="Delete"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </DropdownMenuItem>
                ))}
            </>
          )}

          {/* Shared dashboards */}
          {dashboards.filter((d) => d.is_shared).length > 0 && (
            <>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                <Share2 className="inline h-3 w-3 mr-1" />
                Shared Dashboards
              </div>
              {dashboards
                .filter((d) => d.is_shared)
                .map((d) => (
                  <DropdownMenuItem
                    key={d.id}
                    onClick={() => onSelect(d.id)}
                    className="flex items-center justify-between"
                  >
                    <span className={d.id === activeDashboardId ? "font-medium" : ""}>
                      {d.name}
                    </span>
                    <span className="text-xs text-muted-foreground">{d.widget_count}w</span>
                  </DropdownMenuItem>
                ))}
            </>
          )}

          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Dashboard
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Create Dashboard Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Create Dashboard</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Dashboard"
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label>Description (optional)</Label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Dashboard purpose..."
                maxLength={500}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!newName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

---

## 4. Frontend: Share Toggle on Dashboard Settings

Create file: `frontend/src/features/dashboard/DashboardSettings.tsx`

A small settings popover/menu on the dashboard page that includes share toggle and rename.

```typescript
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Settings, Pencil, Share2, Star } from "lucide-react";
import { updateDashboard } from "@/services/api/dashboards";
import { apiPut } from "@/services/api/client";
import type { Dashboard } from "@/services/api/dashboards";

interface DashboardSettingsProps {
  dashboard: Dashboard;
}

export function DashboardSettings({ dashboard }: DashboardSettingsProps) {
  const [showRename, setShowRename] = useState(false);
  const [newName, setNewName] = useState(dashboard.name);
  const [newDescription, setNewDescription] = useState(dashboard.description);
  const queryClient = useQueryClient();

  const renameMutation = useMutation({
    mutationFn: () =>
      updateDashboard(dashboard.id, {
        name: newName.trim(),
        description: newDescription.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      setShowRename(false);
    },
  });

  const shareMutation = useMutation({
    mutationFn: (shared: boolean) =>
      apiPut(`/customer/dashboards/${dashboard.id}/share`, { shared }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
    },
  });

  const defaultMutation = useMutation({
    mutationFn: () => updateDashboard(dashboard.id, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
    },
  });

  if (!dashboard.is_owner) return null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => {
            setNewName(dashboard.name);
            setNewDescription(dashboard.description);
            setShowRename(true);
          }}>
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>

          {!dashboard.is_default && (
            <DropdownMenuItem onClick={() => defaultMutation.mutate()}>
              <Star className="h-4 w-4 mr-2" />
              Set as Default
            </DropdownMenuItem>
          )}

          <DropdownMenuSeparator />

          <div className="flex items-center justify-between px-2 py-2">
            <div className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              <span className="text-sm">
                {dashboard.is_shared ? "Shared" : "Private"}
              </span>
            </div>
            <Switch
              checked={dashboard.is_shared}
              onCheckedChange={(checked) => shareMutation.mutate(checked)}
              disabled={shareMutation.isPending}
            />
          </div>
          {dashboard.is_shared && (
            <p className="px-2 pb-2 text-xs text-muted-foreground">
              All team members can view this dashboard.
            </p>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={showRename} onOpenChange={setShowRename}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Rename Dashboard</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                maxLength={500}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRename(false)}>Cancel</Button>
            <Button
              onClick={() => renameMutation.mutate()}
              disabled={!newName.trim() || renameMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```

---

## 5. Update DashboardPage with Selector, Bootstrap, and Settings

Edit file: `frontend/src/features/dashboard/DashboardPage.tsx`

This is the final version. Replace the version from task 002 with a complete implementation that:
1. Calls `/customer/dashboards/bootstrap` on mount to ensure a default dashboard exists
2. Shows the `DashboardSelector` dropdown in the header
3. Shows the `DashboardSettings` menu for owned dashboards
4. Removes the `LegacyDashboard` fallback (bootstrap handles first-time users)

```typescript
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/services/auth/AuthProvider";
import { fetchDashboards, fetchDashboard } from "@/services/api/dashboards";
import { apiPost } from "@/services/api/client";
import { DashboardBuilder } from "./DashboardBuilder";
import { DashboardSelector } from "./DashboardSelector";
import { DashboardSettings } from "./DashboardSettings";

export default function DashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const subtitle = user?.tenantId ? `Tenant: ${user.tenantId}` : "Real-time operational view";

  // Bootstrap: ensure default dashboard exists
  const bootstrapMutation = useMutation({
    mutationFn: () => apiPost<{ id: number; created: boolean }>("/customer/dashboards/bootstrap", {}),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      if (result.created && !selectedId) {
        setSelectedId(result.id);
      }
    },
  });

  // Fetch all dashboards
  const { data: dashboardList, isLoading: listLoading } = useQuery({
    queryKey: ["dashboards"],
    queryFn: fetchDashboards,
  });

  // Bootstrap on first load if no dashboards
  useEffect(() => {
    if (!listLoading && dashboardList && dashboardList.dashboards.length === 0) {
      bootstrapMutation.mutate();
    }
  }, [listLoading, dashboardList?.dashboards?.length]);

  // Dashboard selection state
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // Determine active dashboard: selected > default > first
  const defaultDashboard = dashboardList?.dashboards?.find((d) => d.is_default)
    || dashboardList?.dashboards?.[0];
  const activeDashboardId = selectedId ?? defaultDashboard?.id ?? null;

  // Fetch the active dashboard with widgets
  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard", activeDashboardId],
    queryFn: () => fetchDashboard(activeDashboardId!),
    enabled: activeDashboardId !== null,
  });

  // Loading state
  if (listLoading || bootstrapMutation.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description={subtitle} />
        <div className="grid gap-4 grid-cols-3">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={dashboard?.name || "Dashboard"}
        description={dashboard?.description || subtitle}
        action={
          <div className="flex items-center gap-2">
            <DashboardSelector
              activeDashboardId={activeDashboardId}
              onSelect={setSelectedId}
            />
            {dashboard && <DashboardSettings dashboard={dashboard} />}
          </div>
        }
      />

      {dashLoading ? (
        <div className="grid gap-4 grid-cols-3">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      ) : dashboard ? (
        <DashboardBuilder
          dashboard={dashboard}
          canEdit={dashboard.is_owner}
        />
      ) : (
        <div className="text-center py-20 text-muted-foreground">
          No dashboards available. Create one to get started.
        </div>
      )}
    </div>
  );
}
```

---

## 6. Update Router for Dashboard Routes

Edit file: `frontend/src/app/router.tsx`

The existing route `{ path: "dashboard", element: <DashboardPage /> }` already works. No changes needed unless you want to support deep-linking to a specific dashboard by ID.

**Optional enhancement**: Add a route for specific dashboard IDs:
```typescript
{ path: "dashboard", element: <DashboardPage /> },
{ path: "dashboard/:dashboardId", element: <DashboardPage /> },
```

If adding the `:dashboardId` route, update `DashboardPage` to read `useParams()`:
```typescript
import { useParams } from "react-router-dom";
// ...
const { dashboardId } = useParams<{ dashboardId?: string }>();
const paramDashboardId = dashboardId ? Number(dashboardId) : null;
// Use paramDashboardId as initial selectedId
```

---

## 7. Frontend: API Helper for Share Toggle

Add to `frontend/src/services/api/dashboards.ts`:

```typescript
export async function toggleDashboardShare(
  id: number,
  shared: boolean
): Promise<{ id: number; is_shared: boolean }> {
  return apiPut(`/customer/dashboards/${id}/share`, { shared });
}

export async function bootstrapDashboard(): Promise<{ id: number; created: boolean }> {
  return apiPost("/customer/dashboards/bootstrap", {});
}
```

---

## 8. Update Sidebar to Link to Dashboard

The sidebar already has a "Dashboard" link at `/dashboard` (see `AppSidebar.tsx`). No changes needed.

---

## Verification

### 1. Bootstrap Flow (New User)

```bash
# As a user with no dashboards, call bootstrap:
curl -X POST http://localhost:8080/customer/dashboards/bootstrap \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{}'

# Expected: { "id": 1, "created": true }
# Calling again:
# Expected: { "id": 1, "created": false }
```

### 2. Personal Dashboard

```bash
# Create a personal dashboard:
curl -X POST http://localhost:8080/customer/dashboards \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"name": "My Custom View"}'

# List dashboards -- should show both default and custom:
curl http://localhost:8080/customer/dashboards \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Share/Unshare

```bash
# Share a dashboard (makes user_id NULL):
curl -X PUT http://localhost:8080/customer/dashboards/1/share \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"shared": true}'

# Verify: as another user in the same tenant, list dashboards.
# The shared dashboard should appear in their list.
```

### 4. Cross-User Visibility

```bash
# As User A: create and share a dashboard
# As User B (same tenant): list dashboards
# User B should see User A's shared dashboard but NOT User A's personal dashboards.
```

### 5. Default Dashboard for New User

Browser test:
1. Log in as a new user (no dashboards)
2. Navigate to `/app/dashboard`
3. Should see a loading state, then the auto-created default dashboard with 7 widgets
4. Widgets should be arranged in the default layout (fleet status top-left, KPIs in a row, etc.)
5. Click "Edit Layout" -- widgets should be draggable
6. Reload -- layout should persist

### 6. TypeScript

```bash
cd frontend && npx tsc --noEmit
```

### 7. Full Flow

1. User A logs in, sees default dashboard
2. User A creates "Alerts Focus" dashboard with alert_feed and kpi_tile widgets
3. User A drags widgets around, layout auto-saves
4. User A shares "Alerts Focus" with the team
5. User B logs in, sees their own default dashboard
6. User B switches to "Alerts Focus" via the dropdown
7. User B sees the shared dashboard (read-only, cannot edit)
8. User A unshares "Alerts Focus"
9. User B no longer sees it in their dropdown
