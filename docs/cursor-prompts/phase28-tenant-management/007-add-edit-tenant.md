# Phase 28.7: Add Edit Tenant Functionality

## Task

Add ability to edit tenant details from the UI.

## Create Edit Dialog

**File:** `frontend/src/features/operator/EditTenantDialog.tsx`

```typescript
import { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { updateTenant, type Tenant, type TenantUpdate } from "@/services/api/tenants";

interface Props {
  tenant: Tenant | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditTenantDialog({ tenant, open, onOpenChange }: Props) {
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactName, setContactName] = useState("");
  const [plan, setPlan] = useState("standard");
  const [maxDevices, setMaxDevices] = useState(100);
  const [maxRules, setMaxRules] = useState(50);
  const [status, setStatus] = useState("ACTIVE");

  const queryClient = useQueryClient();

  // Populate form when tenant changes
  useEffect(() => {
    if (tenant) {
      setName(tenant.name);
      setContactEmail(tenant.contact_email || "");
      setContactName(tenant.contact_name || "");
      setPlan(tenant.plan);
      setMaxDevices(tenant.max_devices);
      setMaxRules(tenant.max_rules);
      setStatus(tenant.status);
    }
  }, [tenant]);

  const mutation = useMutation({
    mutationFn: (data: TenantUpdate) => updateTenant(tenant!.tenant_id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tenants-summary"] });
      queryClient.invalidateQueries({ queryKey: ["tenant-stats", tenant?.tenant_id] });
      onOpenChange(false);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      name,
      contact_email: contactEmail || undefined,
      contact_name: contactName || undefined,
      plan,
      max_devices: maxDevices,
      max_rules: maxRules,
      status,
    });
  };

  if (!tenant) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Tenant: {tenant.tenant_id}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input
                id="contact_name"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="contact_email">Contact Email</Label>
              <Input
                id="contact_email"
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="plan">Plan</Label>
              <Select value={plan} onValueChange={setPlan}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="premium">Premium</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="status">Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ACTIVE">Active</SelectItem>
                  <SelectItem value="SUSPENDED">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="max_devices">Max Devices</Label>
              <Input
                id="max_devices"
                type="number"
                value={maxDevices}
                onChange={(e) => setMaxDevices(parseInt(e.target.value) || 0)}
                min={1}
              />
            </div>
            <div>
              <Label htmlFor="max_rules">Max Rules</Label>
              <Input
                id="max_rules"
                type="number"
                value={maxRules}
                onChange={(e) => setMaxRules(parseInt(e.target.value) || 0)}
                min={1}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>

          {mutation.isError && (
            <p className="text-sm text-destructive">
              {(mutation.error as Error).message}
            </p>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

## Update Tenant List Page

**File:** `frontend/src/features/operator/OperatorTenantsPage.tsx`

Add edit button and dialog:

```typescript
import { EditTenantDialog } from "./EditTenantDialog";
import { Pencil } from "lucide-react";

// Add state
const [editTenant, setEditTenant] = useState<Tenant | null>(null);

// Add edit button in the actions column (next to delete)
<Button
  variant="ghost"
  size="icon"
  onClick={() => setEditTenant(tenant)}
>
  <Pencil className="h-4 w-4" />
</Button>

// Add dialog at bottom of component (before closing div)
<EditTenantDialog
  tenant={editTenant}
  open={!!editTenant}
  onOpenChange={(open) => !open && setEditTenant(null)}
/>
```

Note: The tenant list uses `TenantSummary` type which doesn't have all fields. You'll need to either:
1. Fetch full tenant data when edit is clicked, OR
2. Expand the summary endpoint to include all fields

**Option 1 - Fetch on edit click:**
```typescript
const handleEdit = async (tenantId: string) => {
  const fullTenant = await fetchTenant(tenantId);
  setEditTenant(fullTenant);
};
```

## Update Tenant Detail Page

**File:** `frontend/src/features/operator/OperatorTenantDetailPage.tsx`

Add edit button in the header area:

```typescript
import { useState } from "react";
import { EditTenantDialog } from "./EditTenantDialog";
import { Pencil } from "lucide-react";
import { fetchTenant } from "@/services/api/tenants";

// Add state
const [showEdit, setShowEdit] = useState(false);
const [fullTenant, setFullTenant] = useState<Tenant | null>(null);

// Fetch full tenant for editing
const handleEditClick = async () => {
  const tenant = await fetchTenant(tenantId!);
  setFullTenant(tenant);
  setShowEdit(true);
};

// Add edit button near the status badge
<Button variant="outline" size="sm" onClick={handleEditClick}>
  <Pencil className="mr-2 h-4 w-4" />
  Edit Tenant
</Button>

// Add dialog
<EditTenantDialog
  tenant={fullTenant}
  open={showEdit}
  onOpenChange={setShowEdit}
/>
```

## Rebuild and Test

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cp -r dist/* ../services/ui_iot/spa/
cd ../compose && docker compose restart ui
```

Verify:
1. Pencil icon appears in tenant list actions
2. "Edit Tenant" button on detail page
3. Edit dialog opens with current values
4. Changes save successfully

## Files

| Action | File |
|--------|------|
| CREATE | `frontend/src/features/operator/EditTenantDialog.tsx` |
| MODIFY | `frontend/src/features/operator/OperatorTenantsPage.tsx` |
| MODIFY | `frontend/src/features/operator/OperatorTenantDetailPage.tsx` |
