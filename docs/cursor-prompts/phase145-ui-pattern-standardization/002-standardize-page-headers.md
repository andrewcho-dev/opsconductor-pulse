# Task 2: Standardize Page Headers

## Context

Two pages don't use the PageHeader component at all — they have custom header layouts. Every page must use PageHeader for consistency.

## Step 1: Fix OperatorDashboard

**File:** `frontend/src/features/operator/OperatorDashboard.tsx`

Currently (lines 69-81) uses a custom flex layout with `text-2xl font-semibold` for "Operator Console".

Replace the custom header (lines 69-81) with PageHeader:
```tsx
<PageHeader
  title="Operator Console"
  description={`${health?.status?.toUpperCase() ?? "UNKNOWN"} | Last: ${lastUpdated}`}
/>
```

Remove the status dot from the description — it's redundant with the status text. If you want to keep a visual indicator, add it as part of the description string.

Import PageHeader:
```tsx
import { PageHeader } from "@/components/shared";
```

## Step 2: Fix SystemDashboard header controls

**File:** `frontend/src/features/operator/SystemDashboard.tsx`

This page has custom controls (Pause/Play, Refresh, interval selector) built with raw `<select>` and `<button>` elements (lines 250-276).

Wrap the controls in a PageHeader-compatible format. The SystemDashboard is a special case — it's an operator monitoring page that needs real-time controls. Keep the controls but move them into the PageHeader `action` prop.

At the top of the return (line 230), wrap everything:
```tsx
return (
  <div className="space-y-4">
    <PageHeader
      title="System"
      description={
        health?.status
          ? `${health.status.toUpperCase()}${!isOnline ? " — OFFLINE" : ""}`
          : "Loading..."
      }
      action={
        <div className="flex items-center gap-2">
          <select
            value={refreshInterval}
            onChange={e => setRefreshInterval(Number(e.target.value))}
            className="h-8 text-sm border border-border rounded-md bg-background px-2"
          >
            <option value={5000}>5s</option>
            <option value={10000}>10s</option>
            <option value={30000}>30s</option>
          </select>
          <Button
            variant={isPaused ? "default" : "outline"}
            size="sm"
            onClick={() => setIsPaused(p => !p)}
            title={isPaused ? "Resume" : "Pause"}
          >
            {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isFetching}
            title="Refresh (R)"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      }
    />
    {/* rest of the dashboard content */}
```

Remove the old custom header/controls block. Import `Button` and `PageHeader`:
```tsx
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
```

The ServiceChip strip and metrics grid remain as content below the PageHeader.

## Step 3: Fix CertificateOverviewPage custom header

**File:** `frontend/src/features/operator/CertificateOverviewPage.tsx`

Lines 140-150 use a custom flex layout with `<h1>` and `<p>` instead of PageHeader.

Replace with:
```tsx
<PageHeader
  title="Certificate Overview"
  description="Fleet-wide view of device X.509 certificates across all tenants."
  action={
    <Button variant="outline" onClick={handleDownloadCaBundle}>
      Download CA Bundle
    </Button>
  }
/>
```

Import PageHeader if not already imported.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
