# Phase 148b — Auto-Open Config Dialog on Widget Add

## Problem

When a user adds a widget to the dashboard, the widget appears with default config (e.g., "No devices selected" for chart widgets). There is NO automatic config dialog, NO button inside the widget, and NO hint about how to configure it. The tiny ⚙ gear icon is easy to miss. Every professional dashboard (Grafana, Datadog, AWS CloudWatch) auto-opens configuration immediately after adding a widget. Ours doesn't.

## Fix Overview

Two changes:
1. **Auto-open the config dialog** when a new widget is added (primary fix)
2. **Show a "Configure" button** inside widgets that have empty/unconfigured state (fallback)

---

## Task 1: Auto-open config dialog after adding a widget

### Step 1: Add onWidgetAdded prop to AddWidgetDrawer

**File:** `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

Add an `onWidgetAdded` callback prop:

```tsx
interface AddWidgetDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dashboardId: number;
  onWidgetAdded?: (widgetId: number) => void;  // NEW
}

export function AddWidgetDrawer({ open, onOpenChange, dashboardId, onWidgetAdded }: AddWidgetDrawerProps) {
```

Update the `addMutation.onSuccess` to call the callback with the new widget's ID. The `addWidget` API returns `DashboardWidget` which has an `id` field:

```tsx
const addMutation = useMutation({
  mutationFn: (def: WidgetDefinition) =>
    addWidget(dashboardId, {
      widget_type: def.type,
      title: def.defaultTitle,
      config: def.defaultConfig,
      position: { x: 0, y: 9999, ...def.defaultSize },
    }),
  onSuccess: (newWidget) => {
    queryClient.invalidateQueries({ queryKey: ["dashboard", dashboardId] });
    onOpenChange(false);
    toast.success("Widget added");
    onWidgetAdded?.(newWidget.id);  // NEW — auto-open config
  },
  onError: (err: Error) => {
    toast.error(getErrorMessage(err) || "Failed to add widget");
  },
});
```

**Note:** The `onSuccess` callback receives the return value of `mutationFn` as its first argument. Since `addWidget()` returns `Promise<DashboardWidget>`, `newWidget` will be the full `DashboardWidget` object with `.id`.

### Step 2: Wire onWidgetAdded in DashboardBuilder

**File:** `frontend/src/features/dashboard/DashboardBuilder.tsx`

Pass `handleConfigureWidget` as the `onWidgetAdded` prop to AddWidgetDrawer:

Find:
```tsx
<AddWidgetDrawer
  open={showAddWidget}
  onOpenChange={onShowAddWidgetChange}
  dashboardId={dashboard.id}
/>
```

Replace with:
```tsx
<AddWidgetDrawer
  open={showAddWidget}
  onOpenChange={onShowAddWidgetChange}
  dashboardId={dashboard.id}
  onWidgetAdded={handleConfigureWidget}
/>
```

**How this works:** When the user adds a widget:
1. `addWidget` API call succeeds → returns new widget with ID
2. `onSuccess` fires → invalidates dashboard query, closes drawer, calls `onWidgetAdded(newWidget.id)`
3. `handleConfigureWidget` sets `configuringWidgetId = newWidget.id`
4. React Query refetches the dashboard → `dashboard.widgets` now includes the new widget
5. `configuringWidget = dashboard.widgets.find(w => w.id === configuringWidgetId)` becomes truthy
6. `WidgetConfigDialog` renders with the new widget → user sees config immediately

**Race condition note:** There's a brief moment between setting `configuringWidgetId` and the dashboard refetch completing where `configuringWidget` is `undefined`. The existing guard `{configuringWidget && ...}` handles this — the dialog simply renders once the data arrives. This is the correct behavior.

---

## Task 2: Add "Configure" button inside unconfigured widgets

### Step 1: Update WidgetContainer to detect unconfigured state and provide configure action

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

The renderers (LineChartRenderer, AreaChartRenderer) show "No devices selected" when `config.devices` is empty. But there's no way to act on that from the widget itself. Add a configure CTA inside the widget when it's unconfigured.

Add a helper function inside WidgetContainerInner to detect if the widget needs configuration:

```tsx
const needsConfiguration = useMemo(() => {
  const type = widget.widget_type;
  const cfg = effectiveConfig;

  // Chart widgets need a device selected
  if (["line_chart", "bar_chart", "area_chart"].includes(type)) {
    const devices = cfg.devices;
    return !Array.isArray(devices) || devices.length === 0;
  }

  return false;
}, [widget.widget_type, effectiveConfig]);
```

Then in the render, wrap the Suspense block with an unconfigured overlay. Add this BEFORE the existing `<WidgetErrorBoundary>` block inside `<CardContent>`:

```tsx
<CardContent className="flex-1 overflow-hidden min-h-0 p-1.5">
  {needsConfiguration && onConfigure ? (
    <div className="h-full flex flex-col items-center justify-center gap-2 text-center">
      <p className="text-sm text-muted-foreground">
        This widget needs to be configured.
      </p>
      <button
        onClick={() => onConfigure(widget.id)}
        className="text-sm text-primary underline underline-offset-2 hover:text-primary/80"
      >
        Configure widget
      </button>
    </div>
  ) : (
    <WidgetErrorBoundary widgetName={displayTitle}>
      <Suspense fallback={<Skeleton className="h-full w-full min-h-[80px]" />}>
        <LazyComponent
          config={effectiveConfig}
          title={displayTitle}
          widgetId={widget.id}
        />
      </Suspense>
    </WidgetErrorBoundary>
  )}
</CardContent>
```

**Important:** This shows "Configure widget" link even when NOT in edit mode, because the user needs to be able to configure a newly added widget. The `onConfigure` callback is always passed to WidgetContainer from DashboardBuilder. Check that DashboardBuilder passes `onConfigure` unconditionally (not only when `isEditing`).

Looking at DashboardBuilder line 202-207:
```tsx
<WidgetContainer
  widget={widget}
  isEditing={isEditing}
  onConfigure={handleConfigureWidget}
  onRemove={handleRemoveWidget}
/>
```

`onConfigure` is already passed unconditionally. But the WidgetContainer currently only shows the gear icon when `isEditing` is true. The new "Configure widget" link inside CardContent will work regardless of edit mode — it calls `onConfigure` directly. This is the correct behavior: users should always be able to configure unconfigured widgets.

### Step 2: Add useMemo import if not present

Make sure `useMemo` is in the import list of WidgetContainer.tsx. Looking at the current file, line 1 already has:
```tsx
import { Suspense, lazy, useMemo, memo } from "react";
```
So no change needed.

---

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Verify

1. Add a "Metric Trend" (line chart) widget → **config dialog opens automatically**
2. Device selector is visible → select a device → save → chart populates
3. Add a "Gauge" widget → config dialog opens automatically → configure metric and style
4. Add a "Pie / Donut" widget → config dialog opens automatically → configure data source
5. Close config dialog without selecting a device on a line chart → widget shows "This widget needs to be configured" with a clickable "Configure widget" link
6. Click "Configure widget" link → config dialog opens (even when NOT in edit mode)
7. Existing widgets that are already configured show their normal content (no "Configure widget" overlay)
