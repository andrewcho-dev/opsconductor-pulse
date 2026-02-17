import { useMemo } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { CreditCard, ExternalLink, Loader2, Plus } from "lucide-react";
import { PageHeader, StatusBadge } from "@/components/shared";
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
  createAddonCheckoutSession,
  createCheckoutSession,
  createPortalSession,
  getBillingConfig,
  getBillingStatus,
  getEntitlements,
} from "@/services/api/billing";

function TypeBadge({ type }: { type: string }) {
  const variants: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800",
    ADDON: "bg-purple-100 text-purple-800",
    TRIAL: "bg-yellow-100 text-yellow-800",
  };
  return <Badge className={variants[type] || "bg-gray-100"}>{type}</Badge>;
}

function usageColor(pct: number) {
  if (pct > 90) return "bg-status-critical";
  if (pct >= 75) return "bg-status-warning";
  return "bg-status-online";
}

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-muted">
      <div
        className={`h-2 rounded-full ${usageColor(percent)}`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}

function formatTerm(term: string | null | undefined) {
  if (!term) return "—";
  try {
    const d = new Date(term);
    return d.toLocaleDateString();
  } catch {
    return term;
  }
}

export default function BillingPage() {
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

  const addonMutation = useMutation({
    mutationFn: async (opts: { parent_subscription_id: string; price_id: string }) => {
      const resp = await createAddonCheckoutSession({
        parent_subscription_id: opts.parent_subscription_id,
        price_id: opts.price_id,
        success_url: `${window.location.origin}/app/billing?success=true`,
        cancel_url: `${window.location.origin}/app/billing`,
      });
      window.location.href = resp.url;
    },
    onError: (err: any) => toast.error(err?.message || "Failed to start add-on checkout"),
  });

  const subscriptions = status?.subscriptions ?? [];
  const tierAllocations = status?.tier_allocations ?? [];

  const tierRows = useMemo(() => {
    return tierAllocations.map((a) => {
      const pct =
        a.slot_limit > 0 ? Math.round((a.slots_used / a.slot_limit) * 100) : 0;
      return { ...a, percent_used: pct };
    });
  }, [tierAllocations]);

  const usageRows = useMemo(() => {
    if (!entitlements) return [];
    const e = entitlements.usage;
    const items: { label: string; current: number; limit: number }[] = [
      { label: "Alert Rules", current: e.alert_rules.current, limit: e.alert_rules.limit },
      {
        label: "Channels",
        current: e.notification_channels.current,
        limit: e.notification_channels.limit,
      },
      { label: "Users", current: e.users.current, limit: e.users.limit },
    ];
    return items.map((it) => ({
      ...it,
      percent_used: it.limit > 0 ? Math.round((it.current / it.limit) * 100) : 0,
    }));
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
      <PageHeader
        title="Billing"
        description="Manage subscriptions, tier allocations, and plan limits."
      />

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
          {subscriptions.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No active subscriptions found.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Term</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscriptions.map((s) => (
                  <TableRow key={s.subscription_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <TypeBadge type={s.subscription_type} />
                        <span className="text-sm font-mono text-muted-foreground">
                          {s.subscription_id}
                        </span>
                      </div>
                      {s.parent_subscription_id && (
                        <div className="text-sm text-muted-foreground">
                          Parent: {s.parent_subscription_id}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>{s.plan_id ?? "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={s.status} variant="subscription" />
                    </TableCell>
                    <TableCell>
                      {s.active_device_count} / {s.device_limit}
                    </TableCell>
                    <TableCell>
                      {formatTerm(s.term_start)} → {formatTerm(s.term_end)}
                    </TableCell>
                    <TableCell className="text-right">
                      {s.subscription_type === "MAIN" && s.status === "ACTIVE" && canManageBilling && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            const priceId = window.prompt("Enter Stripe add-on price_id:");
                            if (!priceId) return;
                            addonMutation.mutate({
                              parent_subscription_id: s.subscription_id,
                              price_id: priceId,
                            });
                          }}
                          disabled={addonMutation.isPending}
                        >
                          Add Capacity
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {tierRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Device Tier Allocations</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tier</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead className="w-[220px]">Progress</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tierRows.map((a) => (
                  <TableRow key={`${a.subscription_id}-${a.tier_id}`}>
                    <TableCell>{a.tier_display_name}</TableCell>
                    <TableCell>
                      {a.slots_used} / {a.slot_limit}{" "}
                      <span className="text-sm text-muted-foreground">
                        ({a.percent_used}%)
                      </span>
                    </TableCell>
                    <TableCell>
                      <ProgressBar percent={a.percent_used} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Resource</TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>Limit</TableHead>
                  <TableHead className="w-[220px]">Progress</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {usageRows.map((r) => (
                  <TableRow key={r.label}>
                    <TableCell>{r.label}</TableCell>
                    <TableCell>{r.current}</TableCell>
                    <TableCell>{r.limit}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex-1">
                          <ProgressBar percent={r.percent_used} />
                        </div>
                        <div className="w-12 text-right text-sm text-muted-foreground">
                          {r.percent_used}%
                        </div>
                      </div>
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

