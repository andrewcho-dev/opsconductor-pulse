"use client";

import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { Building2, Calendar, Cpu, CreditCard } from "lucide-react";
import { PageHeader, StatusBadge } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  cancelDeviceSubscription,
  fetchDeviceSubscriptions,
  updateDeviceSubscription,
} from "@/services/api/operator";
import { fetchDevicePlans } from "@/services/api/device-tiers";

export default function SubscriptionDetailPage() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [newStatus, setNewStatus] = useState<string>("");
  const [newPlanId, setNewPlanId] = useState<string>("");

  const { data: subsData, isLoading } = useQuery({
    queryKey: ["operator-device-subscriptions"],
    queryFn: () => fetchDeviceSubscriptions(),
    enabled: !!subscriptionId,
  });

  const { data: plansData } = useQuery({
    queryKey: ["operator-device-plans"],
    queryFn: () => fetchDevicePlans(),
    enabled: !!subscriptionId,
  });

  const sub = subsData?.subscriptions?.find(
    (s) => s.subscription_id === subscriptionId
  );
  const plans = plansData?.plans ?? [];

  const statusMutation = useMutation({
    mutationFn: (status: string) =>
      updateDeviceSubscription(subscriptionId!, { status }),
    onSuccess: () => {
      toast.success("Status updated");
      queryClient.invalidateQueries({ queryKey: ["operator-device-subscriptions"] });
    },
    onError: (err: Error) => toast.error(err.message || "Failed to update status"),
  });

  const planMutation = useMutation({
    mutationFn: (plan_id: string) =>
      updateDeviceSubscription(subscriptionId!, { plan_id }),
    onSuccess: () => {
      toast.success("Plan updated");
      queryClient.invalidateQueries({ queryKey: ["operator-device-subscriptions"] });
    },
    onError: (err: Error) => toast.error(err.message || "Failed to update plan"),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelDeviceSubscription(subscriptionId!),
    onSuccess: () => {
      toast.success("Subscription cancelled");
      navigate("/operator/subscriptions");
    },
    onError: (err: Error) => toast.error(err.message || "Failed to cancel"),
  });

  if (isLoading) return <div>Loading...</div>;
  if (!sub) return <div>Subscription not found</div>;

  const STATUS_OPTIONS = [
    "TRIAL",
    "ACTIVE",
    "GRACE",
    "SUSPENDED",
    "EXPIRED",
    "CANCELLED",
  ];

  const statusValue = newStatus || sub.status;
  const planValue = newPlanId || sub.plan_id;

  return (
    <div className="space-y-4">
      <PageHeader
        title={sub.subscription_id}
        description={`Device subscription for ${sub.device_id}`}
        breadcrumbs={[
          { label: "Subscriptions", href: "/operator/subscriptions" },
          { label: sub.subscription_id },
        ]}
      />

      <div className="flex items-center gap-3">
        <StatusBadge status={sub.status} variant="subscription" />
        <Badge variant="outline">{sub.plan_id}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cpu className="h-4 w-4" />
              Device
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="font-mono text-sm">{sub.device_id}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CreditCard className="h-4 w-4" />
              Plan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">{sub.plan_id}</Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4" />
              Term
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <div>
              {sub.term_start ? format(new Date(sub.term_start), "MMM d, yyyy") : "—"}
            </div>
            <div>
              {sub.term_end ? format(new Date(sub.term_end), "MMM d, yyyy") : "Open-ended"}
            </div>
            {sub.term_end && new Date(sub.term_end) > new Date() && (
              <div className="mt-1 text-xs text-muted-foreground">
                Expires{" "}
                {formatDistanceToNow(new Date(sub.term_end), { addSuffix: true })}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Building2 className="h-4 w-4" />
              Tenant
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to={`/operator/tenants/${sub.tenant_id}`}
              className="text-sm text-primary hover:underline"
            >
              {sub.tenant_id}
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Change Status</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <Select value={statusValue} onValueChange={setNewStatus}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => statusMutation.mutate(newStatus)}
            disabled={
              !newStatus || newStatus === sub.status || statusMutation.isPending
            }
          >
            {statusMutation.isPending ? "Updating..." : "Update Status"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Change Plan</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <Select value={planValue} onValueChange={setNewPlanId}>
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {plans.map((p) => (
                <SelectItem key={p.plan_id} value={p.plan_id}>
                  {p.name} (${(p.monthly_price_cents / 100).toFixed(2)}/mo)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            onClick={() => planMutation.mutate(newPlanId)}
            disabled={!newPlanId || newPlanId === sub.plan_id || planMutation.isPending}
          >
            {planMutation.isPending ? "Updating..." : "Update Plan"}
          </Button>
        </CardContent>
      </Card>

      {sub.status !== "CANCELLED" && (
        <div className="flex justify-end">
          <Button
            variant="destructive"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            {cancelMutation.isPending ? "Cancelling..." : "Cancel Subscription"}
          </Button>
        </div>
      )}
    </div>
  );
}

