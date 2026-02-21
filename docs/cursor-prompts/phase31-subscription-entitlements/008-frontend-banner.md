# 008: Frontend Subscription Status Banner

## Task

Create a subscription status banner component that displays warnings about subscription expiry, grace period, or suspension.

## File to Create

`frontend/src/components/layout/SubscriptionBanner.tsx`

## Component Requirements

### Banner States

1. **Yellow Warning** (expiring soon - 30 days or less):
   - "Your subscription expires in X days. Renew to avoid service interruption."

2. **Orange Warning** (grace period):
   - "Grace period active. Renew by [date] to avoid suspension."

3. **Red Error** (suspended):
   - "Subscription suspended. Contact support to restore access."

4. **No banner** for:
   - TRIAL or ACTIVE with 30+ days remaining
   - Operator users (they don't have subscriptions)

### Implementation

```tsx
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, AlertCircle, XCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/services/auth/AuthProvider";
import { apiGet } from "@/services/api/client";

interface SubscriptionStatus {
  status: string;
  days_until_expiry: number | null;
  grace_end: string | null;
  term_end: string | null;
}

async function fetchSubscription(): Promise<SubscriptionStatus> {
  return apiGet("/customer/subscription");
}

export function SubscriptionBanner() {
  const { isOperator, isCustomer } = useAuth();

  const { data: subscription } = useQuery({
    queryKey: ["subscription-status"],
    queryFn: fetchSubscription,
    enabled: isCustomer,
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
    staleTime: 60 * 1000,
  });

  // Don't show for operators
  if (isOperator || !isCustomer) {
    return null;
  }

  // No subscription data yet
  if (!subscription) {
    return null;
  }

  const { status, days_until_expiry, grace_end, term_end } = subscription;

  // Suspended - red banner
  if (status === "SUSPENDED" || status === "EXPIRED") {
    return (
      <Alert variant="destructive" className="rounded-none border-x-0 border-t-0">
        <XCircle className="h-4 w-4" />
        <AlertDescription className="flex items-center justify-between">
          <span>
            Subscription {status.toLowerCase()}. Contact support to restore access.
          </span>
          <Button variant="outline" size="sm" className="ml-4">
            Contact Support
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // Grace period - orange banner
  if (status === "GRACE") {
    const graceDate = grace_end ? new Date(grace_end).toLocaleDateString() : "soon";
    return (
      <Alert className="rounded-none border-x-0 border-t-0 border-orange-500 bg-orange-50 dark:bg-orange-950/20">
        <AlertCircle className="h-4 w-4 text-orange-600" />
        <AlertDescription className="flex items-center justify-between text-orange-800 dark:text-orange-200">
          <span>
            Grace period active. Renew by {graceDate} to avoid suspension.
          </span>
          <Button variant="outline" size="sm" className="ml-4 border-orange-500 text-orange-700 hover:bg-orange-100">
            Renew Now
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // Expiring soon (30 days or less) - yellow banner
  if (status === "ACTIVE" && days_until_expiry !== null && days_until_expiry <= 30) {
    return (
      <Alert className="rounded-none border-x-0 border-t-0 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <AlertDescription className="flex items-center justify-between text-yellow-800 dark:text-yellow-200">
          <span>
            Your subscription expires in {days_until_expiry} day{days_until_expiry !== 1 ? "s" : ""}.
            Renew to avoid service interruption.
          </span>
          <Button variant="outline" size="sm" className="ml-4 border-yellow-500 text-yellow-700 hover:bg-yellow-100">
            Renew Now
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  // No banner needed
  return null;
}
```

## Integration

### 1. Add to Layout

Modify `frontend/src/components/layout/AppLayout.tsx` (or wherever the main layout is) to include the banner:

```tsx
import { SubscriptionBanner } from "./SubscriptionBanner";

export function AppLayout({ children }) {
  return (
    <div className="flex h-screen">
      <AppSidebar />
      <div className="flex-1 flex flex-col">
        <SubscriptionBanner />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

The banner should appear at the very top of the main content area, above any page content.

## API Service

Add the subscription API to `frontend/src/services/api/subscription.ts`:

```typescript
import { apiGet } from "./client";

export interface SubscriptionStatus {
  tenant_id: string;
  tenant_name: string;
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  term_start: string | null;
  term_end: string | null;
  days_until_expiry: number | null;
  plan_id: string | null;
  status: "TRIAL" | "ACTIVE" | "GRACE" | "SUSPENDED" | "EXPIRED";
  grace_end: string | null;
}

export async function getSubscription(): Promise<SubscriptionStatus> {
  return apiGet("/customer/subscription");
}

export interface SubscriptionAuditEvent {
  id: number;
  event_type: string;
  event_timestamp: string;
  actor_type: string | null;
  actor_id: string | null;
  details: Record<string, unknown> | null;
}

export async function getSubscriptionAudit(
  limit = 50,
  offset = 0
): Promise<{ events: SubscriptionAuditEvent[]; total: number }> {
  return apiGet(`/customer/subscription/audit?limit=${limit}&offset=${offset}`);
}
```

## Styling Notes

- The banner is full-width with no rounded corners (fits edge-to-edge)
- Uses shadcn/ui Alert component as base
- Different color schemes for each severity level
- Responsive: on mobile, stack text and button vertically if needed
- Dark mode support via Tailwind dark: variants

## Testing

1. Set subscription status to ACTIVE with term_end in 15 days → yellow banner
2. Set status to GRACE → orange banner
3. Set status to SUSPENDED → red banner
4. Set status to ACTIVE with 60+ days → no banner
5. Log in as operator → no banner
