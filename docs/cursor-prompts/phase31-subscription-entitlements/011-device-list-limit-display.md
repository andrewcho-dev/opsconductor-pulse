# 011: Device List Page - Limit Display

## Task

Modify the device list page to show device usage against the subscription limit, and disable device creation when at limit.

## File to Modify

`frontend/src/features/devices/DeviceListPage.tsx`

## Changes Required

### 1. Fetch Subscription Data

Add a query to fetch subscription status:

```tsx
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";

interface SubscriptionStatus {
  device_limit: number;
  active_device_count: number;
  devices_available: number;
  status: string;
}

// Inside DeviceListPage component:
const { data: subscription } = useQuery({
  queryKey: ["subscription-status"],
  queryFn: () => apiGet<SubscriptionStatus>("/customer/subscription"),
});
```

### 2. Update PageHeader Description

Modify the PageHeader to show device count against limit:

```tsx
<PageHeader
  title="Devices"
  description={
    isLoading
      ? "Loading..."
      : subscription
      ? `${totalCount} of ${subscription.device_limit} devices (${subscription.devices_available} available)`
      : `${totalCount} devices in your fleet`
  }
  action={
    <Button
      disabled={subscription && subscription.devices_available === 0}
      onClick={() => setShowCreateModal(true)}
    >
      <Plus className="h-4 w-4 mr-2" />
      New Device
    </Button>
  }
/>
```

### 3. Add Device Count Badge

Add a visual indicator of device usage in the header area:

```tsx
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";

// After PageHeader, before the table:
{subscription && (
  <div className="flex items-center gap-4 py-2">
    <div className="flex-1 max-w-xs">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground">Device Usage</span>
        <span>
          {subscription.active_device_count} / {subscription.device_limit}
        </span>
      </div>
      <Progress
        value={(subscription.active_device_count / subscription.device_limit) * 100}
        className="h-1.5"
      />
    </div>

    {subscription.devices_available === 0 && (
      <Badge variant="outline" className="border-orange-500 text-orange-600">
        <AlertTriangle className="h-3 w-3 mr-1" />
        At Limit
      </Badge>
    )}

    {subscription.devices_available > 0 && subscription.devices_available <= 5 && (
      <Badge variant="outline" className="border-yellow-500 text-yellow-600">
        {subscription.devices_available} remaining
      </Badge>
    )}
  </div>
)}
```

### 4. Tooltip on Disabled Button

If using a create device button that gets disabled, add a tooltip explaining why:

```tsx
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Wrap the button:
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <span>
        <Button
          disabled={subscription?.devices_available === 0}
          onClick={() => setShowCreateModal(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          New Device
        </Button>
      </span>
    </TooltipTrigger>
    {subscription?.devices_available === 0 && (
      <TooltipContent>
        <p>Device limit reached. Remove devices or upgrade your plan.</p>
      </TooltipContent>
    )}
  </Tooltip>
</TooltipProvider>
```

### 5. Handle Subscription Status

Don't show create button if subscription is suspended:

```tsx
{subscription?.status !== 'SUSPENDED' && subscription?.status !== 'EXPIRED' && (
  // New Device button here
)}
```

## Full Updated Header Section

```tsx
<div className="space-y-4">
  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-2xl font-bold">Devices</h1>
      <p className="text-muted-foreground text-sm">
        {isLoading
          ? "Loading..."
          : subscription
          ? `${totalCount} of ${subscription.device_limit} devices`
          : `${totalCount} devices`}
      </p>
    </div>

    {subscription?.status !== 'SUSPENDED' && (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                disabled={subscription?.devices_available === 0}
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                New Device
              </Button>
            </span>
          </TooltipTrigger>
          {subscription?.devices_available === 0 && (
            <TooltipContent>
              Device limit reached
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>
    )}
  </div>

  {subscription && (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        <Progress
          value={(subscription.active_device_count / subscription.device_limit) * 100}
          className="h-2 w-32"
        />
        <span className="text-xs text-muted-foreground">
          {Math.round((subscription.active_device_count / subscription.device_limit) * 100)}%
        </span>
      </div>

      {subscription.devices_available === 0 ? (
        <Badge variant="destructive" className="text-xs">
          At Limit
        </Badge>
      ) : subscription.devices_available <= 5 ? (
        <Badge variant="outline" className="text-xs border-yellow-500 text-yellow-600">
          {subscription.devices_available} slots left
        </Badge>
      ) : null}
    </div>
  )}
</div>
```

## Required Imports

Add these imports to the file:

```tsx
import { Plus, AlertTriangle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
```

## Testing

1. With subscription at 45/50 devices → shows progress bar, "5 slots left" badge
2. With subscription at 50/50 devices → "At Limit" badge, disabled button
3. With suspended subscription → no create button visible
4. Hover on disabled button → shows tooltip "Device limit reached"
