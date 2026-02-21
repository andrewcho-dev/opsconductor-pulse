# Task 4: Quota/Usage KPIs on Home Page + BillingPage Refactor

## Objective

1. Add a resource usage/quota section to the Home page using `KpiCard` + the entitlements API
2. Refactor the BillingPage's custom `ProgressBar` to use the shared `KpiCard` component

## Prerequisites

- `KpiCard` component exists at `frontend/src/components/shared/KpiCard.tsx`
- `getEntitlements()` exists at `frontend/src/services/api/billing.ts`
- `AccountEntitlements` type has `usage: Record<string, { current: number; limit: number | null }>`

---

## Part 1: Home Page — Resource Usage Section

### File to Modify

`frontend/src/features/home/HomePage.tsx`

### Changes

**1. Add imports:**

```tsx
import { getEntitlements } from "@/services/api/billing";
```

**2. Add entitlements query** (alongside the existing alert query):

```tsx
const { data: entitlements } = useQuery({
  queryKey: ["home-entitlements"],
  queryFn: getEntitlements,
  staleTime: 60000,
});
```

**3. Derive usage rows** (before the return statement):

```tsx
const usageKpis = Object.entries(entitlements?.usage ?? {})
  .filter(([, { limit }]) => limit != null && limit > 0)
  .slice(0, 4)
  .map(([key, { current, limit }]) => ({
    key,
    label: key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()),
    current,
    limit: limit!,
  }));
```

**4. Add a "Resource Usage" section** — place it after the "Fleet Health KPIs" grid and before "Quick Actions":

```tsx
{/* Resource Usage */}
{usageKpis.length > 0 && (
  <div className="space-y-2">
    <h3 className="text-sm font-medium text-muted-foreground">Resource Usage</h3>
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {usageKpis.map((u) => (
        <KpiCard
          key={u.key}
          label={u.label}
          value={`${u.current} / ${u.limit}`}
          current={u.current}
          max={u.limit}
          description={`${Math.round((u.current / u.limit) * 100)}% used`}
        />
      ))}
    </div>
  </div>
)}
```

**Notes:**
- Filter to only show items where `limit` is set (non-null, > 0) — unlimited resources are skipped
- Cap at 4 KPI cards to fit the grid layout
- `KpiCard` auto-renders a `Progress` bar when `current` and `max` are provided
- `staleTime: 60000` (1 minute) prevents excessive refetching on the Home page

---

## Part 2: BillingPage — Replace Custom ProgressBar with KpiCard

### File to Modify

`frontend/src/features/settings/BillingPage.tsx`

### Changes

**1. Add import:**

```tsx
import { KpiCard } from "@/components/shared/KpiCard";
```

**2. Remove the local `usageColor` function and `ProgressBar` component** (lines 25-39 approximately):

Delete:
```tsx
function usageColor(pct: number) {
  if (pct > 90) return "bg-status-critical";
  if (pct >= 75) return "bg-status-warning";
  return "bg-status-online";
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div
        className={`h-2 rounded-full ${usageColor(percent)}`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}
```

**3. Replace the "Usage & Limits" Card** (the one with the Table) with a KpiCard grid:

Replace the entire `<Card>` block that contains the "Usage & Limits" `<Table>` with:

```tsx
<Card>
  <CardHeader>
    <CardTitle>Usage & Limits</CardTitle>
  </CardHeader>
  <CardContent>
    {usageRows.length === 0 ? (
      <div className="text-sm text-muted-foreground">
        No usage data available.
      </div>
    ) : (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {usageRows.map((r) => (
          <KpiCard
            key={r.key}
            label={r.label}
            value={`${r.current} / ${r.limit ?? "∞"}`}
            current={r.current}
            max={r.limit ?? undefined}
            description={r.limit ? `${r.percent_used}% used` : "Unlimited"}
          />
        ))}
      </div>
    )}
  </CardContent>
</Card>
```

**4. Clean up the `usageRows` memo** — the `percent_used` field is no longer needed for the ProgressBar but is still used in the KpiCard description, so keep the memo as-is.

**5. Remove unused imports** — `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow` may still be needed for the Subscriptions table above. Only remove them if they are completely unused after the change. Check carefully:
- The "Subscriptions" card still uses `<Table>`, so keep those imports.

---

## Verification

- `npx tsc --noEmit` passes
- Home page shows "Resource Usage" section with KpiCard progress bars (only if entitlements have usage data with limits)
- BillingPage shows "Usage & Limits" as a grid of KpiCards instead of a table with custom progress bars
- BillingPage's Subscriptions table still works (uses Table components)
- KpiCard progress bars render correctly with percentage fill
