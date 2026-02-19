import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { type ColumnDef } from "@tanstack/react-table";
import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getEntitlements,
  listAccountTiers,
  listDevicePlans,
  listDeviceSubscriptions,
} from "@/services/api/billing";
import type { AccountTier, DevicePlan, DeviceSubscription } from "@/services/api/types";

function formatUsd(cents: number | null | undefined) {
  const c = typeof cents === "number" ? cents : 0;
  return `$${(c / 100).toFixed(2)}`;
}

function formatTerm(termStart: string, termEnd: string | null) {
  try {
    const start = new Date(termStart);
    const end = termEnd ? new Date(termEnd) : null;
    return `${format(start, "MMM d, yyyy")} – ${end ? format(end, "MMM d, yyyy") : "Open-ended"}`;
  } catch {
    return `${termStart} – ${termEnd ?? "Open-ended"}`;
  }
}

type Row = DeviceSubscription & {
  plan?: DevicePlan;
};

export default function SubscriptionPage() {
  const entitlements = useQuery({
    queryKey: ["entitlements"],
    queryFn: getEntitlements,
  });
  const tiers = useQuery({
    queryKey: ["account-tiers"],
    queryFn: listAccountTiers,
  });
  const plans = useQuery({
    queryKey: ["device-plans"],
    queryFn: listDevicePlans,
  });
  const subs = useQuery({
    queryKey: ["device-subscriptions"],
    queryFn: listDeviceSubscriptions,
  });

  const currentTier: AccountTier | undefined = useMemo(() => {
    const tierId = entitlements.data?.tier_id;
    if (!tierId) return undefined;
    return tiers.data?.tiers.find((t) => t.tier_id === tierId);
  }, [entitlements.data?.tier_id, tiers.data?.tiers]);

  const rows: Row[] = useMemo(() => {
    const planIndex = new Map<string, DevicePlan>(
      (plans.data?.plans ?? []).map((p) => [p.plan_id, p])
    );
    return (subs.data?.subscriptions ?? []).map((s) => ({
      ...s,
      plan: planIndex.get(s.plan_id),
    }));
  }, [plans.data?.plans, subs.data?.subscriptions]);

  const deviceTotalCents = useMemo(() => {
    return rows.reduce((sum, r) => sum + (r.plan?.monthly_price_cents ?? 0), 0);
  }, [rows]);

  const accountCents = currentTier?.monthly_price_cents ?? 0;

  const columns: ColumnDef<Row>[] = [
    {
      accessorKey: "device_id",
      header: "Device",
      cell: ({ row }) => <span className="font-mono text-sm">{row.original.device_id}</span>,
    },
    {
      id: "plan",
      header: "Plan",
      cell: ({ row }) => {
        const plan = row.original.plan;
        return plan ? <Badge variant="outline">{plan.name}</Badge> : <Badge variant="outline">{row.original.plan_id}</Badge>;
      },
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusBadge status={row.original.status} variant="subscription" />,
    },
    {
      id: "term",
      header: "Term",
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {formatTerm(row.original.term_start, row.original.term_end)}
        </span>
      ),
    },
    {
      id: "monthly",
      header: "Monthly",
      cell: ({ row }) => <span className="text-sm">{formatUsd(row.original.plan?.monthly_price_cents ?? null)}</span>,
    },
  ];

  const loading =
    entitlements.isLoading || tiers.isLoading || plans.isLoading || subs.isLoading;

  if (loading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Subscription" description="Loading..." />
        <Skeleton className="h-28" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const tierName = entitlements.data?.tier_name ?? currentTier?.name ?? "Unassigned";
  const limits = entitlements.data?.limits ?? {};
  const support = entitlements.data?.support ?? {};

  return (
    <div className="space-y-4">
      <PageHeader
        title="Subscription"
        description="Account tier and per-device subscriptions"
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm">Account Tier</CardTitle>
            <div className="mt-1 text-sm">
              <span className="font-medium">{tierName}</span>
              {currentTier ? (
                <span className="text-muted-foreground"> · {formatUsd(currentTier.monthly_price_cents)}/month</span>
              ) : null}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {(limits.users ?? "—")} users · {(limits.alert_rules ?? "—")} alert rules ·{" "}
              {(limits.notification_channels ?? "—")} channels
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              Support: {support.level ?? "—"}
              {support.sla_uptime_pct != null ? ` · SLA: ${support.sla_uptime_pct}%` : ""}
              {support.response_time_hours != null ? ` · Response: ${support.response_time_hours}h` : ""}
            </div>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link to="/app/subscription/renew">Change Tier</Link>
          </Button>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm">Device Subscriptions</CardTitle>
            <div className="mt-1 text-xs text-muted-foreground">
              {rows.length} total
            </div>
          </div>
          <div className="text-xs text-muted-foreground">
            Monthly Total: {formatUsd(accountCents)} + {formatUsd(deviceTotalCents)} ={" "}
            {formatUsd(accountCents + deviceTotalCents)}
          </div>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={rows} />
        </CardContent>
      </Card>
    </div>
  );
}
