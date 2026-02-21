# 013: Operator Subscription Management Card

## Task

Add a Subscription card to the operator tenant detail page that displays subscription info and allows editing.

## File to Modify

`frontend/src/features/operator/OperatorTenantDetailPage.tsx`

## Changes Required

### 1. Add Imports

```tsx
import { CreditCard, Calendar, Settings } from "lucide-react";
import { format } from "date-fns";
import { EditSubscriptionDialog } from "./EditSubscriptionDialog";
```

### 2. Add State for Subscription Dialog

After the existing state declarations:

```tsx
const [showSubscriptionEdit, setShowSubscriptionEdit] = useState(false);
```

### 3. Add Subscription Query

Add a new query to fetch subscription data:

```tsx
const { data: subscription, refetch: refetchSubscription } = useQuery({
  queryKey: ["tenant-subscription", tenantId],
  queryFn: async () => {
    const res = await fetch(`/operator/tenants/${tenantId}/subscription`, {
      headers: { Authorization: `Bearer ${await getToken()}` },
    });
    if (!res.ok) {
      if (res.status === 404) return null;
      throw new Error("Failed to fetch subscription");
    }
    return res.json();
  },
  enabled: !!tenantId,
});
```

Or use the apiGet pattern:

```tsx
import { apiGet } from "@/services/api/client";

const { data: subscription, refetch: refetchSubscription } = useQuery({
  queryKey: ["tenant-subscription", tenantId],
  queryFn: () => apiGet(`/operator/tenants/${tenantId}/subscription`).catch(() => null),
  enabled: !!tenantId,
});
```

### 4. Add Subscription Card

Add this card after the Activity card (inside the `grid gap-6 md:grid-cols-2` section, or as a full-width card below):

```tsx
<Card className="md:col-span-2">
  <CardHeader className="flex flex-row items-center justify-between">
    <CardTitle className="flex items-center gap-2">
      <CreditCard className="h-5 w-5" />
      Subscription
    </CardTitle>
    <Button variant="outline" size="sm" onClick={() => setShowSubscriptionEdit(true)}>
      <Settings className="mr-2 h-4 w-4" />
      Manage
    </Button>
  </CardHeader>
  <CardContent>
    {subscription ? (
      <div className="grid gap-6 md:grid-cols-3">
        {/* Status & Plan */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge
              variant={
                subscription.status === "ACTIVE"
                  ? "default"
                  : subscription.status === "GRACE"
                  ? "outline"
                  : "destructive"
              }
              className={
                subscription.status === "ACTIVE"
                  ? "bg-green-100 text-green-800"
                  : subscription.status === "GRACE"
                  ? "border-orange-500 text-orange-600"
                  : ""
              }
            >
              {subscription.status}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Plan</span>
            <span className="text-sm font-medium">{subscription.plan_id || "Standard"}</span>
          </div>
        </div>

        {/* Device Usage */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Device Limit</span>
            <span className="text-sm font-medium">{subscription.device_limit}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Active Devices</span>
            <span className="text-sm font-medium">{subscription.active_device_count}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Usage</span>
            <span className="text-sm font-medium">
              {Math.round((subscription.active_device_count / Math.max(subscription.device_limit, 1)) * 100)}%
            </span>
          </div>
        </div>

        {/* Term Dates */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Term Start</span>
            <span className="text-sm font-medium">
              {subscription.term_start
                ? format(new Date(subscription.term_start), "MMM d, yyyy")
                : "—"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Term End</span>
            <span className="text-sm font-medium">
              {subscription.term_end
                ? format(new Date(subscription.term_end), "MMM d, yyyy")
                : "—"}
            </span>
          </div>
          {subscription.grace_end && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Grace Ends</span>
              <span className="text-sm font-medium text-orange-600">
                {format(new Date(subscription.grace_end), "MMM d, yyyy")}
              </span>
            </div>
          )}
        </div>
      </div>
    ) : (
      <div className="text-sm text-muted-foreground">
        No subscription found.{" "}
        <Button
          variant="link"
          className="h-auto p-0"
          onClick={() => setShowSubscriptionEdit(true)}
        >
          Create one
        </Button>
      </div>
    )}
  </CardContent>
</Card>
```

### 5. Add EditSubscriptionDialog Component

At the bottom, before the closing `</div>`:

```tsx
<EditSubscriptionDialog
  tenantId={tenantId!}
  subscription={subscription}
  open={showSubscriptionEdit}
  onOpenChange={setShowSubscriptionEdit}
  onSaved={() => {
    refetchSubscription();
    setShowSubscriptionEdit(false);
  }}
/>
```

## Dependencies

Ensure `date-fns` is available:
```bash
cd frontend && npm install date-fns
```

## Next Step

Create the `EditSubscriptionDialog` component (see 014-operator-subscription-dialog.md).
