# Task 5: Standardize Typography Hierarchy

## Context

Typography is chaotic. KPI numbers use 5 different sizes. Page titles are smaller than stat numbers. Card titles have ad-hoc overrides. There's no clear hierarchy.

## The Scale

Enforce this typography scale across the entire app:

| Role | Size | Weight | Tailwind |
|------|------|--------|----------|
| Page title | 18px | semibold | `text-lg font-semibold` |
| Section heading | 14px | semibold, uppercase, muted | `text-sm font-semibold uppercase tracking-wide text-muted-foreground` |
| Card title | 14px | semibold | `text-sm font-semibold` (default, no override) |
| KPI number | 24px | semibold | `text-2xl font-semibold` |
| KPI label | 12px | muted | `text-xs text-muted-foreground` |
| Body text | 14px | normal | `text-sm` |
| Caption | 12px | muted | `text-xs text-muted-foreground` |
| Modal/dialog title | 16px | semibold | `text-base font-semibold` |

## Step 1: Fix PageHeader

**File:** `frontend/src/components/shared/PageHeader.tsx`

```
BEFORE: <h1 className="text-xl font-semibold">{title}</h1>
AFTER:  <h1 className="text-lg font-semibold">{title}</h1>
```

## Step 2: Fix CertificateOverviewPage custom header

**File:** `frontend/src/features/operator/CertificateOverviewPage.tsx`

```
BEFORE: <h1 className="text-xl font-bold">Certificate Overview</h1>
AFTER:  <h1 className="text-lg font-semibold">Certificate Overview</h1>
```

## Step 3: Fix OperatorDashboard heading

**File:** `frontend/src/features/operator/OperatorDashboard.tsx`

```
BEFORE: <div className="text-2xl font-semibold">Operator Console</div>
AFTER:  <div className="text-lg font-semibold">Operator Console</div>
```

## Step 4: Fix EmptyState heading

**File:** `frontend/src/components/shared/EmptyState.tsx`

```
BEFORE: <h3 className="text-lg font-medium text-foreground">{title}</h3>
AFTER:  <h3 className="text-sm font-semibold text-foreground">{title}</h3>
```

## Step 5: Sweep all font-bold → font-semibold

Run: `grep -rn "font-bold" frontend/src/ --include="*.tsx" | grep -v node_modules`

Change every `font-bold` to `font-semibold`. We use ONE weight for emphasis.

**Exception:** Keep `font-bold` in `NOCPage.tsx` for the NOC sidebar label — that's a special full-screen mode.

**Exception:** Keep `font-bold` in `NotFoundPage.tsx` for the 404 heading — that's intentionally dramatic.

## Step 6: Fix AnalyticsPage page title

**File:** `frontend/src/features/analytics/AnalyticsPage.tsx`

If there's a hardcoded `<h1 className="text-lg font-semibold">Analytics</h1>`, verify it matches the scale. If it uses PageHeader, no change needed.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
