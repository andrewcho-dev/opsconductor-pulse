# Task 2: Redesign HomePage.tsx

## Files to modify
- `frontend/src/features/home/HomePage.tsx`

## New file to create
- `frontend/src/features/home/useBroadcasts.ts` — React Query hook for broadcasts

## Read first
Read the current `frontend/src/features/home/HomePage.tsx` in full.
Read `frontend/src/lib/api.ts` or wherever API calls are made to understand the fetch pattern.

## Step 1 — useBroadcasts hook

Create `frontend/src/features/home/useBroadcasts.ts`:

```ts
import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"  // use the existing fetch utility

export interface Broadcast {
  id: string
  title: string
  body: string
  type: "info" | "warning" | "update"
  pinned: boolean
  created_at: string
}

export function useBroadcasts() {
  return useQuery({
    queryKey: ["broadcasts"],
    queryFn: () => apiFetch<Broadcast[]>("/api/v1/customer/broadcasts"),
    staleTime: 5 * 60 * 1000,  // 5 min — news doesn't change often
  })
}
```

Adjust the import path for `apiFetch` to match what the rest of the codebase uses.

## Step 2 — New HomePage layout

Replace the current HomePage content with a two-column layout:

### Overall structure
```
<div class="page-container">
  <PageHeader title="Overview" />

  <div class="two-col-grid">
    <!-- LEFT: main content (2/3 width) -->
    <div class="main-col">
      <FleetHealthSection />
      <QuickActionsSection />
      <RecentAlertsSection />  {/* keep but make compact */}
    </div>

    <!-- RIGHT: sidebar panel (1/3 width) -->
    <div class="side-col">
      <DocumentationSection />
      <NewsSection />
    </div>
  </div>
</div>
```

Use Tailwind: `grid grid-cols-1 lg:grid-cols-3 gap-6` with the main col spanning 2 columns
(`lg:col-span-2`) and side col taking 1 column.

### FleetHealthSection
Keep the existing 4 KPI cards (Total, Online, Stale, Offline) but make them more compact.
Use smaller cards in a 2×2 or 4-across grid. Pull from existing `useFleetSummary` or similar hook.

### QuickActionsSection
Keep the 4 quick action buttons but style them as outlined cards instead of a single card
with buttons. Each action: icon + title + short description + arrow.

### DocumentationSection (RIGHT column, top)

```tsx
<Card>
  <CardHeader>
    <CardTitle>Documentation</CardTitle>
  </CardHeader>
  <CardContent>
    <ul class="space-y-2">
      <li><a href="#" class="doc-link">Getting started guide →</a></li>
      <li><a href="#" class="doc-link">Device provisioning →</a></li>
      <li><a href="#" class="doc-link">Alert configuration →</a></li>
      <li><a href="#" class="doc-link">API reference →</a></li>
      <li><a href="#" class="doc-link">Fleet management →</a></li>
    </ul>
  </CardContent>
</Card>
```

Links are `href="#"` placeholders. Style each link as: text-sm text-primary hover:underline flex items-center gap-1.

### NewsSection (RIGHT column, below docs)

```tsx
<Card>
  <CardHeader>
    <CardTitle>News & Updates</CardTitle>
  </CardHeader>
  <CardContent>
    {/* if loading: show 3 skeleton rows */}
    {/* if empty: show "No updates at this time" */}
    {/* if data: show broadcast items */}
    {broadcasts.map(b => (
      <BroadcastItem key={b.id} broadcast={b} />
    ))}
  </CardContent>
</Card>
```

BroadcastItem (inline component):
- Type badge: "info" → blue, "warning" → yellow/orange, "update" → green
- Title in semibold
- Body text in text-sm text-muted-foreground
- Date in text-xs text-muted-foreground
- Pinned items get a pin icon

### OnboardingChecklist
Only show if user has 0 devices (check fleet summary total === 0). Move to BOTTOM of main col.
Do not show when user has devices.

## Step 3 — Remove clutter
Remove from the current page:
- The "Resource Usage" section (subscription entitlement cards) — move to Account/Billing page
- Any duplicate data already shown in the KPIs

## After changes
Run: `cd frontend && npm run build 2>&1 | tail -20`
Fix all TypeScript errors.
