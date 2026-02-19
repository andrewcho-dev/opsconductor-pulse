import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";

import { PageHeader } from "@/components/shared";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { getErrorMessage } from "@/lib/errors";
import {
  createCheckoutSession,
  getEntitlements,
  listAccountTiers,
  listDevicePlans,
} from "@/services/api/billing";
import type { AccountTier, DevicePlan } from "@/services/api/types";

function formatUsd(cents: number | null | undefined) {
  const c = typeof cents === "number" ? cents : 0;
  return `$${(c / 100).toFixed(2)}`;
}

function renderKeyValue(label: string, value: string) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span>{value}</span>
    </div>
  );
}

function TierCard({
  tier,
  isCurrent,
  onSelect,
}: {
  tier: AccountTier;
  isCurrent: boolean;
  onSelect: () => void;
}) {
  return (
    <Card className={isCurrent ? "border-primary bg-primary/5" : ""}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>{tier.name}</span>
          {isCurrent ? <Badge variant="outline">Current</Badge> : null}
        </CardTitle>
        <CardDescription>
          {tier.description} · {formatUsd(tier.monthly_price_cents)}/month
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {renderKeyValue("Users", String(tier.limits.users ?? "—"))}
        {renderKeyValue("Alert rules", String(tier.limits.alert_rules ?? "—"))}
        {renderKeyValue("Channels", String(tier.limits.notification_channels ?? "—"))}
        <Separator className="my-2" />
        <div className="grid gap-1 text-xs">
          {Object.entries(tier.features ?? {}).slice(0, 6).map(([key, enabled]) => (
            <div key={key} className="flex items-center gap-2">
              <Check className={`h-3 w-3 ${enabled ? "text-green-600" : "text-muted-foreground"}`} />
              <span className={enabled ? "" : "text-muted-foreground"}>{key}</span>
            </div>
          ))}
        </div>
        <div className="pt-2">
          <Button size="sm" variant={isCurrent ? "outline" : "default"} onClick={onSelect}>
            {isCurrent ? "Selected" : "Select"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function PlanCard({
  plan,
  onSelect,
}: {
  plan: DevicePlan;
  onSelect: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-2">
          <span>{plan.name}</span>
          <Badge variant="outline">{formatUsd(plan.monthly_price_cents)}/mo</Badge>
        </CardTitle>
        <CardDescription>{plan.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {renderKeyValue("Sensors", String(plan.limits.sensors ?? "—"))}
        {renderKeyValue("Retention", `${plan.limits.data_retention_days ?? "—"} days`)}
        {renderKeyValue("Telemetry", `${plan.limits.telemetry_rate_per_minute ?? "—"} msg/min`)}
        <div className="pt-2">
          <Button size="sm" variant="outline" onClick={onSelect}>
            Select
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function RenewalPage() {
  const navigate = useNavigate();

  const entitlements = useQuery({ queryKey: ["entitlements"], queryFn: getEntitlements });
  const tiers = useQuery({ queryKey: ["account-tiers"], queryFn: listAccountTiers });
  const plans = useQuery({ queryKey: ["device-plans"], queryFn: listDevicePlans });

  const checkoutMutation = useMutation({
    mutationFn: async (priceId: string) => {
      const resp = await createCheckoutSession({
        price_id: priceId,
        success_url: `${window.location.origin}/app/subscription?success=true`,
        cancel_url: `${window.location.origin}/app/subscription/renew`,
      });
      window.location.href = resp.url;
    },
    onError: (err: Error) => toast.error(getErrorMessage(err) || "Failed to start checkout"),
  });

  return (
    <div className="space-y-4">
      <PageHeader
        title="Upgrade"
        description="Choose an account tier and device plan options"
      />

      <Card>
        <CardHeader>
          <CardTitle>Account Tier Selection</CardTitle>
          <CardDescription>Account-level limits and features for your tenant</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {(tiers.data?.tiers ?? []).map((tier) => (
              <TierCard
                key={tier.tier_id}
                tier={tier}
                isCurrent={tier.tier_id === entitlements.data?.tier_id}
                onSelect={() => {
                  const priceId = window.prompt("Enter Stripe price_id for this tier:");
                  if (!priceId) return;
                  checkoutMutation.mutate(priceId);
                }}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Device Plan Selection</CardTitle>
          <CardDescription>Device-level limits and features (applied per device)</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {(plans.data?.plans ?? []).map((plan) => (
              <PlanCard
                key={plan.plan_id}
                plan={plan}
                onSelect={() => {
                  const priceId = window.prompt("Enter Stripe price_id for this device plan:");
                  if (!priceId) return;
                  checkoutMutation.mutate(priceId);
                }}
              />
            ))}
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Device plans are assigned per device from the device detail page.
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => navigate("/subscription")}>
          Back
        </Button>
      </div>
    </div>
  );
}
