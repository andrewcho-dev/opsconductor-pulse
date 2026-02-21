# 008: Frontend Customer Multi-Subscription View

## Task

Update the customer subscription page to show multiple subscriptions.

## File to Modify

`frontend/src/features/subscription/SubscriptionPage.tsx`

## Updated Implementation

Replace the current single-subscription view with a multi-subscription view:

```tsx
import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import {
  CreditCard, Cpu, Clock, Plus, Minus, RefreshCw, AlertTriangle, ChevronDown
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Collapsible, CollapsibleContent, CollapsibleTrigger
} from "@/components/ui/collapsible";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { apiGet } from "@/services/api/client";
import { useState } from "react";

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  parent_subscription_id: string | null;
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  term_start: string;
  term_end: string;
  status: string;
  description: string | null;
}

interface SubscriptionsResponse {
  subscriptions: Subscription[];
  summary: {
    total_device_limit: number;
    total_active_devices: number;
    total_available: number;
  };
}

interface AuditEvent {
  id: number;
  event_type: string;
  event_timestamp: string;
  details: Record<string, unknown> | null;
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    ADDON: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    TRIAL: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    TEMPORARY: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  };
  return <Badge className={colors[type] || "bg-gray-100"}>{type}</Badge>;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-800",
    TRIAL: "bg-blue-100 text-blue-800",
    GRACE: "bg-orange-100 text-orange-800",
    SUSPENDED: "bg-red-100 text-red-800",
    EXPIRED: "bg-gray-100 text-gray-800",
  };
  return <Badge className={colors[status] || "bg-gray-100"}>{status}</Badge>;
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div
        className={`h-2 rounded-full ${value >= 90 ? "bg-orange-500" : "bg-primary"}`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

function SubscriptionCard({ subscription }: { subscription: Subscription }) {
  const [expanded, setExpanded] = useState(false);
  const usagePercent = Math.round(
    (subscription.active_device_count / Math.max(subscription.device_limit, 1)) * 100
  );
  const daysUntilExpiry = Math.max(
    0,
    Math.floor((new Date(subscription.term_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  );

  // Fetch devices for this subscription when expanded
  const { data: devicesData } = useQuery({
    queryKey: ["subscription-devices", subscription.subscription_id],
    queryFn: () => apiGet(`/customer/subscriptions/${subscription.subscription_id}`),
    enabled: expanded,
  });

  return (
    <Collapsible open={expanded} onOpenChange={setExpanded}>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TypeBadge type={subscription.subscription_type} />
              <StatusBadge status={subscription.status} />
              {subscription.description && (
                <span className="text-sm text-muted-foreground">
                  {subscription.description}
                </span>
              )}
            </div>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm">
                <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} />
              </Button>
            </CollapsibleTrigger>
          </div>
          <code className="text-xs text-muted-foreground font-mono">
            {subscription.subscription_id}
          </code>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Usage Bar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>
                {subscription.active_device_count} / {subscription.device_limit} devices
              </span>
              <span className="text-muted-foreground">{usagePercent}%</span>
            </div>
            <ProgressBar value={usagePercent} />
          </div>

          {/* Term Info */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Term</span>
            <span>
              {format(new Date(subscription.term_start), "MMM d, yyyy")} —{" "}
              {format(new Date(subscription.term_end), "MMM d, yyyy")}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Expires in</span>
            <span className={daysUntilExpiry <= 30 ? "text-orange-600 font-medium" : ""}>
              {daysUntilExpiry} days
            </span>
          </div>

          {/* Expanded: Device List */}
          <CollapsibleContent>
            <div className="pt-4 border-t">
              <h4 className="text-sm font-medium mb-2">Devices on this subscription</h4>
              {devicesData?.devices?.length > 0 ? (
                <div className="max-h-48 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Device ID</TableHead>
                        <TableHead>Site</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {devicesData.devices.slice(0, 20).map((d: any) => (
                        <TableRow key={d.device_id}>
                          <TableCell className="font-mono text-xs">{d.device_id}</TableCell>
                          <TableCell>{d.site_id}</TableCell>
                          <TableCell>
                            <StatusBadge status={d.status} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {devicesData.total_devices > 20 && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Showing 20 of {devicesData.total_devices} devices
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No devices assigned yet</p>
              )}
            </div>
          </CollapsibleContent>
        </CardContent>
      </Card>
    </Collapsible>
  );
}

export default function SubscriptionPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => apiGet<SubscriptionsResponse>("/customer/subscriptions"),
  });

  const { data: auditData } = useQuery({
    queryKey: ["subscription-audit"],
    queryFn: () =>
      apiGet<{ events: AuditEvent[]; total: number }>("/customer/subscription/audit?limit=10"),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Subscriptions" description="Loading..." />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
    );
  }

  const subscriptions = data?.subscriptions || [];
  const summary = data?.summary;

  // Group by type
  const mainSubs = subscriptions.filter(s => s.subscription_type === "MAIN");
  const addonSubs = subscriptions.filter(s => s.subscription_type === "ADDON");
  const otherSubs = subscriptions.filter(s => !["MAIN", "ADDON"].includes(s.subscription_type));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subscriptions"
        description="View your subscription plans and device allocations"
      />

      {/* Summary Card */}
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Total Device Capacity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-8">
              <div>
                <div className="text-2xl font-bold">
                  {summary.total_active_devices} / {summary.total_device_limit}
                </div>
                <p className="text-sm text-muted-foreground">devices used</p>
              </div>
              <div className="flex-1">
                <ProgressBar
                  value={(summary.total_active_devices / Math.max(summary.total_device_limit, 1)) * 100}
                />
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-600">
                  {summary.total_available}
                </div>
                <p className="text-sm text-muted-foreground">available</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Subscriptions */}
      {mainSubs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Primary Subscriptions</h2>
          {mainSubs.map(sub => (
            <SubscriptionCard key={sub.subscription_id} subscription={sub} />
          ))}
        </div>
      )}

      {/* Addon Subscriptions */}
      {addonSubs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Add-on Subscriptions</h2>
          {addonSubs.map(sub => (
            <SubscriptionCard key={sub.subscription_id} subscription={sub} />
          ))}
        </div>
      )}

      {/* Trial/Temporary Subscriptions */}
      {otherSubs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Trial & Temporary</h2>
          {otherSubs.map(sub => (
            <SubscriptionCard key={sub.subscription_id} subscription={sub} />
          ))}
        </div>
      )}

      {/* No Subscriptions */}
      {subscriptions.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">No active subscriptions found.</p>
            <p className="text-sm text-muted-foreground mt-2">
              Contact your administrator to set up a subscription.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Recent Activity */}
      {auditData?.events && auditData.events.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {auditData.events.slice(0, 5).map(event => (
                <div key={event.id} className="flex items-center justify-between text-sm">
                  <span>{event.event_type.replace(/_/g, " ")}</span>
                  <span className="text-muted-foreground">
                    {formatDistanceToNow(new Date(event.event_timestamp), { addSuffix: true })}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

## Also Update SubscriptionBanner

Update `frontend/src/components/layout/SubscriptionBanner.tsx` to use the new `/customer/subscriptions` endpoint and show warnings based on any subscription's status:

- If ANY subscription is SUSPENDED → show red banner
- If ANY subscription is in GRACE → show orange banner
- If ANY active subscription expires in ≤30 days → show yellow banner
- Use the first matching subscription's details for the banner

## Required UI Components

Ensure these shadcn components are installed:
- Collapsible: `npx shadcn-ui@latest add collapsible`
