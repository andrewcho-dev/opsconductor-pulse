"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";

interface TenantRow {
  tenant_id: string;
  name: string;
}

interface TenantListResponse {
  tenants: TenantRow[];
}

interface SubscriptionRow {
  subscription_id: string;
  subscription_type: string;
}

interface SubscriptionListResponse {
  subscriptions: SubscriptionRow[];
}

interface CreateSubscriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void;
  preselectedTenantId?: string;
}

const TYPE_OPTIONS = ["MAIN", "ADDON", "TRIAL", "TEMPORARY"] as const;

export function CreateSubscriptionDialog({
  open,
  onOpenChange,
  onCreated,
  preselectedTenantId,
}: CreateSubscriptionDialogProps) {
  const [tenantId, setTenantId] = useState(preselectedTenantId ?? "");
  const [subscriptionType, setSubscriptionType] =
    useState<(typeof TYPE_OPTIONS)[number]>("MAIN");
  const [deviceLimit, setDeviceLimit] = useState("50");
  const [termDays, setTermDays] = useState("365");
  const [parentSubscriptionId, setParentSubscriptionId] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (open) {
      setTenantId(preselectedTenantId ?? "");
      setSubscriptionType("MAIN");
      setDeviceLimit("50");
      setTermDays("365");
      setParentSubscriptionId("");
      setDescription("");
      setNotes("");
    }
  }, [open, preselectedTenantId]);

  const { data: tenantData } = useQuery({
    queryKey: ["operator-tenants"],
    queryFn: () => apiGet<TenantListResponse>("/operator/tenants?status=ALL&limit=500"),
    enabled: open,
  });

  const parentQueryString = useMemo(() => {
    if (!tenantId) return "";
    const params = new URLSearchParams();
    params.set("tenant_id", tenantId);
    params.set("subscription_type", "MAIN");
    params.set("status", "ACTIVE");
    params.set("limit", "200");
    return params.toString();
  }, [tenantId]);

  const { data: parentData } = useQuery({
    queryKey: ["operator-parent-subscriptions", parentQueryString],
    queryFn: () =>
      apiGet<SubscriptionListResponse>(`/operator/subscriptions?${parentQueryString}`),
    enabled: open && subscriptionType === "ADDON" && !!tenantId,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        tenant_id: tenantId,
        subscription_type: subscriptionType,
        device_limit: Number(deviceLimit),
        description: description || undefined,
        notes: notes || undefined,
      };

      if (subscriptionType === "ADDON") {
        payload.parent_subscription_id = parentSubscriptionId || undefined;
      } else if (termDays) {
        payload.term_days = Number(termDays);
      }

      return apiPost("/operator/subscriptions", payload);
    },
    onSuccess: () => {
      onCreated?.();
    },
  });

  const tenantOptions = tenantData?.tenants ?? [];
  const parentOptions = parentData?.subscriptions ?? [];

  const canSubmit =
    tenantId &&
    deviceLimit &&
    Number(deviceLimit) > 0 &&
    (subscriptionType !== "ADDON" || parentSubscriptionId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Subscription</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <span className="text-sm font-medium">Tenant</span>
            <Select value={tenantId} onValueChange={setTenantId}>
              <SelectTrigger>
                <SelectValue placeholder="Select tenant" />
              </SelectTrigger>
              <SelectContent>
                {tenantOptions.map((tenant) => (
                  <SelectItem key={tenant.tenant_id} value={tenant.tenant_id}>
                    {tenant.name} ({tenant.tenant_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Subscription Type</span>
            <Select
              value={subscriptionType}
              onValueChange={(value) =>
                setSubscriptionType(value as typeof subscriptionType)
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {subscriptionType === "ADDON" && (
            <div className="space-y-2">
              <span className="text-sm font-medium">Parent Subscription</span>
              <Select value={parentSubscriptionId} onValueChange={setParentSubscriptionId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select parent subscription" />
                </SelectTrigger>
                <SelectContent>
                  {parentOptions.map((sub) => (
                    <SelectItem key={sub.subscription_id} value={sub.subscription_id}>
                      {sub.subscription_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <span className="text-sm font-medium">Device Limit</span>
            <Input
              type="number"
              min="1"
              value={deviceLimit}
              onChange={(event) => setDeviceLimit(event.target.value)}
            />
          </div>

          {subscriptionType !== "ADDON" && (
            <div className="space-y-2">
              <span className="text-sm font-medium">Term Length (days)</span>
              <Input
                type="number"
                min="1"
                value={termDays}
                onChange={(event) => setTermDays(event.target.value)}
              />
            </div>
          )}

          <div className="space-y-2">
            <span className="text-sm font-medium">Description</span>
            <Input
              placeholder="Optional description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Notes</span>
            <Textarea
              placeholder="Notes for audit log"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-sm text-destructive">
            {(mutation.error as Error).message}
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit || mutation.isPending}
          >
            {mutation.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
