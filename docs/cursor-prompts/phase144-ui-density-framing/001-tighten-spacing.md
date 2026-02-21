# Task 1: Tighten Global Spacing

## Context

The app wastes significant screen space due to compounded padding. Currently:
- AppShell main area: `p-6` (24px all sides)
- Page wrappers: `space-y-6` (24px between sections)
- Card component: `py-4` (16px top/bottom) + `gap-4` (16px between children)
- Card grids: `gap-4` (16px)
- Modal containers: `p-6` (24px)
- Subscription banners: `px-6` (24px horizontal)

## Changes

### 1a. AppShell — reduce main content padding

**File:** `frontend/src/components/layout/AppShell.tsx`

```
BEFORE: <main className="flex-1 overflow-auto p-6">
AFTER:  <main className="flex-1 overflow-auto p-4">
```

### 1b. Card component — tighten internal spacing

**File:** `frontend/src/components/ui/card.tsx`

Card wrapper:
```
BEFORE: "bg-card text-card-foreground flex flex-col gap-4 rounded-lg border py-4"
AFTER:  "bg-card text-card-foreground flex flex-col gap-2 rounded-lg border py-3"
```

CardHeader:
```
BEFORE: "... gap-1.5 px-4 ... [.border-b]:pb-4"
AFTER:  "... gap-1.5 px-3 ... [.border-b]:pb-3"
```

CardContent:
```
BEFORE: "px-4"
AFTER:  "px-3"
```

CardFooter:
```
BEFORE: "flex items-center px-4 [.border-t]:pt-4"
AFTER:  "flex items-center px-3 [.border-t]:pt-3"
```

### 1c. Page wrappers — all space-y-6 to space-y-4

Run: `grep -rn "space-y-6" frontend/src/features/ --include="*.tsx"`

For every page-level wrapper (the outermost `<div className="space-y-6">`), change to `space-y-4`.

There are ~47 files. Change ALL of them.

**Exception:** Do NOT change `space-y-6` inside the SystemDashboard (`frontend/src/features/operator/SystemDashboard.tsx`) — it uses `space-y-2` already (correct).

### 1d. Card grid gaps

Run: `grep -rn "gap-4" frontend/src/features/ --include="*.tsx"` and look for grid containers that hold cards.

Change card grid containers from `gap-4` to `gap-3`. Common patterns:
- `grid gap-4 md:grid-cols-2` → `grid gap-3 md:grid-cols-2`
- `grid gap-4 md:grid-cols-3` → `grid gap-3 md:grid-cols-3`
- `grid gap-4 md:grid-cols-4` → `grid gap-3 md:grid-cols-4`

**Only change gaps in card/stat grids.** Leave `gap-4` in form layouts (flexbox with inputs) alone.

### 1e. WidgetContainer — tighten

**File:** `frontend/src/features/dashboard/widgets/WidgetContainer.tsx`

```
BEFORE: <CardHeader className="flex flex-row items-center justify-between py-2 px-3 shrink-0">
AFTER:  <CardHeader className="flex flex-row items-center justify-between py-1.5 px-2 shrink-0">
```

```
BEFORE: <CardContent className="flex-1 overflow-auto p-2">
AFTER:  <CardContent className="flex-1 overflow-auto p-1.5">
```

### 1f. Subscription banners — reduce horizontal padding

**File:** `frontend/src/components/layout/SubscriptionBanner.tsx`

Change all three banner variants from `px-6` to `px-4`.

### 1g. Modal containers — reduce padding

Run: `grep -rn "p-6 shadow" frontend/src/features/ --include="*.tsx"`

Change modal/dialog custom containers from `p-6` to `p-4`. Common pattern:
```
BEFORE: className="... p-6 shadow-lg space-y-4"
AFTER:  className="... p-4 shadow-lg space-y-3"
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
