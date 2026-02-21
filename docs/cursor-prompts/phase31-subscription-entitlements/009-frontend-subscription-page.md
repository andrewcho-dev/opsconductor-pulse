# 009: Frontend Subscription Page

## Task

Create a customer-facing subscription management page showing plan details, usage, and audit history.

## Files to Create

1. `frontend/src/features/subscription/SubscriptionPage.tsx`
2. Add route and sidebar entry

## Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Subscription                                                │
│ Manage your subscription and device entitlements            │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌─────────────────────┐             │
│ │ Plan Details        │ │ Device Usage        │             │
│ │                     │ │                     │             │
│ │ Status: ACTIVE      │ │ ████████░░ 45/50    │             │
│ │ Plan: Standard      │ │ 90% used            │             │
│ │ Term: Jan 1 - Dec 31│ │                     │             │
│ │ Expires in: 245 days│ │ 5 devices available │             │
│ └─────────────────────┘ └─────────────────────┘             │
│                                                             │
│ ┌───────────────────────────────────────────────────────────┤
│ │ Subscription History                                      │
│ ├───────────────────────────────────────────────────────────┤
│ │ DEVICE_ADDED    │ sensor-042 added    │ 2 hours ago      │
│ │ DEVICE_REMOVED  │ sensor-001 removed  │ 1 day ago        │
│ │ RENEWED         │ Annual renewal      │ 30 days ago      │
│ └───────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
```

## Implementation

```tsx
import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import {
  CreditCard,
  Cpu,
  Calendar,
  Clock,
  Plus,
  Minus,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { apiGet } from "@/services/api/client";

interface Subscription {
  tenant_id: string;
  tenant_name: string;
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  term_start: string | null;
  term_end: string | null;
  days_until_expiry: number | null;
  plan_id: string | null;
  status: string;
  grace_end: string | null;
}

interface AuditEvent {
  id: number;
  event_type: string;
  event_timestamp: string;
  actor_type: string | null;
  details: Record<string, unknown> | null;
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    TRIAL: "bg-blue-100 text-blue-800",
    ACTIVE: "bg-green-100 text-green-800",
    GRACE: "bg-orange-100 text-orange-800",
    SUSPENDED: "bg-red-100 text-red-800",
    EXPIRED: "bg-gray-100 text-gray-800",
  };

  return (
    <Badge className={variants[status] || "bg-gray-100"}>
      {status}
    </Badge>
  );
}

function EventIcon({ type }: { type: string }) {
  switch (type) {
    case "DEVICE_ADDED":
      return <Plus className="h-4 w-4 text-green-600" />;
    case "DEVICE_REMOVED":
      return <Minus className="h-4 w-4 text-red-600" />;
    case "RENEWED":
    case "CREATED":
      return <RefreshCw className="h-4 w-4 text-blue-600" />;
    case "GRACE_STARTED":
    case "SUSPENDED":
      return <AlertTriangle className="h-4 w-4 text-orange-600" />;
    default:
      return <Clock className="h-4 w-4 text-gray-600" />;
  }
}

function formatEventDescription(event: AuditEvent): string {
  const details = event.details || {};
  switch (event.event_type) {
    case "DEVICE_ADDED":
      return `Device ${details.device_id || "unknown"} added`;
    case "DEVICE_REMOVED":
      return `Device ${details.device_id || "unknown"} removed`;
    case "RENEWED":
      return "Subscription renewed";
    case "CREATED":
      return "Subscription created";
    case "LIMIT_CHANGED":
      return `Device limit changed to ${details.new_limit || "?"}`;
    case "GRACE_STARTED":
      return "Grace period started";
    case "SUSPENDED":
      return "Subscription suspended";
    case "REACTIVATED":
      return "Subscription reactivated";
    default:
      return event.event_type.replace(/_/g, " ").toLowerCase();
  }
}

export default function SubscriptionPage() {
  const { data: subscription, isLoading: subLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => apiGet<Subscription>("/customer/subscription"),
  });

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ["subscription-audit"],
    queryFn: () =>
      apiGet<{ events: AuditEvent[]; total: number }>(
        "/customer/subscription/audit?limit=20"
      ),
  });

  if (subLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Subscription" description="Loading..." />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Subscription"
          description="No subscription found"
        />
      </div>
    );
  }

  const usagePercent = Math.round(
    (subscription.active_device_count / Math.max(subscription.device_limit, 1)) * 100
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subscription"
        description="Manage your subscription and device entitlements"
      />

      <div className="grid gap-4 md:grid-cols-2">
        {/* Plan Details Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Plan Details</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Status</span>
              <StatusBadge status={subscription.status} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Plan</span>
              <span className="text-sm font-medium">
                {subscription.plan_id || "Standard"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Term</span>
              <span className="text-sm">
                {subscription.term_start
                  ? format(new Date(subscription.term_start), "MMM d, yyyy")
                  : "—"}{" "}
                -{" "}
                {subscription.term_end
                  ? format(new Date(subscription.term_end), "MMM d, yyyy")
                  : "—"}
              </span>
            </div>
            {subscription.days_until_expiry !== null && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Expires in</span>
                <span
                  className={`text-sm font-medium ${
                    subscription.days_until_expiry <= 30
                      ? "text-orange-600"
                      : "text-green-600"
                  }`}
                >
                  {subscription.days_until_expiry} days
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Device Usage Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Device Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>
                  {subscription.active_device_count} / {subscription.device_limit} devices
                </span>
                <span className="text-muted-foreground">{usagePercent}%</span>
              </div>
              <Progress value={usagePercent} className="h-2" />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Available</span>
              <span
                className={`text-sm font-medium ${
                  subscription.devices_available <= 5
                    ? "text-orange-600"
                    : "text-green-600"
                }`}
              >
                {subscription.devices_available} devices
              </span>
            </div>
            {subscription.devices_available === 0 && (
              <p className="text-xs text-orange-600">
                Device limit reached. Remove devices or upgrade your plan to add more.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Subscription History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Subscription History</CardTitle>
        </CardHeader>
        <CardContent>
          {auditLoading ? (
            <Skeleton className="h-32" />
          ) : auditData?.events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditData?.events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>
                      <EventIcon type={event.event_type} />
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {event.event_type}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatEventDescription(event)}
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(event.event_timestamp), {
                        addSuffix: true,
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

## Route Configuration

Add to your router configuration (likely `frontend/src/App.tsx` or a routes file):

```tsx
import SubscriptionPage from "@/features/subscription/SubscriptionPage";

// In routes array:
{ path: "/subscription", element: <SubscriptionPage /> }
```

## Sidebar Entry

Modify `frontend/src/components/layout/AppSidebar.tsx`:

```tsx
import { CreditCard } from "lucide-react";

// Add to customerNav array:
{ label: "Subscription", href: "/subscription", icon: CreditCard },
```

## Dependencies

Ensure `date-fns` is installed:
```bash
cd frontend && npm install date-fns
```

## Testing

1. Navigate to /subscription as a customer
2. Verify plan details card shows correct subscription info
3. Verify device usage shows correct count and progress bar
4. Verify audit history table populates with events
5. Test different subscription statuses (ACTIVE, GRACE, etc.) show correct badges
