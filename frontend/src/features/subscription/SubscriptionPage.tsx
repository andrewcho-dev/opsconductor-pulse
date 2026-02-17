import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import {
  ChevronDown,
  ChevronUp,
  CreditCard,
  Cpu,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { apiGet } from "@/services/api/client";

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  term_start: string | null;
  term_end: string | null;
  status: string;
  description: string | null;
}

interface SubscriptionDevice {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

interface SubscriptionDetail extends Subscription {
  devices: SubscriptionDevice[];
  total_devices: number;
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
  actor_type: string | null;
  details: Record<string, unknown> | null;
}

function TypeBadge({ type }: { type: string }) {
  const variants: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800",
    ADDON: "bg-purple-100 text-purple-800",
    TRIAL: "bg-yellow-100 text-yellow-800",
    TEMPORARY: "bg-orange-100 text-orange-800",
  };
  return <Badge className={variants[type] || "bg-gray-100"}>{type}</Badge>;
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div
        className="h-2 rounded-full bg-primary"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

function SubscriptionCard({ subscription }: { subscription: Subscription }) {
  const [open, setOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["subscription-detail", subscription.subscription_id],
    queryFn: () =>
      apiGet<SubscriptionDetail>(
        `/customer/subscriptions/${subscription.subscription_id}`
      ),
    enabled: open,
  });

  const usagePercent = Math.round(
    (subscription.active_device_count / Math.max(subscription.device_limit, 1)) * 100
  );

  const daysUntilExpiry = useMemo(() => {
    if (!subscription.term_end) return null;
    const diffMs = new Date(subscription.term_end).getTime() - Date.now();
    return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  }, [subscription.term_end]);

  const deviceList = data?.devices ?? [];
  const totalDevices = data?.total_devices ?? deviceList.length;
  const visibleDevices = deviceList.slice(0, 20);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <TypeBadge type={subscription.subscription_type} />
            <StatusBadge status={subscription.status} variant="subscription" />
            <span className="text-sm text-muted-foreground font-mono">
              {subscription.subscription_id}
            </span>
          </div>
          {subscription.description && (
            <p className="text-sm text-muted-foreground">{subscription.description}</p>
          )}
        </div>
        <div className="text-right text-sm text-muted-foreground">
          {subscription.term_end
            ? format(new Date(subscription.term_end), "MMM d, yyyy")
            : "No term end"}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>
              {subscription.active_device_count} / {subscription.device_limit} devices
            </span>
            <span className="text-muted-foreground">{usagePercent}%</span>
          </div>
          <ProgressBar value={usagePercent} />
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{subscription.devices_available} available</span>
            {subscription.term_end && (
              <span
                className={
                  daysUntilExpiry !== null && daysUntilExpiry <= 30
                    ? "text-orange-600"
                    : "text-muted-foreground"
                }
              >
                Expires {formatDistanceToNow(new Date(subscription.term_end), { addSuffix: true })}
              </span>
            )}
          </div>
        </div>

        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" size="sm" className="w-full justify-between">
              <span>Devices</span>
              {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4">
            {isLoading ? (
              <Skeleton className="h-24" />
            ) : deviceList.length === 0 ? (
              <p className="text-sm text-muted-foreground">No devices assigned.</p>
            ) : (
              <div className="space-y-2">
                <Table aria-label="Subscription devices">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Device ID</TableHead>
                      <TableHead>Site</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Seen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visibleDevices.map((device) => (
                      <TableRow key={device.device_id}>
                        <TableCell className="font-mono text-sm">
                          {device.device_id}
                        </TableCell>
                        <TableCell>{device.site_id}</TableCell>
                        <TableCell>
                          <StatusBadge status={device.status} variant="device" />
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {device.last_seen_at
                            ? formatDistanceToNow(new Date(device.last_seen_at), { addSuffix: true })
                            : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {totalDevices > visibleDevices.length && (
                  <p className="text-sm text-muted-foreground">
                    Showing {visibleDevices.length} of {totalDevices} devices
                  </p>
                )}
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

export default function SubscriptionPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => apiGet<SubscriptionsResponse>("/customer/subscriptions"),
  });

  const { data: auditData, isLoading: auditLoading } = useQuery({
    queryKey: ["subscription-audit"],
    queryFn: () =>
      apiGet<{ events: AuditEvent[]; total: number }>(
        "/customer/subscription/audit?limit=20"
      ),
  });

  if (isLoading) {
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

  const subscriptions = data?.subscriptions ?? [];
  const summary = data?.summary;

  if (!subscriptions.length) {
    return (
      <div className="space-y-6">
        <PageHeader title="Subscription" description="No active subscriptions" />
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            No active subscriptions found for your account.
          </CardContent>
        </Card>
      </div>
    );
  }

  const primarySubs = subscriptions.filter((sub) => sub.subscription_type === "MAIN");
  const addonSubs = subscriptions.filter((sub) => sub.subscription_type === "ADDON");
  const otherSubs = subscriptions.filter((sub) =>
    ["TRIAL", "TEMPORARY"].includes(sub.subscription_type)
  );

  const summaryUsage =
    summary && summary.total_device_limit > 0
      ? Math.round(
          (summary.total_active_devices / summary.total_device_limit) * 100
        )
      : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subscription"
        description="Manage your subscriptions and device entitlements"
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Capacity</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>
                  {summary?.total_active_devices ?? 0} /{" "}
                  {summary?.total_device_limit ?? 0} devices
                </span>
                <span className="text-muted-foreground">{summaryUsage}%</span>
              </div>
              <ProgressBar value={summaryUsage} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Available</span>
              <span className="text-sm font-medium">
                {summary?.total_available ?? 0} devices
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Subscriptions</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Primary</span>
              <span>{primarySubs.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Add-ons</span>
              <span>{addonSubs.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Trial & Temporary</span>
              <span>{otherSubs.length}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <div className="text-sm font-semibold">Primary</div>
        {primarySubs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No primary subscriptions.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {primarySubs.map((subscription) => (
              <SubscriptionCard
                key={subscription.subscription_id}
                subscription={subscription}
              />
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div className="text-sm font-semibold">Add-ons</div>
        {addonSubs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No add-on subscriptions.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {addonSubs.map((subscription) => (
              <SubscriptionCard
                key={subscription.subscription_id}
                subscription={subscription}
              />
            ))}
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div className="text-sm font-semibold">Trial & Temporary</div>
        {otherSubs.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No trial or temporary subscriptions.
          </p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {otherSubs.map((subscription) => (
              <SubscriptionCard
                key={subscription.subscription_id}
                subscription={subscription}
              />
            ))}
          </div>
        )}
      </div>

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
            <Table aria-label="Subscription audit events">
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditData?.events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-sm">
                      {event.event_type}
                    </TableCell>
                    <TableCell className="text-sm">
                      {event.event_type.replace(/_/g, " ").toLowerCase()}
                    </TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
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
