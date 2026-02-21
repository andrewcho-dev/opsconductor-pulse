# Task 4: Frontend — SIM Provisioning UI + API Functions + Types

## Files
1. `frontend/src/services/api/types.ts` — Add provisioning and plan types
2. `frontend/src/services/api/carrier.ts` — Add `provisionDeviceSim()` and `listCarrierPlans()`
3. `frontend/src/features/devices/DeviceCarrierPanel.tsx` — Add provisioning UI for unlinked devices

## Context

Currently, when a device has no carrier link (`status?.linked === false`), `DeviceCarrierPanel.tsx` shows a static message: "No carrier integration linked to this device." (lines 155-166). We need to replace this with a "Provision SIM" button that opens a dialog for claiming a new SIM.

The existing file already imports everything from `@/services/api/carrier` (line 21-26), uses `@tanstack/react-query` (line 2), and has `AlertDialog` components imported (lines 10-19).

## Changes

### Step 1: Add types to `frontend/src/services/api/types.ts`

Add these interfaces after the existing `CarrierLinkRequest` interface (line 269):

```typescript
export interface CarrierProvisionRequest {
  carrier_integration_id: number;
  iccid: string;
  plan_id?: number;
}

export interface CarrierProvisionResponse {
  provisioned: boolean;
  device_id: string;
  carrier_device_id: string;
  carrier_integration_id: number;
  iccid: string;
  claim_result: Record<string, unknown>;
}

export interface CarrierPlan {
  id: number;
  name: string;
  description?: string;
  data: number; // bytes or plan-specific
  price?: number;
  [key: string]: unknown;
}

export interface CarrierPlansResponse {
  plans: CarrierPlan[];
  carrier_name: string;
  note?: string;
}
```

### Step 2: Add API functions to `frontend/src/services/api/carrier.ts`

Add the import of the new types. Update the existing import block at the top (line 2-9) to include the new types:

```typescript
import type {
  CarrierIntegration,
  CarrierIntegrationCreate,
  CarrierIntegrationUpdate,
  CarrierDeviceStatus,
  CarrierDeviceUsage,
  CarrierActionResult,
  CarrierLinkRequest,
  CarrierProvisionRequest,
  CarrierProvisionResponse,
  CarrierPlansResponse,
} from "./types";
```

Add these two functions at the end of the file (after `linkDeviceToCarrier`):

```typescript
export async function provisionDeviceSim(
  deviceId: string,
  data: CarrierProvisionRequest,
): Promise<CarrierProvisionResponse> {
  return apiPost(
    `/api/v1/customer/devices/${encodeURIComponent(deviceId)}/carrier/provision`,
    data,
  );
}

export async function listCarrierPlans(integrationId: number): Promise<CarrierPlansResponse> {
  return apiGet(`/api/v1/customer/carrier/integrations/${integrationId}/plans`);
}
```

### Step 3: Add provisioning UI to `DeviceCarrierPanel.tsx`

This is the most complex change. We need to:
1. Import new API functions and types
2. Add state for the provisioning dialog
3. Replace the static "not linked" message with a "Provision SIM" button + dialog

#### 3a. Update imports (line 1-28)

Add to the existing lucide-react import (line 4): `Plus`

```typescript
import { Pause, Play, Plus, Radio, RefreshCw, RotateCcw, XCircle } from "lucide-react";
```

Add these imports that aren't yet present:

```typescript
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
```

Update the carrier API import (line 21-26) to include the new functions:

```typescript
import {
  executeCarrierAction,
  getCarrierDiagnostics,
  getCarrierStatus,
  getCarrierUsage,
  listCarrierIntegrations,
  listCarrierPlans,
  provisionDeviceSim,
} from "@/services/api/carrier";
```

Update the types import (line 27) to include the new types:

```typescript
import type { CarrierDeviceStatus, CarrierDeviceUsage, CarrierPlansResponse } from "@/services/api/types";
```

#### 3b. Add provisioning state and queries inside the component

Inside the `DeviceCarrierPanel` component function (after line 50, the `queryClient` and `confirmAction` state), add:

```typescript
const [provisionOpen, setProvisionOpen] = useState(false);
const [selectedIntegrationId, setSelectedIntegrationId] = useState<number | null>(null);
const [iccid, setIccid] = useState("");
const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);

const integrationsQuery = useQuery({
  queryKey: ["carrier-integrations"],
  queryFn: listCarrierIntegrations,
  enabled: provisionOpen,
});

const plansQuery = useQuery({
  queryKey: ["carrier-plans", selectedIntegrationId],
  queryFn: () => listCarrierPlans(selectedIntegrationId!),
  enabled: provisionOpen && selectedIntegrationId != null,
});

const provisionMutation = useMutation({
  mutationFn: () =>
    provisionDeviceSim(deviceId, {
      carrier_integration_id: selectedIntegrationId!,
      iccid,
      plan_id: selectedPlanId ?? undefined,
    }),
  onSuccess: () => {
    toast.success("SIM provisioned successfully");
    setProvisionOpen(false);
    setIccid("");
    setSelectedIntegrationId(null);
    setSelectedPlanId(null);
    queryClient.invalidateQueries({ queryKey: ["carrier-status", deviceId] });
    queryClient.invalidateQueries({ queryKey: ["carrier-usage", deviceId] });
    queryClient.invalidateQueries({ queryKey: ["carrier-diagnostics", deviceId] });
  },
  onError: (err: any) => {
    toast.error(`Provisioning failed: ${err?.message ?? "Unknown error"}`);
  },
});
```

#### 3c. Replace the "not linked" block (lines 155-166)

Replace the existing block:

```tsx
if (status?.linked === false) {
    return (
      <div className="rounded-md border border-border p-3 space-y-3">
        <h3 className="text-sm font-medium">Carrier Integration</h3>
        <div className="text-center py-6 text-muted-foreground text-sm">
          <Radio className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p>No carrier integration linked to this device.</p>
          <p className="text-xs mt-1">Link a carrier in device settings to enable diagnostics.</p>
        </div>
      </div>
    );
  }
```

With:

```tsx
if (status?.linked === false) {
    const integrations = (integrationsQuery.data as { integrations: Array<{ id: number; display_name: string; carrier_name: string }> } | undefined)?.integrations ?? [];
    const plans = (plansQuery.data as CarrierPlansResponse | undefined)?.plans ?? [];

    return (
      <div className="rounded-md border border-border p-3 space-y-3">
        <h3 className="text-sm font-medium">Carrier Integration</h3>
        <div className="text-center py-6 text-muted-foreground text-sm">
          <Radio className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p>No carrier integration linked to this device.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => setProvisionOpen(true)}
          >
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            Provision SIM
          </Button>
        </div>

        <Dialog open={provisionOpen} onOpenChange={setProvisionOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Provision SIM Card</DialogTitle>
              <DialogDescription>
                Claim a new SIM from your carrier and link it to this device.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="prov-integration">Carrier Integration</Label>
                <Select
                  value={selectedIntegrationId?.toString() ?? ""}
                  onValueChange={(v) => {
                    setSelectedIntegrationId(Number(v));
                    setSelectedPlanId(null);
                  }}
                >
                  <SelectTrigger id="prov-integration">
                    <SelectValue placeholder="Select carrier..." />
                  </SelectTrigger>
                  <SelectContent>
                    {integrations.map((i) => (
                      <SelectItem key={i.id} value={i.id.toString()}>
                        {i.display_name} ({i.carrier_name})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="prov-iccid">ICCID</Label>
                <Input
                  id="prov-iccid"
                  placeholder="89014103211118510720"
                  value={iccid}
                  onChange={(e) => setIccid(e.target.value)}
                  maxLength={22}
                />
                <p className="text-xs text-muted-foreground">
                  The 15-22 digit number printed on the SIM card.
                </p>
              </div>

              {plans.length > 0 ? (
                <div className="space-y-2">
                  <Label htmlFor="prov-plan">Data Plan (optional)</Label>
                  <Select
                    value={selectedPlanId?.toString() ?? ""}
                    onValueChange={(v) => setSelectedPlanId(v ? Number(v) : null)}
                  >
                    <SelectTrigger id="prov-plan">
                      <SelectValue placeholder="Select plan..." />
                    </SelectTrigger>
                    <SelectContent>
                      {plans.map((p) => (
                        <SelectItem key={p.id} value={p.id.toString()}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : null}
            </div>
            <DialogFooter>
              <Button
                variant="ghost"
                onClick={() => setProvisionOpen(false)}
                disabled={provisionMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={() => provisionMutation.mutate()}
                disabled={
                  !selectedIntegrationId ||
                  iccid.length < 15 ||
                  provisionMutation.isPending
                }
              >
                {provisionMutation.isPending ? "Provisioning..." : "Provision SIM"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }
```

## Notes

- The `Select` component uses `onValueChange` (Radix pattern), not `onChange`.
- The `Dialog` component is from `@/components/ui/dialog` — verify this exists in the project. If it uses a different pattern, adjust accordingly. The existing `AlertDialog` in the file (line 10-19) confirms Radix-based dialog components are available.
- The `integrations` query only fires when the dialog is open (`enabled: provisionOpen`), to avoid unnecessary API calls.
- The `plans` query only fires when an integration is selected, to avoid errors.
- ICCID validation is minimal (length 15-22) — the backend `ProvisionRequest` Pydantic model also validates this.

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Check for the Dialog component existence:
```bash
ls frontend/src/components/ui/dialog.tsx
```

If `dialog.tsx` doesn't exist, you'll need to generate it with:
```bash
cd frontend && npx shadcn@latest add dialog
```
