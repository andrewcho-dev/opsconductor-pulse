# Phase 148f — Widget Sizing Constraints, Padding Reduction, and Scroll Fixes

## Problems

1. **Widgets can be resized smaller than their content** — `DashboardBuilder.tsx` builds react-grid-layout items without `minH`/`minW` constraints. The widget registry defines `minSize` for every widget type, but it's never applied. Users can shrink a table widget to 1×1 and lose all content.

2. **Excessive internal padding** — The shadcn `Card` component applies `py-3` (12px top + 12px bottom). With a row height of 100px, that's 24% of a single-row widget wasted on padding. The `WidgetContainer` already overrides `CardContent` padding to `p-1.5`, but the outer Card `py-3` still applies.

3. **No vertical scrollbar on table widget** — `TableRenderer.tsx` wraps the table in a plain `<div>` with no overflow handling. When content exceeds widget height, it's clipped by `WidgetContainer`'s `overflow-hidden`.

4. **No vertical scrollbar on alert feed widget** — `AlertFeedRenderer.tsx` has the same problem — a `space-y-1` div with no scroll container.

## Fixes

### Fix 1: Enforce minSize in DashboardBuilder.tsx

**File:** `frontend/src/features/dashboard/DashboardBuilder.tsx`

In the `layoutItems` useMemo (around line 53-67), look up each widget's definition from the registry and apply `minW`/`minH`:

```tsx
import { getWidgetDefinition } from "./widgets/widget-registry";

// Inside the useMemo:
const layoutItems: RglLayoutItem[] = useMemo(
  () =>
    dashboard.widgets.map((w) => {
      const local = localLayoutRef.current?.find((l) => l.i === String(w.id));
      const def = getWidgetDefinition(w.widget_type);
      return {
        i: String(w.id),
        x: local?.x ?? w.position?.x ?? 0,
        y: local?.y ?? w.position?.y ?? 0,
        w: local?.w ?? w.position?.w ?? def?.defaultSize.w ?? 2,
        h: local?.h ?? w.position?.h ?? def?.defaultSize.h ?? 2,
        minW: def?.minSize.w ?? 1,
        minH: def?.minSize.h ?? 1,
        maxW: def?.maxSize.w,
        maxH: def?.maxSize.h,
        static: !isEditing,
      };
    }),
  [dashboard.widgets, isEditing]
);
```

This ensures react-grid-layout prevents resizing below the widget's defined minimum. Note: `getWidgetDefinition` is already exported from `widget-registry.ts`.

### Fix 2: Reduce Card padding in WidgetContainer.tsx

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

The outer `<Card>` on line 68 currently has:
```tsx
<Card className="relative h-full flex flex-col overflow-hidden">
```

The `Card` component internally applies `py-3`. Override it to zero out the wasteful vertical padding:

```tsx
<Card className="relative h-full flex flex-col overflow-hidden py-0">
```

The `py-0` will override the Card's default `py-3`, eliminating 24px of dead space. The CardHeader already has its own `py-1.5` and CardContent has `p-1.5`, so internal spacing remains correct.

### Fix 3: Add scroll to TableRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/TableRenderer.tsx`

Wrap the table output in a scroll container. The renderer should fill its parent and scroll vertically:

Change the outermost wrapper from:
```tsx
<div className="rounded-md border border-border">
  <Table>
```

To:
```tsx
<div className="h-full flex flex-col overflow-hidden rounded-md border border-border">
  <div className="flex-1 overflow-y-auto min-h-0">
    <Table>
```

And close the extra `</div>` after `</Table>`.

This creates a flex column that fills the widget, with the inner div providing vertical scrolling. The `min-h-0` is essential for flex children to actually shrink and enable scrolling.

### Fix 4: Add scroll to AlertFeedRenderer.tsx

**File:** `frontend/src/features/dashboard/widgets/renderers/AlertFeedRenderer.tsx`

Same pattern. Change the outermost wrapper from:
```tsx
<div className="space-y-1">
```

To:
```tsx
<div className="h-full overflow-y-auto space-y-1">
```

This makes the alert list scroll when items exceed the widget height.

## Files to Modify

1. `frontend/src/features/dashboard/DashboardBuilder.tsx` — add minW/minH/maxW/maxH to layout items
2. `frontend/src/features/dashboard/widgets/WidgetContainer.tsx` — add `py-0` to Card
3. `frontend/src/features/dashboard/widgets/renderers/TableRenderer.tsx` — add scroll container
4. `frontend/src/features/dashboard/widgets/renderers/AlertFeedRenderer.tsx` — add scroll container

## Verification

1. **minSize enforcement**: Enter edit mode, try to resize a table widget (minSize 3×2) below 3 columns or 2 rows — react-grid-layout should prevent it
2. **Reduced padding**: Widgets should have noticeably less dead space at top and bottom. Content should fill the card more completely.
3. **Table scroll**: Add a device table widget, resize it to its minimum height. If there are more rows than fit, a vertical scrollbar should appear and the table should scroll.
4. **Alert feed scroll**: Same test with alert feed — scrollbar should appear when content exceeds widget height.
5. **Build check**: `cd frontend && npx tsc --noEmit && npm run build` — both must pass.
