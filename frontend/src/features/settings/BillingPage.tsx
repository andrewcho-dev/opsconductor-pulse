import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { CreditCard, ExternalLink, Loader2, Plus } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { KpiCard } from "@/components/shared/KpiCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  createCheckoutSession,
  createPortalSession,
  getBillingConfig,
  getBillingStatus,
  getEntitlements,
} from "@/services/api/billing";

export default function BillingPage({ embedded }: { embedded?: boolean }) {
  const { data: config } = useQuery({
    queryKey: ["billing-config"],
    queryFn: getBillingConfig,
  });
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
  });
  const { data: entitlements } = useQuery({
    queryKey: ["billing-entitlements"],
    queryFn: getEntitlements,
  });

  const portalMutation = useMutation({
    mutationFn: async () => {
      const resp = await createPortalSession({ return_url: window.location.href });
      window.location.href = resp.url;
    },
    onError: (err: any) => toast.error(err?.message || "Failed to open billing portal"),
  });

  const checkoutMutation = useMutation({
    mutationFn: async (priceId: string) => {
      const resp = await createCheckoutSession({
        price_id: priceId,
        success_url: `${window.location.origin}/app/billing?success=true`,
        cancel_url: `${window.location.origin}/app/billing`,
      });
      window.location.href = resp.url;
    },
    onError: (err: any) => toast.error(err?.message || "Failed to start checkout"),
  });

  const devicePlans = status?.device_plans ?? [];

  const usageRows = useMemo(() => {
    if (!entitlements) return [];
    return Object.entries(entitlements.usage ?? {}).map(([key, { current, limit }]) => {
      const label = key.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
      const pct = limit && limit > 0 ? Math.round((current / limit) * 100) : 0;
      return { key, label, current, limit: limit ?? null, percent_used: pct };
    });
  }, [entitlements]);

  if (statusLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const canManageBilling = status?.has_billing_account;
  const canSubscribe = !status?.has_billing_account && config?.stripe_configured;

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Billing" description="Manage account tier and billing limits." />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Account Tier</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">
              {entitlements?.tier_name ?? "Unassigned"}
            </Badge>
            <span className="text-muted-foreground">
              Support: {entitlements?.support?.level ?? "—"}
              {entitlements?.support?.sla_uptime_pct != null
                ? ` · SLA: ${entitlements.support.sla_uptime_pct}%`
                : ""}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            Subscriptions
          </CardTitle>
          <div className="flex gap-2">
            {canManageBilling && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => portalMutation.mutate()}
                disabled={portalMutation.isPending}
              >
                {portalMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="mr-2 h-4 w-4" />
                )}
                Manage Billing
              </Button>
            )}
            {canSubscribe && (
              <Button
                size="sm"
                onClick={() => {
                  const priceId = window.prompt("Enter Stripe price_id to subscribe:");
                  if (!priceId) return;
                  checkoutMutation.mutate(priceId);
                }}
                disabled={checkoutMutation.isPending}
              >
                {checkoutMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                Subscribe
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {devicePlans.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No active device subscriptions found.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Plan</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Monthly</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {devicePlans.map((p) => (
                  <TableRow key={p.plan_id}>
                    <TableCell>
                      <Badge variant="outline">{p.plan_name}</Badge>
                      <div className="text-xs text-muted-foreground">{p.plan_id}</div>
                    </TableCell>
                    <TableCell>{p.device_count}</TableCell>
                    <TableCell>${(p.total_monthly_price_cents / 100).toFixed(2)}</TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell className="font-medium">Total</TableCell>
                  <TableCell />
                  <TableCell className="font-medium">
                    ${((status?.total_monthly_price_cents ?? 0) / 100).toFixed(2)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

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

      <Card>
        <CardHeader>
          <CardTitle>Features</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {Object.entries(entitlements?.features ?? {}).length === 0 ? (
            <div className="text-sm text-muted-foreground">No feature data available.</div>
          ) : (
            Object.entries(entitlements?.features ?? {}).map(([key, enabled]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-muted-foreground">{key}</span>
                <Badge variant={enabled ? "default" : "outline"}>
                  {enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

