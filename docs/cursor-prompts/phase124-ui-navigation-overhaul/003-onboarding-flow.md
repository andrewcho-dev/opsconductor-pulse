# Task 003: Onboarding Checklist for New Tenants

## Commit message
```
feat(ui): add new-tenant onboarding checklist on dashboard
```

## Overview
Create an `OnboardingChecklist` component that detects new tenants (0 devices) and displays a step-by-step setup guide on the DashboardPage. Steps update dynamically as the user completes them. Dismissible with persistence to localStorage.

---

## Step 1: Create `frontend/src/components/shared/OnboardingChecklist.tsx`

### Detection logic
The component uses existing API hooks to determine if the tenant is "new" (needs onboarding). The checklist shows when:
- The tenant has 0 devices, OR
- Not all steps are complete AND the user has not dismissed the checklist.

The dismiss state is stored in localStorage key `pulse_onboarding_dismissed`.

### Checklist steps

Each step queries real data to determine completion status:

| # | Step | Completed when | Link |
|---|------|---------------|------|
| 1 | Add your first device | Device count > 0 | `/devices` |
| 2 | Configure an alert rule | Alert rule count > 0 | `/alert-rules` |
| 3 | Set up notifications | Notification channel count > 0 | `/notifications` |
| 4 | Invite your team | User count > 1 (self + at least one invite) | `/users` |

### Data fetching

Use TanStack React Query hooks to check completion. These queries should have `staleTime: 30000` so they do not re-fetch on every render:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchDevices } from "@/services/api/devices";
import { apiGet } from "@/services/api/client";
import type { AlertRuleListResponse } from "@/services/api/types";
import { fetchTenantUsers } from "@/services/api/users";

// Step 1: Devices
const { data: deviceData, isLoading: devicesLoading } = useQuery({
  queryKey: ["onboarding-devices"],
  queryFn: () => fetchDevices({ limit: 1 }),
  staleTime: 30000,
});
const hasDevices = (deviceData?.total ?? 0) > 0;

// Step 2: Alert rules
const { data: rulesData, isLoading: rulesLoading } = useQuery({
  queryKey: ["onboarding-rules"],
  queryFn: () => apiGet<AlertRuleListResponse>("/customer/alert-rules"),
  staleTime: 30000,
});
const hasRules = (rulesData?.count ?? 0) > 0;

// Step 3: Notification channels
const { data: channelsData, isLoading: channelsLoading } = useQuery({
  queryKey: ["onboarding-channels"],
  queryFn: () => apiGet<{ channels: unknown[]; total: number }>("/customer/notification-channels"),
  staleTime: 30000,
});
const hasChannels = (channelsData?.total ?? 0) > 0;

// Step 4: Users (count > 1 means team member invited)
const { data: usersData, isLoading: usersLoading } = useQuery({
  queryKey: ["onboarding-users"],
  queryFn: () => fetchTenantUsers(undefined, 2, 0),
  staleTime: 30000,
});
const hasTeam = (usersData?.total ?? 0) > 1;
```

### Dismiss logic

```typescript
const DISMISS_KEY = "pulse_onboarding_dismissed";

const [dismissed, setDismissed] = useState(() => {
  return localStorage.getItem(DISMISS_KEY) === "true";
});

const handleDismiss = () => {
  localStorage.setItem(DISMISS_KEY, "true");
  setDismissed(true);
};
```

### Visibility rule

```typescript
const allComplete = hasDevices && hasRules && hasChannels && hasTeam;
const isLoading = devicesLoading || rulesLoading || channelsLoading || usersLoading;

// Don't show if dismissed, all complete, or still loading initial data
if (dismissed || allComplete || isLoading) return null;
```

### Component JSX

Use Shadcn Card components for the checklist container. Each step is a row with a check/circle icon, label, description, and a link button.

```typescript
import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2, Circle, Cpu, ShieldAlert, Webhook, Users, X, Rocket,
} from "lucide-react";
import { fetchDevices } from "@/services/api/devices";
import { apiGet } from "@/services/api/client";
import type { AlertRuleListResponse } from "@/services/api/types";
import { fetchTenantUsers } from "@/services/api/users";

interface Step {
  label: string;
  description: string;
  href: string;
  icon: typeof Cpu;
  complete: boolean;
}

export function OnboardingChecklist() {
  // ... state and queries as above ...

  const steps: Step[] = [
    {
      label: "Add your first device",
      description: "Register a device to start collecting telemetry data.",
      href: "/devices",
      icon: Cpu,
      complete: hasDevices,
    },
    {
      label: "Configure an alert rule",
      description: "Set thresholds to get notified when metrics go out of range.",
      href: "/alert-rules",
      icon: ShieldAlert,
      complete: hasRules,
    },
    {
      label: "Set up notifications",
      description: "Connect a webhook, email, or MQTT channel for alert delivery.",
      href: "/notifications",
      icon: Webhook,
      complete: hasChannels,
    },
    {
      label: "Invite your team",
      description: "Add team members so they can monitor devices too.",
      href: "/users",
      icon: Users,
      complete: hasTeam,
    },
  ];

  const completedCount = steps.filter((s) => s.complete).length;

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-base">Welcome to OpsConductor Pulse</CardTitle>
            <p className="text-sm text-muted-foreground mt-0.5">
              Complete these steps to get the most out of your fleet monitoring.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{completedCount}/{steps.length}</Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleDismiss}
            title="Dismiss checklist"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div
              key={step.label}
              className={`flex items-start gap-3 rounded-md border p-3 transition-colors ${
                step.complete
                  ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30"
                  : "border-border bg-card"
              }`}
            >
              {step.complete ? (
                <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-600 shrink-0" />
              ) : (
                <Circle className="mt-0.5 h-5 w-5 text-muted-foreground shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span
                      className={`text-sm font-medium ${
                        step.complete ? "line-through text-muted-foreground" : ""
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {!step.complete && (
                    <Button variant="outline" size="sm" asChild className="shrink-0">
                      <Link to={step.href}>Get started</Link>
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
```

---

## Step 2: Mount in DashboardPage.tsx

Edit `frontend/src/features/dashboard/DashboardPage.tsx`:

Add the import:
```typescript
import { OnboardingChecklist } from "@/components/shared/OnboardingChecklist";
```

Insert the component **after** the `<PageHeader>` and **before** the first `<WidgetErrorBoundary>` (the FleetKpiStrip). Place it inside the existing `<div className="space-y-6">` so it participates in the vertical spacing:

```tsx
export default function DashboardPage() {
  // ... existing code ...

  return (
    <div className="space-y-6">
      <PageHeader
        title="Fleet Overview"
        description={subtitle}
        action={/* ... existing ... */}
      />

      {/* NEW: Onboarding checklist for new tenants */}
      <OnboardingChecklist />

      <WidgetErrorBoundary widgetName="Fleet KPI Strip">
        <FleetKpiStrip />
      </WidgetErrorBoundary>

      {/* ... rest of existing widgets unchanged ... */}
    </div>
  );
}
```

The `OnboardingChecklist` component handles its own visibility logic -- it returns `null` when dismissed or when all steps are complete, so it does not need conditional rendering in DashboardPage.

---

## Step 3: Export from shared index (if exists)

Check if `frontend/src/components/shared/index.ts` exists. If so, add the export:
```typescript
export { OnboardingChecklist } from "./OnboardingChecklist";
```

If no barrel file exists, skip this step; the direct import path is fine.

---

## Verification

1. `cd frontend && npm run build` -- zero errors.
2. Log in as a customer tenant that has 0 devices, 0 alert rules, 0 notification channels, and only 1 user (yourself).
3. Dashboard shows the onboarding checklist card between PageHeader and FleetKpiStrip.
4. The card shows 4 steps, all with empty circles (0/4 complete).
5. Click "Get started" on "Add your first device" -- navigates to `/devices`.
6. After adding a device, return to dashboard. Step 1 now shows a green check and strikethrough text. Badge shows 1/4.
7. Click the X (dismiss) button. Checklist disappears.
8. Refresh the page. Checklist stays hidden (localStorage).
9. Clear localStorage key `pulse_onboarding_dismissed`. Refresh. Checklist reappears (if not all steps complete).
10. Complete all 4 steps. Checklist auto-hides (even without dismissing).
11. Log in as an existing tenant with devices. Checklist does not appear (all steps already complete).

---

## Files Created/Modified

| Action | File |
|--------|------|
| CREATE | `frontend/src/components/shared/OnboardingChecklist.tsx` |
| MODIFY | `frontend/src/features/dashboard/DashboardPage.tsx` |
