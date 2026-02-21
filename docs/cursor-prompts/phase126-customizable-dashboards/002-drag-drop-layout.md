# Task 002: Drag-Drop Layout with react-grid-layout

**Commit message**: `feat(dashboards): add drag-drop layout with react-grid-layout`

---

## 1. Install Dependencies

```bash
cd frontend
npm install react-grid-layout @types/react-grid-layout
```

This adds `react-grid-layout` (provides `<ReactGridLayout>` and `<ResponsiveGridLayout>`) and its TypeScript types to `frontend/package.json`.

**Important**: react-grid-layout requires its CSS to be imported. Add the import in the component file or globally.

---

## 2. Import react-grid-layout CSS

Add to `frontend/src/app/globals.css` (or wherever global styles are loaded). If using Tailwind CSS 4 with `@import`, add near the top:

```css
@import "react-grid-layout/css/styles.css";
@import "react-resizable/css/styles.css";
```

Alternatively, import these in the `DashboardBuilder.tsx` component file directly:

```typescript
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";
```

---

## 3. Create DashboardBuilder Component

Create file: `frontend/src/features/dashboard/DashboardBuilder.tsx`

This is the core component that replaces the static grid with a drag-and-drop grid layout.

```typescript
import { useState, useCallback, useRef, useMemo } from "react";
import { Responsive, WidthProvider } from "react-grid-layout";
import type { Layout, Layouts } from "react-grid-layout";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Pencil, Lock, Plus } from "lucide-react";
import { WidgetContainer } from "./widgets/WidgetContainer";
import { AddWidgetDrawer } from "./AddWidgetDrawer";
import { WidgetConfigDialog } from "./WidgetConfigDialog";
import { batchUpdateLayout, removeWidget } from "@/services/api/dashboards";
import type { Dashboard, DashboardWidget, LayoutItem } from "@/services/api/dashboards";

import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const ResponsiveGridLayout = WidthProvider(Responsive);

interface DashboardBuilderProps {
  dashboard: Dashboard;
  canEdit: boolean; // true if user is owner or has edit permission
}

export function DashboardBuilder({ dashboard, canEdit }: DashboardBuilderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showAddWidget, setShowAddWidget] = useState(false);
  const [configuringWidgetId, setConfiguringWidgetId] = useState<number | null>(null);
  const queryClient = useQueryClient();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  // Build react-grid-layout items from widget positions
  const layoutItems: Layout[] = useMemo(
    () =>
      dashboard.widgets.map((w) => ({
        i: String(w.id),
        x: w.position?.x ?? 0,
        y: w.position?.y ?? 0,
        w: w.position?.w ?? 2,
        h: w.position?.h ?? 2,
        // Lock items when not editing
        static: !isEditing,
      })),
    [dashboard.widgets, isEditing]
  );

  // Mutation: batch layout save
  const layoutMutation = useMutation({
    mutationFn: (layout: LayoutItem[]) => batchUpdateLayout(dashboard.id, layout),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
    },
  });

  // Mutation: remove widget
  const removeMutation = useMutation({
    mutationFn: (widgetId: number) => removeWidget(dashboard.id, widgetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
    },
  });

  // Debounced layout save on drag/resize
  const handleLayoutChange = useCallback(
    (layout: Layout[]) => {
      if (!isEditing) return;

      // Clear previous debounce
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        const layoutData: LayoutItem[] = layout.map((item) => ({
          widget_id: Number(item.i),
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
        }));
        layoutMutation.mutate(layoutData);
      }, 500);
    },
    [isEditing, dashboard.id, layoutMutation]
  );

  const handleRemoveWidget = useCallback(
    (widgetId: number) => {
      if (confirm("Remove this widget from the dashboard?")) {
        removeMutation.mutate(widgetId);
      }
    },
    [removeMutation]
  );

  const handleConfigureWidget = useCallback((widgetId: number) => {
    setConfiguringWidgetId(widgetId);
  }, []);

  const configuringWidget = dashboard.widgets.find((w) => w.id === configuringWidgetId);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      {canEdit && (
        <div className="flex items-center gap-2">
          <Button
            variant={isEditing ? "default" : "outline"}
            size="sm"
            onClick={() => setIsEditing(!isEditing)}
          >
            {isEditing ? (
              <>
                <Lock className="mr-1 h-4 w-4" />
                Lock Layout
              </>
            ) : (
              <>
                <Pencil className="mr-1 h-4 w-4" />
                Edit Layout
              </>
            )}
          </Button>

          {isEditing && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddWidget(true)}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add Widget
            </Button>
          )}

          {layoutMutation.isPending && (
            <span className="text-xs text-muted-foreground animate-pulse">Saving...</span>
          )}
        </div>
      )}

      {/* Grid */}
      {dashboard.widgets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-muted-foreground mb-4">This dashboard has no widgets yet.</p>
          {canEdit && (
            <Button variant="outline" onClick={() => {
              setIsEditing(true);
              setShowAddWidget(true);
            }}>
              <Plus className="mr-1 h-4 w-4" />
              Add Your First Widget
            </Button>
          )}
        </div>
      ) : (
        <ResponsiveGridLayout
          className="layout"
          layouts={{ lg: layoutItems }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={100}
          isDraggable={isEditing}
          isResizable={isEditing}
          draggableHandle=".drag-handle"
          onLayoutChange={(layout) => handleLayoutChange(layout)}
          compactType="vertical"
          margin={[16, 16]}
        >
          {dashboard.widgets.map((widget) => (
            <div key={String(widget.id)} className="relative group">
              {isEditing && (
                <div className="drag-handle absolute top-0 left-0 right-0 h-8 cursor-grab active:cursor-grabbing z-10 flex items-center justify-center">
                  <div className="h-1 w-8 rounded-full bg-border opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              )}
              <WidgetContainer
                widget={widget}
                isEditing={isEditing}
                onConfigure={handleConfigureWidget}
                onRemove={handleRemoveWidget}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      )}

      {/* Add Widget Drawer */}
      <AddWidgetDrawer
        open={showAddWidget}
        onOpenChange={setShowAddWidget}
        dashboardId={dashboard.id}
      />

      {/* Widget Config Dialog */}
      {configuringWidget && (
        <WidgetConfigDialog
          open={configuringWidgetId !== null}
          onOpenChange={(open) => {
            if (!open) setConfiguringWidgetId(null);
          }}
          dashboardId={dashboard.id}
          widget={configuringWidget}
        />
      )}
    </div>
  );
}
```

---

## 4. Create AddWidgetDrawer Component

Create file: `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

A slide-out sheet listing all available widget types. Click one to open the config dialog, then adds the widget.

```typescript
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { getAllWidgetTypes, type WidgetDefinition } from "./widgets/widget-registry";
import { addWidget } from "@/services/api/dashboards";
import type { WidgetType } from "@/services/api/dashboards";
import {
  Hash, TrendingUp, BarChart3, Gauge, Table2,
  Bell, PieChart, Cpu, Activity,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const ICON_MAP: Record<string, LucideIcon> = {
  Hash,
  TrendingUp,
  BarChart3,
  Gauge,
  Table2,
  Bell,
  PieChart,
  Cpu,
  Activity,
};

interface AddWidgetDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
}

export function AddWidgetDrawer({ open, onOpenChange, dashboardId }: AddWidgetDrawerProps) {
  const queryClient = useQueryClient();
  const allWidgets = getAllWidgetTypes();

  const addMutation = useMutation({
    mutationFn: (def: WidgetDefinition) =>
      addWidget(dashboardId, {
        widget_type: def.type,
        title: def.defaultTitle,
        config: def.defaultConfig,
        position: { x: 0, y: Infinity, ...def.defaultSize }, // Place at bottom
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[360px] sm:w-[420px]">
        <SheetHeader>
          <SheetTitle>Add Widget</SheetTitle>
          <SheetDescription>
            Choose a widget type to add to your dashboard.
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-2">
          {allWidgets.map((def) => {
            const Icon = ICON_MAP[def.icon] || Activity;
            return (
              <button
                key={def.type}
                onClick={() => addMutation.mutate(def)}
                disabled={addMutation.isPending}
                className="w-full flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors disabled:opacity-50"
              >
                <div className="rounded-md bg-muted p-2 shrink-0">
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium">{def.label}</div>
                  <div className="text-xs text-muted-foreground">{def.description}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    Default size: {def.defaultSize.w}x{def.defaultSize.h}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

---

## 5. Create WidgetConfigDialog Component

Create file: `frontend/src/features/dashboard/WidgetConfigDialog.tsx`

A dialog for configuring a widget's title and type-specific settings.

```typescript
import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { updateWidget } from "@/services/api/dashboards";
import { getWidgetDefinition } from "./widgets/widget-registry";
import type { DashboardWidget } from "@/services/api/dashboards";

interface WidgetConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
  widget: DashboardWidget;
}

const TIME_RANGES = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const METRICS = [
  { value: "temperature", label: "Temperature" },
  { value: "humidity", label: "Humidity" },
  { value: "pressure", label: "Pressure" },
  { value: "vibration", label: "Vibration" },
  { value: "power", label: "Power" },
  { value: "flow", label: "Flow" },
  { value: "level", label: "Level" },
  { value: "device_count", label: "Device Count" },
  { value: "alert_count", label: "Alert Count" },
  { value: "uptime_pct", label: "Uptime %" },
];

export function WidgetConfigDialog({
  open,
  onOpenChange,
  dashboardId,
  widget,
}: WidgetConfigDialogProps) {
  const [title, setTitle] = useState(widget.title);
  const [config, setConfig] = useState<Record<string, unknown>>(widget.config);
  const queryClient = useQueryClient();
  const definition = getWidgetDefinition(widget.widget_type);

  useEffect(() => {
    setTitle(widget.title);
    setConfig(widget.config);
  }, [widget]);

  const mutation = useMutation({
    mutationFn: () =>
      updateWidget(dashboardId, widget.id, { title, config }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
      onOpenChange(false);
    },
  });

  function updateConfig(key: string, value: unknown) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  // Render type-specific config fields
  function renderConfigFields() {
    const widgetType = widget.widget_type;

    if (widgetType === "kpi_tile" || widgetType === "line_chart" || widgetType === "bar_chart") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || ""}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Time Range</Label>
            <Select
              value={(config.time_range as string) || "24h"}
              onValueChange={(v) => updateConfig("time_range", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select range" />
              </SelectTrigger>
              <SelectContent>
                {TIME_RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      );
    }

    if (widgetType === "gauge") {
      return (
        <>
          <div className="space-y-2">
            <Label>Metric</Label>
            <Select
              value={(config.metric as string) || "uptime_pct"}
              onValueChange={(v) => updateConfig("metric", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select metric" />
              </SelectTrigger>
              <SelectContent>
                {METRICS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Min</Label>
              <Input
                type="number"
                value={(config.min as number) ?? 0}
                onChange={(e) => updateConfig("min", Number(e.target.value))}
              />
            </div>
            <div className="space-y-2">
              <Label>Max</Label>
              <Input
                type="number"
                value={(config.max as number) ?? 100}
                onChange={(e) => updateConfig("max", Number(e.target.value))}
              />
            </div>
          </div>
        </>
      );
    }

    if (widgetType === "table") {
      return (
        <div className="space-y-2">
          <Label>Rows to show</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.limit as number) ?? 10}
            onChange={(e) => updateConfig("limit", Number(e.target.value))}
          />
        </div>
      );
    }

    if (widgetType === "alert_feed") {
      return (
        <div className="space-y-2">
          <Label>Max items</Label>
          <Input
            type="number"
            min={5}
            max={50}
            value={(config.max_items as number) ?? 20}
            onChange={(e) => updateConfig("max_items", Number(e.target.value))}
          />
        </div>
      );
    }

    // fleet_status, device_count, health_score have no extra config
    return (
      <p className="text-sm text-muted-foreground">
        This widget type has no additional configuration.
      </p>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>
            Configure {definition?.label || "Widget"}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Widget title"
              maxLength={100}
            />
          </div>
          {renderConfigFields()}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 6. Update DashboardPage to Use DashboardBuilder

Edit file: `frontend/src/features/dashboard/DashboardPage.tsx`

Replace the current hardcoded layout with a component that:
1. Fetches the user's dashboards via `fetchDashboards()`
2. If user has dashboards, loads the default (or first) dashboard via `fetchDashboard(id)`
3. Renders `<DashboardBuilder>` with the loaded dashboard
4. Falls back to the old layout if no dashboards exist yet (this fallback will be replaced in task 003 with auto-created default dashboards)

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/services/auth/AuthProvider";
import { fetchDashboards, fetchDashboard } from "@/services/api/dashboards";
import { DashboardBuilder } from "./DashboardBuilder";
// Keep old imports for fallback
import { WidgetErrorBoundary } from "@/components/shared/WidgetErrorBoundary";
import { AlertTrendWidget, DeviceStatusWidget } from "./widgets";
import { UptimeSummaryWidget } from "@/features/devices/UptimeSummaryWidget";
import FleetKpiStrip from "./FleetKpiStrip";

function LegacyDashboard() {
  // ... move the existing hardcoded layout here as a fallback
  // (ActiveAlertsPanel, RecentlyActiveDevicesPanel, etc.)
  // This is temporary -- task 003 will auto-create a default dashboard
  return (
    <div className="space-y-6">
      <WidgetErrorBoundary widgetName="Fleet KPI Strip">
        <FleetKpiStrip />
      </WidgetErrorBoundary>
      <WidgetErrorBoundary widgetName="Fleet Uptime">
        <UptimeSummaryWidget />
      </WidgetErrorBoundary>
      <div className="grid gap-6 lg:grid-cols-2">
        <WidgetErrorBoundary widgetName="Device Status">
          <DeviceStatusWidget />
        </WidgetErrorBoundary>
        <WidgetErrorBoundary widgetName="Alert Trend">
          <AlertTrendWidget />
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const subtitle = user?.tenantId ? `Tenant: ${user.tenantId}` : "Real-time operational view";

  // Fetch all dashboards for the user
  const { data: dashboardList, isLoading: listLoading } = useQuery({
    queryKey: ["dashboards"],
    queryFn: fetchDashboards,
  });

  // Find the default dashboard, or the first one
  const defaultDashboard = dashboardList?.dashboards?.find((d) => d.is_default)
    || dashboardList?.dashboards?.[0];

  // Fetch the selected dashboard with widgets
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const activeDashboardId = selectedId ?? defaultDashboard?.id ?? null;

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard", activeDashboardId],
    queryFn: () => fetchDashboard(activeDashboardId!),
    enabled: activeDashboardId !== null,
  });

  if (listLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description={subtitle} />
        <Skeleton className="h-[400px]" />
      </div>
    );
  }

  // No dashboards yet -> show legacy fallback
  if (!dashboardList?.dashboards?.length) {
    return (
      <div className="space-y-6">
        <PageHeader title="Fleet Overview" description={subtitle} />
        <LegacyDashboard />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={dashboard?.name || "Dashboard"}
        description={dashboard?.description || subtitle}
      />

      {dashLoading ? (
        <Skeleton className="h-[400px]" />
      ) : dashboard ? (
        <DashboardBuilder
          dashboard={dashboard}
          canEdit={dashboard.is_owner}
        />
      ) : (
        <LegacyDashboard />
      )}
    </div>
  );
}
```

**Important implementation notes**:
- Move the inline `ActiveAlertsPanel` and `RecentlyActiveDevicesPanel` functions from the old `DashboardPage.tsx` into the `LegacyDashboard` component or keep them as local functions.
- The `selectedId` state and `setSelectedId` will be wired up to a dashboard selector dropdown in task 003.
- Keep the `relativeTime` and `statusDot` helper functions -- they may still be used by the legacy fallback.

---

## 7. react-grid-layout Custom Styles

Add to `frontend/src/app/globals.css` (or a new file `frontend/src/features/dashboard/dashboard-grid.css`):

```css
/* Dashboard grid customizations */
.react-grid-layout {
  position: relative;
}

.react-grid-item {
  transition: all 200ms ease;
  transition-property: left, top, width, height;
}

.react-grid-item.cssTransforms {
  transition-property: transform, width, height;
}

.react-grid-item.resizing {
  z-index: 1;
  will-change: width, height;
  opacity: 0.9;
}

.react-grid-item.react-draggable-dragging {
  transition: none;
  z-index: 3;
  will-change: transform;
  opacity: 0.8;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.react-grid-item > .react-resizable-handle {
  position: absolute;
  width: 20px;
  height: 20px;
}

.react-grid-item > .react-resizable-handle::after {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 5px;
  height: 5px;
  border-right: 2px solid rgba(0, 0, 0, 0.2);
  border-bottom: 2px solid rgba(0, 0, 0, 0.2);
}

/* Dark mode resize handle */
.dark .react-grid-item > .react-resizable-handle::after {
  border-right-color: rgba(255, 255, 255, 0.2);
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

/* Placeholder styling for drop target */
.react-grid-item.react-grid-placeholder {
  background: hsl(var(--primary) / 0.1);
  border: 2px dashed hsl(var(--primary) / 0.3);
  border-radius: 0.5rem;
  opacity: 1;
}
```

---

## Verification

1. **Dependency installed**:
   ```bash
   cd frontend && npm ls react-grid-layout
   ```
   Should show `react-grid-layout@X.Y.Z`

2. **TypeScript check**:
   ```bash
   cd frontend && npx tsc --noEmit
   ```

3. **Manual browser test**:
   - Navigate to `/app/dashboard`
   - If you have dashboards (from task 001 API calls), the `DashboardBuilder` renders
   - Click "Edit Layout" -- drag handles appear
   - Drag a widget to a new position -- layout saves after 500ms debounce
   - Click "Add Widget" -- sheet slides out with widget type list
   - Click a widget type -- it appears at the bottom of the grid
   - Click the gear icon on a widget -- config dialog opens
   - Click the X icon on a widget -- widget is removed after confirm
   - Click "Lock Layout" -- widgets become static
   - Reload page -- layout persists (positions saved to DB)

4. **API verification**:
   ```bash
   # After dragging widgets, check the layout was saved:
   curl http://localhost:8080/customer/dashboards/1 \
     -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
   ```
   Widget positions should reflect the drag-drop changes.
