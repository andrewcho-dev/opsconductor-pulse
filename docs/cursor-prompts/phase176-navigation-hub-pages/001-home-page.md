# Task 1: Home Landing Page

## Objective

Create a new Home page at `/home` that serves as the default landing page for customers. It provides fleet health at a glance, quick actions, recent alerts, and an onboarding checklist.

## File to Create

`frontend/src/features/home/HomePage.tsx`

## Design

The Home page has 4 sections stacked vertically:

1. **Fleet Health KPIs** — 4 KpiCards in a grid showing Total Devices, Online, Stale, Offline
2. **Quick Actions** — Row of action buttons (Add Device, View Alerts, Fleet Map, Create Alert Rule)
3. **Recent Alerts** — Last 5 open alerts in a compact list
4. **Getting Started** — Inline OnboardingChecklist (if not dismissed)

## Implementation

```tsx
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Cpu,
  Plus,
  Bell,
  MapPin,
  ShieldAlert,
  AlertTriangle,
  ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { KpiCard } from "@/components/shared/KpiCard";
import { OnboardingChecklist } from "@/components/shared/OnboardingChecklist";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFleetSummary } from "@/hooks/use-devices";
import { fetchAlerts } from "@/services/api/alerts";
import { useAuth } from "@/services/auth/AuthProvider";

export default function HomePage() {
  const { user } = useAuth();
  const { summary, isLoading: fleetLoading } = useFleetSummary();

  const { data: alertData, isLoading: alertsLoading } = useQuery({
    queryKey: ["home-recent-alerts"],
    queryFn: () => fetchAlerts("OPEN", 5, 0),
    staleTime: 30000,
  });

  const orgName = user?.tenantId ?? "your organization";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back`}
        description={`Here's what's happening across ${orgName}`}
      />

      {/* Fleet Health KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {fleetLoading ? (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        ) : (
          <>
            <KpiCard
              label="Total Devices"
              value={summary?.total ?? 0}
              icon={<Cpu className="h-4 w-4" />}
            />
            <KpiCard
              label="Online"
              value={summary?.ONLINE ?? 0}
              valueClassName="text-status-online"
              description={
                summary?.total
                  ? `${Math.round(((summary.ONLINE ?? 0) / summary.total) * 100)}% of fleet`
                  : undefined
              }
            />
            <KpiCard
              label="Stale"
              value={summary?.STALE ?? 0}
              valueClassName="text-status-stale"
            />
            <KpiCard
              label="Offline"
              value={summary?.OFFLINE ?? 0}
              valueClassName="text-muted-foreground"
            />
          </>
        )}
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/devices/wizard">
                <Plus className="mr-1 h-4 w-4" />
                Add Device
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/alerts">
                <Bell className="mr-1 h-4 w-4" />
                View Alerts
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/map">
                <MapPin className="mr-1 h-4 w-4" />
                Fleet Map
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link to="/alerts?tab=rules">
                <ShieldAlert className="mr-1 h-4 w-4" />
                Alert Rules
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Alerts */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">Recent Alerts</CardTitle>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/alerts" className="text-xs">
              View all
              <ChevronRight className="ml-1 h-3 w-3" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : !alertData?.alerts?.length ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No open alerts — your fleet is healthy.
            </p>
          ) : (
            <div className="space-y-2">
              {alertData.alerts.slice(0, 5).map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-center gap-3 rounded-md border p-2 text-sm"
                >
                  <AlertTriangle className="h-4 w-4 shrink-0 text-destructive" />
                  <div className="flex-1 min-w-0 truncate">{alert.title ?? alert.rule_name}</div>
                  <Badge variant="outline" className="shrink-0 text-xs">
                    {alert.severity}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Onboarding Checklist */}
      <OnboardingChecklist />
    </div>
  );
}

export const Component = HomePage;
```

**Notes:**
- The `useFleetSummary()` hook uses WebSocket for real-time updates (already implemented)
- `fetchAlerts("OPEN", 5, 0)` fetches the first 5 open alerts — check the actual function signature and adjust if needed (it may take parameters differently)
- The `alert.title ?? alert.rule_name` pattern handles both titled and auto-generated alerts — check the actual `Alert` type for the correct field names
- `text-status-online` and `text-status-stale` use the status color tokens defined in Phase 175's CSS
- Export both `default` and `Component` for lazy loading compatibility

## Route Registration

This will be handled in Task 8 (route updates). For now, just create the file.

## Verification

- `npx tsc --noEmit` passes
- File is created at the correct path
- All imports resolve correctly
- Component renders fleet health KPIs, quick actions, recent alerts, and onboarding checklist
