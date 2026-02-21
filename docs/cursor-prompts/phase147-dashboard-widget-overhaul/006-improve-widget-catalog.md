# Task 6: Improve Widget Catalog

## Context

The AddWidgetDrawer shows a flat list of 9 widgets with short descriptions. Users need categories, better descriptions, and visual organization to understand what's available.

## Step 1: Add categories to widget definitions

**File:** `frontend/src/features/dashboard/widgets/widget-registry.ts`

Add a `category` field to `WidgetDefinition`:

```typescript
export interface WidgetDefinition {
  type: WidgetType;
  label: string;
  description: string;
  category: "charts" | "metrics" | "data" | "fleet";
  icon: string;
  defaultTitle: string;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  maxSize: { w: number; h: number };
  defaultConfig: Record<string, unknown>;
  component: () => Promise<{ default: ComponentType<WidgetRendererProps> }>;
}
```

Update each widget entry with its category and improve descriptions:

| Widget | Category | Improved Description |
|--------|----------|---------------------|
| `kpi_tile` | `metrics` | `"Single metric value with configurable data source. Ideal for at-a-glance monitoring."` |
| `line_chart` | `charts` | `"Time-series trend line. Track metric changes over configurable time ranges."` |
| `bar_chart` | `charts` | `"Grouped bar comparison. Compare metric values across categories or time periods."` |
| `gauge` | `metrics` | `"Radial gauge dial showing a value within min/max bounds. Great for utilization metrics."` |
| `table` | `data` | `"Sortable device list with status, battery level, and last-seen timestamp."` |
| `alert_feed` | `data` | `"Live alert stream from connected devices. Filters by severity level."` |
| `fleet_status` | `fleet` | `"Donut chart showing online vs. stale device distribution across your fleet."` |
| `device_count` | `fleet` | `"Compact device counter with online/offline breakdown."` |
| `health_score` | `fleet` | `"Overall fleet health percentage based on device connectivity and alert status."` |

Add a helper to get widgets grouped by category:

```typescript
export function getWidgetsByCategory(): Array<{
  category: string;
  label: string;
  widgets: WidgetDefinition[];
}> {
  const categories = [
    { category: "charts", label: "Charts" },
    { category: "metrics", label: "Metrics" },
    { category: "data", label: "Data" },
    { category: "fleet", label: "Fleet Overview" },
  ];

  return categories.map((cat) => ({
    ...cat,
    widgets: getAllWidgetTypes().filter((w) => w.category === cat.category),
  }));
}
```

## Step 2: Update AddWidgetDrawer with categorized layout

**File:** `frontend/src/features/dashboard/AddWidgetDrawer.tsx`

Replace the flat list with categorized sections:

```tsx
import { getWidgetsByCategory } from "./widgets/widget-registry";

// In the component:
const categorizedWidgets = getWidgetsByCategory();

// In the render:
<div className="space-y-4 overflow-y-auto flex-1">
  {categorizedWidgets.map((group) => (
    <div key={group.category}>
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 px-1">
        {group.label}
      </h4>
      <div className="space-y-2">
        {group.widgets.map((def) => {
          const Icon = ICON_MAP[def.icon] ?? Hash;
          return (
            <button
              key={def.type}
              disabled={addMutation.isPending}
              onClick={() => addMutation.mutate(def)}
              className="w-full flex items-start gap-3 rounded-lg border border-border p-3 text-left hover:bg-accent transition-colors disabled:opacity-50"
            >
              <div className="rounded-md bg-muted p-2">
                <Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">{def.label}</div>
                <div className="text-xs text-muted-foreground line-clamp-2">{def.description}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Default: {def.defaultSize.w}×{def.defaultSize.h}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  ))}
</div>
```

## Step 3: Improve drawer header

Add a brief instruction at the top of the drawer:

```tsx
<SheetHeader>
  <SheetTitle>Add Widget</SheetTitle>
  <p className="text-sm text-muted-foreground">
    Select a widget to add to your dashboard. You can configure it after adding.
  </p>
</SheetHeader>
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```

After this task: open the Add Widget drawer and verify widgets are grouped by category (Charts, Metrics, Data, Fleet Overview) with improved descriptions.
