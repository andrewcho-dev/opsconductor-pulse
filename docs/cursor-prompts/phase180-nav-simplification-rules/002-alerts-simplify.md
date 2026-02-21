# Task 2: Simplify Alerts to Inbox Only

## Objective

With Rules, Escalation, On-Call, and Maintenance tabs moved to the Rules hub (Task 1), simplify the Alerts page to show just the alert inbox. The hub wrapper with tab navigation is no longer needed for a single view.

## File to Modify

`frontend/src/features/alerts/AlertsHubPage.tsx`

## Changes

Replace the entire hub page implementation with a simplified version that renders `AlertListPage` directly (no tabs):

```tsx
import { PageHeader } from "@/components/shared";
import AlertListPage from "./AlertListPage";

export default function AlertsHubPage() {
  return (
    <div className="space-y-4">
      <PageHeader title="Alerts" description="Monitor and triage active alerts" />
      <AlertListPage embedded />
    </div>
  );
}

export const Component = AlertsHubPage;
```

**What changes:**
- Remove the `TABS` array and all tab-related JSX
- Remove `useSearchParams` import (no longer needed)
- Remove `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` imports
- Remove imports for `AlertRulesPage`, `EscalationPoliciesPage`, `OncallSchedulesPage`, `MaintenanceWindowsPage`
- Keep `AlertListPage` import and render it with `embedded` prop

**What stays the same:**
- The route `/alerts` still works
- `AlertListPage` renders identically (it was already `embedded` mode)
- The `PageHeader` provides the page title

## Route Redirects

These redirects will be added in Task 4 (sidebar-routes), but note them here for context:

Old URL → New URL:
- `/alerts?tab=rules` → `/rules?tab=alert-rules`
- `/alerts?tab=escalation` → `/rules?tab=escalation`
- `/alerts?tab=oncall` → `/rules?tab=oncall`
- `/alerts?tab=maintenance` → `/rules?tab=maintenance`

These are query-parameter-based redirects, which React Router doesn't handle natively. The simplest approach is to add redirect logic inside `AlertsHubPage` itself:

```tsx
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import AlertListPage from "./AlertListPage";

const TAB_REDIRECTS: Record<string, string> = {
  rules: "/rules?tab=alert-rules",
  escalation: "/rules?tab=escalation",
  oncall: "/rules?tab=oncall",
  maintenance: "/rules?tab=maintenance",
};

export default function AlertsHubPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const tab = params.get("tab");

  useEffect(() => {
    if (tab && TAB_REDIRECTS[tab]) {
      navigate(TAB_REDIRECTS[tab], { replace: true });
    }
  }, [tab, navigate]);

  // If redirecting, don't render the page
  if (tab && TAB_REDIRECTS[tab]) return null;

  return (
    <div className="space-y-4">
      <PageHeader title="Alerts" description="Monitor and triage active alerts" />
      <AlertListPage embedded />
    </div>
  );
}

export const Component = AlertsHubPage;
```

This handles the case where someone has a bookmark to `/alerts?tab=rules` — they'll be redirected to `/rules?tab=alert-rules`.

## Verification

- `npx tsc --noEmit` passes
- `/alerts` shows the alert inbox directly (no tab navigation)
- `/alerts?tab=rules` redirects to `/rules?tab=alert-rules`
- `/alerts?tab=escalation` redirects to `/rules?tab=escalation`
- `/alerts?tab=oncall` redirects to `/rules?tab=oncall`
- `/alerts?tab=maintenance` redirects to `/rules?tab=maintenance`
- `/alerts?tab=inbox` still shows the alert inbox (no redirect for `inbox` tab)
