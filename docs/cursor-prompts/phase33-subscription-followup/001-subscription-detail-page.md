# 001: Operator Subscription Detail Page

## Task

Implement the full subscription detail page for operators to view and manage a single subscription.

## File to Update

`frontend/src/features/operator/SubscriptionDetailPage.tsx`

## Implementation

Replace the placeholder with a full detail page:

```tsx
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import {
  ArrowLeft, Cpu, Calendar, Users, Edit, Trash2, AlertTriangle
} from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { apiGet, apiPatch } from "@/services/api/client";

// Reuse badge components from SubscriptionsPage or extract to shared
function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    MAIN: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    ADDON: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    TRIAL: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    TEMPORARY: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
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

export default function SubscriptionDetailPage() {
  const { subscriptionId } = useParams<{ subscriptionId: string }>();
  const queryClient = useQueryClient();
  const [showEdit, setShowEdit] = useState(false);
  const [showStatusChange, setShowStatusChange] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["subscription-detail", subscriptionId],
    queryFn: () => apiGet(`/operator/subscriptions/${subscriptionId}`),
    enabled: !!subscriptionId,
  });

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!data) {
    return <div>Subscription not found</div>;
  }

  const sub = data;
  const usagePercent = Math.round(
    (sub.active_device_count / Math.max(sub.device_limit, 1)) * 100
  );

  return (
    <div className="space-y-6">
      {/* Header with back link */}
      <div className="flex items-center gap-4">
        <Link to="/operator/subscriptions">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Subscriptions
          </Button>
        </Link>
      </div>

      <PageHeader
        title={sub.subscription_id}
        description={sub.description || `${sub.subscription_type} subscription for ${sub.tenant_name}`}
      />

      {/* Status and Actions Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TypeBadge type={sub.subscription_type} />
          <StatusBadge status={sub.status} />
          {sub.parent_subscription_id && (
            <span className="text-sm text-muted-foreground">
              Parent: <Link to={`/operator/subscriptions/${sub.parent_subscription_id}`} className="text-primary hover:underline font-mono">{sub.parent_subscription_id}</Link>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowEdit(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowStatusChange(true)}>
            Change Status
          </Button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              Device Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {sub.active_device_count} / {sub.device_limit}
            </div>
            <div className="h-2 mt-2 rounded-full bg-muted">
              <div
                className={`h-2 rounded-full ${usagePercent >= 90 ? "bg-orange-500" : "bg-primary"}`}
                style={{ width: `${Math.min(100, usagePercent)}%` }}
              />
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {sub.device_limit - sub.active_device_count} slots available
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Term Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              <p><span className="text-muted-foreground">Start:</span> {format(new Date(sub.term_start), "MMM d, yyyy")}</p>
              <p><span className="text-muted-foreground">End:</span> {format(new Date(sub.term_end), "MMM d, yyyy")}</p>
            </div>
            <p className="text-sm mt-2">
              {new Date(sub.term_end) > new Date() ? (
                <span>Expires {formatDistanceToNow(new Date(sub.term_end), { addSuffix: true })}</span>
              ) : (
                <span className="text-destructive">Expired {formatDistanceToNow(new Date(sub.term_end), { addSuffix: true })}</span>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Users className="h-4 w-4" />
              Tenant
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to={`/operator/tenants/${sub.tenant_id}`}
              className="text-primary hover:underline font-medium"
            >
              {sub.tenant_name}
            </Link>
            <p className="text-xs text-muted-foreground font-mono mt-1">
              {sub.tenant_id}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Child Subscriptions (for MAIN) */}
      {sub.child_subscriptions && sub.child_subscriptions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Child Subscriptions (ADDON)</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subscription ID</TableHead>
                  <TableHead>Devices</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sub.child_subscriptions.map((child: any) => (
                  <TableRow key={child.subscription_id}>
                    <TableCell>
                      <Link
                        to={`/operator/subscriptions/${child.subscription_id}`}
                        className="text-primary hover:underline font-mono text-sm"
                      >
                        {child.subscription_id}
                      </Link>
                    </TableCell>
                    <TableCell>{child.active_device_count} / {child.device_limit}</TableCell>
                    <TableCell><StatusBadge status={child.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Devices on this Subscription */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Devices ({sub.devices?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sub.devices && sub.devices.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device ID</TableHead>
                  <TableHead>Site</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Seen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sub.devices.map((device: any) => (
                  <TableRow key={device.device_id}>
                    <TableCell className="font-mono text-sm">{device.device_id}</TableCell>
                    <TableCell>{device.site_id}</TableCell>
                    <TableCell>
                      <Badge variant={device.status === "ACTIVE" ? "default" : "secondary"}>
                        {device.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {device.last_seen_at
                        ? formatDistanceToNow(new Date(device.last_seen_at), { addSuffix: true })
                        : "Never"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground">No devices assigned to this subscription.</p>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <EditSubscriptionDialog
        open={showEdit}
        onOpenChange={setShowEdit}
        subscription={sub}
        onUpdated={() => {
          queryClient.invalidateQueries({ queryKey: ["subscription-detail", subscriptionId] });
          setShowEdit(false);
        }}
      />

      {/* Status Change Dialog */}
      <StatusChangeDialog
        open={showStatusChange}
        onOpenChange={setShowStatusChange}
        subscription={sub}
        onUpdated={() => {
          queryClient.invalidateQueries({ queryKey: ["subscription-detail", subscriptionId] });
          setShowStatusChange(false);
        }}
      />
    </div>
  );
}

// Edit Dialog Component
function EditSubscriptionDialog({ open, onOpenChange, subscription, onUpdated }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscription: any;
  onUpdated: () => void;
}) {
  const [deviceLimit, setDeviceLimit] = useState(subscription.device_limit.toString());
  const [description, setDescription] = useState(subscription.description || "");
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiPatch(`/operator/subscriptions/${subscription.subscription_id}`, {
      device_limit: parseInt(deviceLimit, 10),
      description: description || null,
      notes,
    }),
    onSuccess: onUpdated,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Subscription</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Device Limit</Label>
            <Input
              type="number"
              min="1"
              value={deviceLimit}
              onChange={(e) => setDeviceLimit(e.target.value)}
            />
            {parseInt(deviceLimit, 10) < subscription.active_device_count && (
              <p className="text-sm text-destructive flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" />
                Cannot set limit below current device count ({subscription.active_device_count})
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
            />
          </div>
          <div className="space-y-2">
            <Label>Notes (required for audit)</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for this change..."
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!notes || parseInt(deviceLimit, 10) < subscription.active_device_count || mutation.isPending}
          >
            {mutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Status Change Dialog Component
function StatusChangeDialog({ open, onOpenChange, subscription, onUpdated }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subscription: any;
  onUpdated: () => void;
}) {
  const [newStatus, setNewStatus] = useState(subscription.status);
  const [notes, setNotes] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiPatch(`/operator/subscriptions/${subscription.subscription_id}`, {
      status: newStatus,
      notes,
    }),
    onSuccess: onUpdated,
  });

  const statusOptions = ["TRIAL", "ACTIVE", "GRACE", "SUSPENDED", "EXPIRED"];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Subscription Status</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="rounded-md bg-muted p-3">
            <p className="text-sm">
              Current status: <StatusBadge status={subscription.status} />
            </p>
          </div>
          <div className="space-y-2">
            <Label>New Status</Label>
            <Select value={newStatus} onValueChange={setNewStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {newStatus === "SUSPENDED" && (
            <div className="rounded-md bg-orange-50 dark:bg-orange-950 p-3 text-sm">
              <p className="font-medium text-orange-800 dark:text-orange-200">Warning</p>
              <p className="text-orange-700 dark:text-orange-300">
                Suspending will block telemetry ingest for all devices on this subscription.
              </p>
            </div>
          )}
          <div className="space-y-2">
            <Label>Notes (required for audit)</Label>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for status change..."
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!notes || newStatus === subscription.status || mutation.isPending}
            variant={newStatus === "SUSPENDED" ? "destructive" : "default"}
          >
            {mutation.isPending ? "Updating..." : `Set to ${newStatus}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

## Also Add apiPatch

If not already present in `frontend/src/services/api/client.ts`:

```typescript
export async function apiPatch<T = unknown>(path: string, body: unknown): Promise<T> {
  const response = await apiClient.patch(path, body);
  return response.data;
}
```

## Install Alert Dialog

If not present:
```bash
npx shadcn@latest add alert-dialog
```

## Verification

1. Navigate to /operator/subscriptions
2. Click on a subscription ID to open detail page
3. Verify info cards show correct data
4. Click Edit → change device limit → verify update
5. Click Change Status → set to SUSPENDED → verify warning shown
6. For MAIN subscription with ADDON children, verify child subscriptions table appears
