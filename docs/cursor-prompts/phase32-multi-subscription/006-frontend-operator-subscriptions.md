# 006: Operator UI for Multi-Subscription Management

## Task

Update the operator UI to manage multiple subscriptions per tenant.

## Files to Create/Modify

1. `frontend/src/features/operator/SubscriptionsPage.tsx` (NEW)
2. `frontend/src/features/operator/CreateSubscriptionDialog.tsx` (NEW)
3. `frontend/src/features/operator/OperatorTenantDetailPage.tsx` (UPDATE)
4. `frontend/src/components/layout/AppSidebar.tsx` (UPDATE - add nav)

## 1. SubscriptionsPage.tsx

List all subscriptions with filtering.

```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { Plus, Filter } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { apiGet } from "@/services/api/client";
import { CreateSubscriptionDialog } from "./CreateSubscriptionDialog";

interface Subscription {
  subscription_id: string;
  tenant_id: string;
  tenant_name: string;
  subscription_type: string;
  device_limit: number;
  active_device_count: number;
  term_end: string;
  status: string;
  description: string | null;
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800",
    ADDON: "bg-purple-100 text-purple-800",
    TRIAL: "bg-yellow-100 text-yellow-800",
    TEMPORARY: "bg-orange-100 text-orange-800",
  };
  return <Badge className={colors[type] || "bg-gray-100"}>{type}</Badge>;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-800",
    TRIAL: "bg-blue-100 text-blue-800",
    GRACE: "bg-orange-100 text-orange-800",
    SUSPENDED: "bg-red-100 text-red-800",
    EXPIRED: "bg-gray-100 text-gray-800",
  };
  return <Badge className={colors[status] || "bg-gray-100"}>{status}</Badge>;
}

export default function SubscriptionsPage() {
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [tenantFilter, setTenantFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["operator-subscriptions", typeFilter, statusFilter, tenantFilter],
    queryFn: async () => {
      let url = "/operator/subscriptions?limit=200";
      if (typeFilter !== "ALL") url += `&subscription_type=${typeFilter}`;
      if (statusFilter !== "ALL") url += `&status=${statusFilter}`;
      if (tenantFilter) url += `&tenant_id=${tenantFilter}`;
      return apiGet<{ subscriptions: Subscription[] }>(url);
    },
  });

  const subscriptions = data?.subscriptions || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subscriptions"
        description="Manage tenant subscriptions across the platform"
      />

      <div className="flex items-center gap-4">
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Types</SelectItem>
            <SelectItem value="MAIN">MAIN</SelectItem>
            <SelectItem value="ADDON">ADDON</SelectItem>
            <SelectItem value="TRIAL">TRIAL</SelectItem>
            <SelectItem value="TEMPORARY">TEMPORARY</SelectItem>
          </SelectContent>
        </Select>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Status</SelectItem>
            <SelectItem value="ACTIVE">ACTIVE</SelectItem>
            <SelectItem value="TRIAL">TRIAL</SelectItem>
            <SelectItem value="GRACE">GRACE</SelectItem>
            <SelectItem value="SUSPENDED">SUSPENDED</SelectItem>
          </SelectContent>
        </Select>

        <Input
          placeholder="Filter by tenant..."
          value={tenantFilter}
          onChange={(e) => setTenantFilter(e.target.value)}
          className="w-48"
        />

        <div className="flex-1" />

        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Subscription
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Subscription ID</TableHead>
                <TableHead>Tenant</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Devices</TableHead>
                <TableHead>Term End</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {subscriptions.map((sub) => (
                <TableRow key={sub.subscription_id}>
                  <TableCell>
                    <Link
                      to={`/operator/subscriptions/${sub.subscription_id}`}
                      className="text-primary hover:underline font-mono text-sm"
                    >
                      {sub.subscription_id}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link
                      to={`/operator/tenants/${sub.tenant_id}`}
                      className="hover:underline"
                    >
                      {sub.tenant_name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <TypeBadge type={sub.subscription_type} />
                  </TableCell>
                  <TableCell>
                    {sub.active_device_count} / {sub.device_limit}
                  </TableCell>
                  <TableCell className="text-sm">
                    {format(new Date(sub.term_end), "MMM d, yyyy")}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={sub.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <CreateSubscriptionDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        onCreated={() => {
          refetch();
          setShowCreate(false);
        }}
      />
    </div>
  );
}
```

## 2. CreateSubscriptionDialog.tsx

Dialog to create new subscriptions.

```tsx
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { apiGet, apiPost } from "@/services/api/client";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
  preselectedTenantId?: string;
}

export function CreateSubscriptionDialog({
  open, onOpenChange, onCreated, preselectedTenantId
}: Props) {
  const [tenantId, setTenantId] = useState(preselectedTenantId || "");
  const [type, setType] = useState("MAIN");
  const [deviceLimit, setDeviceLimit] = useState("50");
  const [termDays, setTermDays] = useState("365");
  const [parentId, setParentId] = useState("");
  const [description, setDescription] = useState("");
  const [notes, setNotes] = useState("");

  // Fetch tenants for dropdown
  const { data: tenantsData } = useQuery({
    queryKey: ["tenants-list"],
    queryFn: () => apiGet<{ tenants: { tenant_id: string; name: string }[] }>("/operator/tenants?limit=500"),
    enabled: open && !preselectedTenantId,
  });

  // Fetch MAIN subscriptions for ADDON parent selection
  const { data: mainSubs } = useQuery({
    queryKey: ["main-subscriptions", tenantId],
    queryFn: () => apiGet<{ subscriptions: { subscription_id: string }[] }>(
      `/operator/subscriptions?tenant_id=${tenantId}&subscription_type=MAIN&status=ACTIVE`
    ),
    enabled: open && type === "ADDON" && !!tenantId,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      return apiPost("/operator/subscriptions", {
        tenant_id: tenantId,
        subscription_type: type,
        device_limit: parseInt(deviceLimit, 10),
        term_days: type !== "ADDON" ? parseInt(termDays, 10) : undefined,
        parent_subscription_id: type === "ADDON" ? parentId : undefined,
        description: description || undefined,
        notes: notes || undefined,
      });
    },
    onSuccess: onCreated,
  });

  const handleSubmit = () => {
    if (!tenantId || !notes) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Create Subscription</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!preselectedTenantId && (
            <div className="space-y-2">
              <Label>Tenant</Label>
              <Select value={tenantId} onValueChange={setTenantId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select tenant..." />
                </SelectTrigger>
                <SelectContent>
                  {tenantsData?.tenants.map((t) => (
                    <SelectItem key={t.tenant_id} value={t.tenant_id}>
                      {t.name} ({t.tenant_id})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <Label>Subscription Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MAIN">MAIN - Primary subscription</SelectItem>
                <SelectItem value="ADDON">ADDON - Additional capacity</SelectItem>
                <SelectItem value="TRIAL">TRIAL - Evaluation period</SelectItem>
                <SelectItem value="TEMPORARY">TEMPORARY - Project/event</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {type === "ADDON" && (
            <div className="space-y-2">
              <Label>Parent Subscription (MAIN)</Label>
              <Select value={parentId} onValueChange={setParentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select parent..." />
                </SelectTrigger>
                <SelectContent>
                  {mainSubs?.subscriptions.map((s) => (
                    <SelectItem key={s.subscription_id} value={s.subscription_id}>
                      {s.subscription_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                ADDON will inherit term end date from parent
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label>Device Limit</Label>
            <Input
              type="number"
              min="1"
              value={deviceLimit}
              onChange={(e) => setDeviceLimit(e.target.value)}
            />
          </div>

          {type !== "ADDON" && (
            <div className="space-y-2">
              <Label>Term Length (days)</Label>
              <Input
                type="number"
                min="1"
                value={termDays}
                onChange={(e) => setTermDays(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {type === "TRIAL" ? "Default: 14 days" : "Default: 365 days"}
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label>Description</Label>
            <Input
              placeholder="e.g., Q4 2024 Expansion"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Notes (required for audit)</Label>
            <Textarea
              placeholder="Reason for creating this subscription..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!tenantId || !notes || mutation.isPending}
          >
            {mutation.isPending ? "Creating..." : "Create Subscription"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## 3. Update OperatorTenantDetailPage.tsx

Replace single subscription card with multi-subscription view.

```tsx
// Replace the existing Subscription card with:

<Card className="md:col-span-2">
  <CardHeader className="flex flex-row items-center justify-between">
    <CardTitle className="flex items-center gap-2">
      <CreditCard className="h-5 w-5" />
      Subscriptions
    </CardTitle>
    <Button variant="outline" size="sm" onClick={() => setShowCreateSubscription(true)}>
      <Plus className="mr-2 h-4 w-4" />
      Add Subscription
    </Button>
  </CardHeader>
  <CardContent>
    {subscriptions && subscriptions.length > 0 ? (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Devices</TableHead>
            <TableHead>Term End</TableHead>
            <TableHead>Status</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {subscriptions.map((sub) => (
            <TableRow key={sub.subscription_id}>
              <TableCell className="font-mono text-sm">{sub.subscription_id}</TableCell>
              <TableCell><TypeBadge type={sub.subscription_type} /></TableCell>
              <TableCell>{sub.active_device_count} / {sub.device_limit}</TableCell>
              <TableCell>{format(new Date(sub.term_end), "MMM d, yyyy")}</TableCell>
              <TableCell><StatusBadge status={sub.status} /></TableCell>
              <TableCell>
                <Button variant="ghost" size="sm" onClick={() => openSubscriptionEdit(sub)}>
                  Edit
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    ) : (
      <p className="text-muted-foreground">No subscriptions. Create one to enable devices.</p>
    )}
  </CardContent>
</Card>
```

## 4. Add Route and Sidebar Entry

In router.tsx, add:
```tsx
{ path: "subscriptions", element: <SubscriptionsPage /> },
{ path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
```

In AppSidebar.tsx, add to operatorNav:
```tsx
{ label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
```
