# 003: Subscription Renewal Workflow

## Task

Implement the customer-facing renewal workflow, including:
1. Renewal page with plan options
2. Device selection when downsizing
3. Term extension API
4. "Renew Now" button functionality

## Files to Create/Update

1. `frontend/src/features/subscription/RenewalPage.tsx` (NEW)
2. `frontend/src/features/subscription/DeviceSelectionModal.tsx` (NEW)
3. `services/ui_iot/routes/customer.py` (UPDATE - add renewal endpoint)
4. `frontend/src/app/router.tsx` (UPDATE - add route)

## 1. Renewal Page

**File:** `frontend/src/features/subscription/RenewalPage.tsx`

```tsx
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { format, addDays, addYears } from "date-fns";
import { Check, AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { apiGet, apiPost } from "@/services/api/client";
import { DeviceSelectionModal } from "./DeviceSelectionModal";

interface Subscription {
  subscription_id: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  term_end: string;
  status: string;
}

interface RenewalOption {
  id: string;
  name: string;
  device_limit: number;
  term_days: number;
  price_display: string;
  features: string[];
}

// Hardcoded plans - replace with API call to pricing service
const RENEWAL_OPTIONS: RenewalOption[] = [
  {
    id: "starter",
    name: "Starter",
    device_limit: 50,
    term_days: 365,
    price_display: "Contact Sales",
    features: ["50 devices", "1 year term", "Email support"],
  },
  {
    id: "professional",
    name: "Professional",
    device_limit: 200,
    term_days: 365,
    price_display: "Contact Sales",
    features: ["200 devices", "1 year term", "Priority support", "API access"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    device_limit: 1000,
    term_days: 365,
    price_display: "Contact Sales",
    features: ["1000 devices", "1 year term", "24/7 support", "Dedicated CSM", "Custom integrations"],
  },
];

export default function RenewalPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const subscriptionId = searchParams.get("subscription");

  const [selectedPlan, setSelectedPlan] = useState<string>("");
  const [showDeviceSelection, setShowDeviceSelection] = useState(false);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);

  // Fetch current subscription(s)
  const { data: subsData } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => apiGet<{ subscriptions: Subscription[] }>("/customer/subscriptions"),
  });

  // Find the subscription to renew (or default to first MAIN)
  const subscriptions = subsData?.subscriptions || [];
  const targetSub = subscriptionId
    ? subscriptions.find(s => s.subscription_id === subscriptionId)
    : subscriptions.find(s => s.subscription_type === "MAIN");

  const selectedOption = RENEWAL_OPTIONS.find(o => o.id === selectedPlan);

  // Check if downsizing (new limit < current device count)
  const isDownsizing = selectedOption && targetSub &&
    selectedOption.device_limit < targetSub.active_device_count;

  const devicesToRemove = isDownsizing
    ? targetSub.active_device_count - selectedOption.device_limit
    : 0;

  const renewMutation = useMutation({
    mutationFn: async () => {
      return apiPost("/customer/subscription/renew", {
        subscription_id: targetSub?.subscription_id,
        plan_id: selectedPlan,
        term_days: selectedOption?.term_days,
        new_device_limit: selectedOption?.device_limit,
        devices_to_deactivate: isDownsizing ? selectedDevices : undefined,
      });
    },
    onSuccess: () => {
      navigate("/app/subscription?renewed=true");
    },
  });

  const canProceed = selectedPlan && targetSub && (
    !isDownsizing || selectedDevices.length === devicesToRemove
  );

  if (!targetSub) {
    return (
      <div className="space-y-6">
        <PageHeader title="Renew Subscription" description="No subscription found to renew" />
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              You don't have an active subscription to renew.
            </p>
            <Button className="mt-4" onClick={() => navigate("/app/subscription")}>
              Back to Subscriptions
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Renew Subscription"
        description="Choose a plan and extend your subscription term"
      />

      {/* Current Subscription Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Current Subscription</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-mono text-sm">{targetSub.subscription_id}</p>
              <p className="text-sm text-muted-foreground">
                {targetSub.active_device_count} devices • Expires {format(new Date(targetSub.term_end), "MMM d, yyyy")}
              </p>
            </div>
            <Badge variant={targetSub.status === "ACTIVE" ? "default" : "destructive"}>
              {targetSub.status}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Plan Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Plan</CardTitle>
          <CardDescription>Choose the plan that fits your needs</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup value={selectedPlan} onValueChange={setSelectedPlan}>
            <div className="grid gap-4 md:grid-cols-3">
              {RENEWAL_OPTIONS.map((option) => (
                <Label
                  key={option.id}
                  htmlFor={option.id}
                  className={`cursor-pointer rounded-lg border p-4 ${
                    selectedPlan === option.id
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-primary/50"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{option.name}</p>
                      <p className="text-sm text-muted-foreground">{option.price_display}</p>
                    </div>
                    <RadioGroupItem value={option.id} id={option.id} />
                  </div>
                  <Separator className="my-3" />
                  <ul className="space-y-1">
                    {option.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-600" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  {option.device_limit < targetSub.active_device_count && (
                    <div className="mt-3 rounded bg-orange-50 dark:bg-orange-950 p-2">
                      <p className="text-xs text-orange-700 dark:text-orange-300 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Requires removing {targetSub.active_device_count - option.device_limit} devices
                      </p>
                    </div>
                  )}
                </Label>
              ))}
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Device Selection Warning */}
      {isDownsizing && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
              <div>
                <p className="font-medium text-orange-800 dark:text-orange-200">
                  Device Reduction Required
                </p>
                <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
                  The selected plan allows {selectedOption?.device_limit} devices, but you currently have {targetSub.active_device_count}.
                  You need to select {devicesToRemove} device(s) to deactivate.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => setShowDeviceSelection(true)}
                >
                  Select Devices to Deactivate ({selectedDevices.length}/{devicesToRemove})
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary and Action */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Renewal Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedOption ? (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Plan</span>
                <span>{selectedOption.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Device Limit</span>
                <span>{selectedOption.device_limit} devices</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">New Term End</span>
                <span>{format(addDays(new Date(), selectedOption.term_days), "MMM d, yyyy")}</span>
              </div>
              <Separator className="my-3" />
              <div className="flex justify-between font-medium">
                <span>Price</span>
                <span>{selectedOption.price_display}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select a plan to see summary</p>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate("/app/subscription")}>
          Cancel
        </Button>
        <Button
          disabled={!canProceed || renewMutation.isPending}
          onClick={() => renewMutation.mutate()}
        >
          {renewMutation.isPending ? "Processing..." : "Request Renewal"}
        </Button>
      </div>

      {/* Device Selection Modal */}
      <DeviceSelectionModal
        open={showDeviceSelection}
        onOpenChange={setShowDeviceSelection}
        subscriptionId={targetSub.subscription_id}
        requiredCount={devicesToRemove}
        selectedDevices={selectedDevices}
        onSelectionChange={setSelectedDevices}
      />
    </div>
  );
}
```

## 2. Device Selection Modal

**File:** `frontend/src/features/subscription/DeviceSelectionModal.tsx`

```tsx
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Search, AlertTriangle } from "lucide-react";
import { apiGet } from "@/services/api/client";

interface Device {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscriptionId: string;
  requiredCount: number;
  selectedDevices: string[];
  onSelectionChange: (devices: string[]) => void;
}

export function DeviceSelectionModal({
  open, onOpenChange, subscriptionId, requiredCount, selectedDevices, onSelectionChange
}: Props) {
  const [searchQuery, setSearchQuery] = useState("");

  const { data } = useQuery({
    queryKey: ["subscription-devices", subscriptionId],
    queryFn: () => apiGet<{ devices: Device[] }>(`/customer/subscriptions/${subscriptionId}`),
    enabled: open,
  });

  const devices = data?.devices || [];

  const filteredDevices = useMemo(() => {
    if (!searchQuery) return devices;
    const q = searchQuery.toLowerCase();
    return devices.filter(d =>
      d.device_id.toLowerCase().includes(q) ||
      d.site_id.toLowerCase().includes(q)
    );
  }, [devices, searchQuery]);

  const toggleDevice = (deviceId: string) => {
    if (selectedDevices.includes(deviceId)) {
      onSelectionChange(selectedDevices.filter(id => id !== deviceId));
    } else if (selectedDevices.length < requiredCount) {
      onSelectionChange([...selectedDevices, deviceId]);
    }
  };

  const isComplete = selectedDevices.length === requiredCount;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Devices to Deactivate</DialogTitle>
          <DialogDescription>
            Choose {requiredCount} device(s) that will be deactivated when you renew with the smaller plan.
            These devices will stop sending telemetry.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2 py-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search devices..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
          <Badge variant={isComplete ? "default" : "outline"}>
            {selectedDevices.length} / {requiredCount}
          </Badge>
        </div>

        <ScrollArea className="flex-1 border rounded-md">
          <div className="p-2 space-y-1">
            {filteredDevices.map((device) => {
              const isSelected = selectedDevices.includes(device.device_id);
              const isDisabled = !isSelected && selectedDevices.length >= requiredCount;
              return (
                <div
                  key={device.device_id}
                  className={`flex items-center gap-3 p-2 rounded cursor-pointer ${
                    isSelected
                      ? "bg-destructive/10 border border-destructive/20"
                      : isDisabled
                      ? "opacity-50"
                      : "hover:bg-muted"
                  }`}
                  onClick={() => !isDisabled && toggleDevice(device.device_id)}
                >
                  <Checkbox checked={isSelected} disabled={isDisabled} />
                  <div className="flex-1">
                    <div className="font-mono text-sm">{device.device_id}</div>
                    <div className="text-xs text-muted-foreground">
                      Site: {device.site_id}
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {device.status}
                  </Badge>
                </div>
              );
            })}
          </div>
        </ScrollArea>

        {isComplete && (
          <div className="rounded-md bg-orange-50 dark:bg-orange-950 p-3 text-sm">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5" />
              <div>
                <p className="font-medium text-orange-800 dark:text-orange-200">
                  {selectedDevices.length} device(s) will be deactivated
                </p>
                <p className="text-orange-700 dark:text-orange-300 text-xs mt-1">
                  These devices will stop accepting telemetry after renewal.
                </p>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => onOpenChange(false)} disabled={!isComplete}>
            Confirm Selection
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## 3. Backend Renewal Endpoint

**File:** `services/ui_iot/routes/customer.py`

Add this endpoint:

```python
from pydantic import BaseModel
from typing import Optional, List

class RenewalRequest(BaseModel):
    subscription_id: str
    plan_id: Optional[str] = None
    term_days: int = 365
    new_device_limit: Optional[int] = None
    devices_to_deactivate: Optional[List[str]] = None


@router.post("/subscription/renew")
async def request_renewal(data: RenewalRequest, request: Request):
    """
    Request subscription renewal.
    If downsizing, deactivates specified devices first.
    """
    tenant_id = get_tenant_id()
    user = get_user()
    ip, _ = get_request_metadata(request)

    pool = await get_pool()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify subscription belongs to tenant
        sub = await conn.fetchrow(
            "SELECT * FROM subscriptions WHERE subscription_id = $1 AND tenant_id = $2",
            data.subscription_id, tenant_id
        )
        if not sub:
            raise HTTPException(404, "Subscription not found")

        # If downsizing, deactivate specified devices first
        if data.devices_to_deactivate:
            required_reduction = sub['active_device_count'] - (data.new_device_limit or sub['device_limit'])
            if len(data.devices_to_deactivate) != required_reduction:
                raise HTTPException(400, f"Must select exactly {required_reduction} devices to deactivate")

            # Verify all devices belong to this subscription
            devices = await conn.fetch(
                "SELECT device_id FROM device_registry WHERE subscription_id = $1 AND device_id = ANY($2)",
                data.subscription_id, data.devices_to_deactivate
            )
            if len(devices) != len(data.devices_to_deactivate):
                raise HTTPException(400, "Some devices not found on this subscription")

            # Deactivate devices
            await conn.execute(
                """
                UPDATE device_registry
                SET status = 'INACTIVE', subscription_id = NULL, updated_at = now()
                WHERE device_id = ANY($1)
                """,
                data.devices_to_deactivate
            )

            # Update subscription device count
            await conn.execute(
                """
                UPDATE subscriptions
                SET active_device_count = active_device_count - $1
                WHERE subscription_id = $2
                """,
                len(data.devices_to_deactivate), data.subscription_id
            )

        # Calculate new term_end
        from datetime import datetime, timezone, timedelta
        new_term_end = datetime.now(timezone.utc) + timedelta(days=data.term_days)

        # Update subscription
        await conn.execute(
            """
            UPDATE subscriptions
            SET term_end = $1,
                device_limit = COALESCE($2, device_limit),
                plan_id = COALESCE($3, plan_id),
                status = 'ACTIVE',
                grace_end = NULL,
                updated_at = now()
            WHERE subscription_id = $4
            """,
            new_term_end, data.new_device_limit, data.plan_id, data.subscription_id
        )

        # Audit log
        await conn.execute(
            """
            INSERT INTO subscription_audit
                (tenant_id, event_type, actor_type, actor_id, details, ip_address)
            VALUES ($1, 'RENEWED', 'user', $2, $3, $4)
            """,
            tenant_id,
            user.get('sub') if user else None,
            json.dumps({
                'subscription_id': data.subscription_id,
                'plan_id': data.plan_id,
                'term_days': data.term_days,
                'new_device_limit': data.new_device_limit,
                'devices_deactivated': data.devices_to_deactivate,
            }),
            ip
        )

        return {
            "subscription_id": data.subscription_id,
            "renewed": True,
            "new_term_end": new_term_end.isoformat(),
            "devices_deactivated": len(data.devices_to_deactivate) if data.devices_to_deactivate else 0,
        }
```

## 4. Router Update

**File:** `frontend/src/app/router.tsx`

Add route under customer routes:

```tsx
import RenewalPage from "@/features/subscription/RenewalPage";

// In customer routes:
{ path: "subscription/renew", element: <RenewalPage /> },
```

## 5. Update Subscription Banner "Renew Now"

**File:** `frontend/src/components/layout/SubscriptionBanner.tsx`

Update the Renew Now button to navigate:

```tsx
import { useNavigate } from "react-router-dom";

// In the banner component:
const navigate = useNavigate();

// Change button onClick:
<Button
  size="sm"
  variant="outline"
  onClick={() => navigate("/app/subscription/renew")}
>
  Renew Now
</Button>
```

## Install Radio Group

If not present:
```bash
npx shadcn@latest add radio-group
```

## Verification

1. Set a subscription term_end to 7 days from now
2. Banner should show with "Renew Now" button
3. Click "Renew Now" → navigates to /app/subscription/renew
4. Select a plan smaller than current device count
5. Warning appears about device reduction
6. Click "Select Devices to Deactivate"
7. Select required devices
8. Click "Request Renewal"
9. Verify subscription term extended and devices deactivated
