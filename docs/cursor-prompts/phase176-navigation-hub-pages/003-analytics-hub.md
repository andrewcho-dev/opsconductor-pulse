# Task 3: Analytics Hub Page

## Objective

Create an Analytics hub page that consolidates the Analytics (Explorer) and Reports pages into a single page with 2 tabs. Modify each existing page to support an `embedded` prop.

## Files to Modify

1. `frontend/src/features/analytics/AnalyticsPage.tsx` — add `embedded` prop
2. `frontend/src/features/reports/ReportsPage.tsx` — add `embedded` prop

## File to Create

`frontend/src/features/analytics/AnalyticsHubPage.tsx`

---

## Step 1: Modify AnalyticsPage.tsx

Add `embedded` prop to the function signature:

```tsx
export default function AnalyticsPage({ embedded }: { embedded?: boolean }) {
```

AnalyticsPage does NOT use `PageHeader` — it has a custom header with an icon and export button. Find that custom header section and wrap it:

```tsx
{!embedded && (
  // ... the existing custom header JSX (icon, title, export button) ...
)}
```

If the export button is important for the embedded view, extract it and render it separately when embedded:

```tsx
{embedded && exportButton && (
  <div className="flex justify-end gap-2 mb-4">{exportButton}</div>
)}
```

## Step 2: Modify ReportsPage.tsx

Add `embedded` prop to the function signature:

```tsx
export default function ReportsPage({ embedded }: { embedded?: boolean }) {
```

ReportsPage uses `PageHeader`. Wrap it:

```tsx
{!embedded && <PageHeader title="Reports" description="Exports, SLA summaries, and report history." />}
```

## Step 3: Create AnalyticsHubPage

**Create** `frontend/src/features/analytics/AnalyticsHubPage.tsx`:

```tsx
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import AnalyticsPage from "./AnalyticsPage";
import ReportsPage from "@/features/reports/ReportsPage";

export default function AnalyticsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "explorer";

  return (
    <div className="space-y-4">
      <PageHeader
        title="Analytics"
        description="Query metrics and review operational reports"
      />
      <Tabs
        value={tab}
        onValueChange={(v) => setParams({ tab: v }, { replace: true })}
      >
        <TabsList variant="line">
          <TabsTrigger value="explorer">Explorer</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>
        <TabsContent value="explorer" className="mt-4">
          <AnalyticsPage embedded />
        </TabsContent>
        <TabsContent value="reports" className="mt-4">
          <ReportsPage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = AnalyticsHubPage;
```

## Verification

- `npx tsc --noEmit` passes
- AnalyticsHubPage renders with 2 tabs (Explorer, Reports)
- Explorer tab shows the analytics query builder and chart
- Reports tab shows exports, SLA summary, and report history
- No duplicate headers in either tab
- Tab state in URL: `/analytics?tab=reports`
