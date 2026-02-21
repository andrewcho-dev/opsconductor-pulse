# 007: Frontend Code Fixes

## Priority: MEDIUM

## Issues to Fix

### 1. Fix Empty Catch Blocks

**Files with empty catch blocks (14 instances):**
- `frontend/src/services/api/client.ts` (6 instances)
- `frontend/src/features/devices/DeviceDetailPage.tsx`
- `frontend/src/features/devices/DeviceInfoCard.tsx`
- `frontend/src/components/ui/tag-input.tsx`
- Others

**Fix pattern:**
```typescript
// BEFORE:
try {
  const data = await apiGet('/endpoint');
} catch (e) {
  // Empty - silent failure
}

// AFTER:
try {
  const data = await apiGet('/endpoint');
} catch (error) {
  console.error('Failed to fetch data:', error);
  // Or use error reporting service
  // reportError(error, { context: 'fetchData' });
}
```

**For API client specifically:**
```typescript
// frontend/src/services/api/client.ts
import { toast } from '@/components/ui/use-toast';

export async function apiGet<T>(path: string): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: getHeaders(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.detail || 'Request failed');
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error(`API GET ${path} failed:`, error);
    throw new ApiError(0, 'Network error');
  }
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}
```

---

### 2. Extract Duplicate StatusBadge Component

**Problem:** StatusBadge implemented 4 times in different files.

**Fix:** Use the existing shared component.

**File:** `frontend/src/components/shared/StatusBadge.tsx` (already exists)

**Remove duplicates from:**
- `frontend/src/features/subscription/SubscriptionPage.tsx:71`
- `frontend/src/features/operator/SubscriptionDetailPage.tsx:49`
- `frontend/src/features/operator/SubscriptionsPage.tsx:65`

**Replace with import:**
```typescript
import { StatusBadge } from '@/components/shared/StatusBadge';

// If you need different color schemes, extend the shared component:
// frontend/src/components/shared/StatusBadge.tsx
interface StatusBadgeProps {
  status: string;
  variant?: 'default' | 'subscription' | 'device';
}

const colorSchemes = {
  default: {
    ACTIVE: 'bg-green-100 text-green-800',
    INACTIVE: 'bg-gray-100 text-gray-800',
    // ...
  },
  subscription: {
    ACTIVE: 'bg-green-100 text-green-800',
    TRIAL: 'bg-blue-100 text-blue-800',
    GRACE: 'bg-orange-100 text-orange-800',
    SUSPENDED: 'bg-red-100 text-red-800',
    EXPIRED: 'bg-gray-100 text-gray-800',
  },
  // ...
};

export function StatusBadge({ status, variant = 'default' }: StatusBadgeProps) {
  const colors = colorSchemes[variant];
  return <Badge className={colors[status] || 'bg-gray-100'}>{status}</Badge>;
}
```

---

### 3. Extract Duplicate formatTimestamp Function

**Problem:** formatTimestamp duplicated in 4 files.

**Fix:** Create shared utility.

**Create:** `frontend/src/lib/format.ts`
```typescript
import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';

export function formatTimestamp(
  timestamp: string | Date | null | undefined,
  formatString: string = 'MMM d, yyyy HH:mm'
): string {
  if (!timestamp) return 'N/A';

  const date = typeof timestamp === 'string' ? parseISO(timestamp) : timestamp;

  if (!isValid(date)) return 'Invalid date';

  return format(date, formatString);
}

export function formatRelativeTime(
  timestamp: string | Date | null | undefined,
  options?: { addSuffix?: boolean }
): string {
  if (!timestamp) return 'N/A';

  const date = typeof timestamp === 'string' ? parseISO(timestamp) : timestamp;

  if (!isValid(date)) return 'Invalid date';

  return formatDistanceToNow(date, { addSuffix: options?.addSuffix ?? true });
}

export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
```

**Update imports in all files:**
```typescript
// BEFORE:
const formatTimestamp = (ts: string) => { ... };

// AFTER:
import { formatTimestamp } from '@/lib/format';
```

---

### 4. Remove `any` Types

**File:** `frontend/src/features/operator/SubscriptionDetailPage.tsx`
**Lines:** 80, 241, 283, 352, 440

**Fix:** Create proper interfaces:
```typescript
// Create or update: frontend/src/services/api/types.ts

export interface SubscriptionDetail {
  subscription_id: string;
  tenant_id: string;
  tenant_name: string;
  subscription_type: 'MAIN' | 'ADDON' | 'TRIAL' | 'TEMPORARY';
  parent_subscription_id: string | null;
  device_limit: number;
  active_device_count: number;
  term_start: string;
  term_end: string;
  status: 'TRIAL' | 'ACTIVE' | 'GRACE' | 'SUSPENDED' | 'EXPIRED';
  grace_end: string | null;
  plan_id: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  devices: SubscriptionDevice[];
  child_subscriptions: ChildSubscription[];
}

export interface SubscriptionDevice {
  device_id: string;
  site_id: string;
  status: string;
  last_seen_at: string | null;
}

export interface ChildSubscription {
  subscription_id: string;
  device_limit: number;
  active_device_count: number;
  status: string;
}
```

**Update component to use types:**
```typescript
// BEFORE:
const sub = data as any;
{sub.devices.map((device: any) => ...)}

// AFTER:
const sub = data as SubscriptionDetail;
{sub.devices.map((device) => ...)}
```

---

### 5. Add Root Error Boundary

**Create:** `frontend/src/components/ErrorBoundary.tsx`

```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Report to error tracking service
    // reportError(error, { componentStack: errorInfo.componentStack });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                An unexpected error occurred. Please try refreshing the page.
              </p>
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                  {this.state.error.message}
                </pre>
              )}
              <Button onClick={this.handleReset} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh Page
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
```

**Update App.tsx:**
```typescript
import { ErrorBoundary } from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
```

---

### 6. Add Accessibility Attributes

**Priority components to update:**

**Buttons with only icons:**
```typescript
// BEFORE:
<Button variant="ghost" size="sm" onClick={handleEdit}>
  <Edit className="h-4 w-4" />
</Button>

// AFTER:
<Button
  variant="ghost"
  size="sm"
  onClick={handleEdit}
  aria-label="Edit subscription"
>
  <Edit className="h-4 w-4" />
</Button>
```

**Form inputs:**
```typescript
// BEFORE:
<Input value={search} onChange={handleSearch} placeholder="Search..." />

// AFTER:
<Input
  value={search}
  onChange={handleSearch}
  placeholder="Search..."
  aria-label="Search devices"
  role="searchbox"
/>
```

**Tables:**
```typescript
// BEFORE:
<Table>

// AFTER:
<Table aria-label="Device list">
```

**Status indicators:**
```typescript
// BEFORE:
<Badge className="bg-green-100">ACTIVE</Badge>

// AFTER:
<Badge className="bg-green-100" role="status" aria-label="Status: Active">
  ACTIVE
</Badge>
```

---

### 7. Remove Unused Zustand Stores

**Check usage first:**
```bash
grep -rn "useDeviceStore\|useAlertStore" frontend/src/
```

**If unused, remove:**
- `frontend/src/stores/device-store.ts`
- `frontend/src/stores/alert-store.ts`

**If needed, document their purpose or integrate them:**
```typescript
// If keeping, add documentation:
/**
 * Device store for local state management.
 * Used for optimistic updates and offline support.
 * Server state is managed by React Query.
 */
export const useDeviceStore = create<DeviceStore>(...);
```

---

### 8. Remove console.log Statements

**File:** `frontend/src/features/devices/DeviceEditModal.tsx:95`

```typescript
// REMOVE:
console.log("Geocode response:", result);

// If needed for debugging, use conditional:
if (import.meta.env.DEV) {
  console.log("Geocode response:", result);
}
```

**Search and remove all debug logs:**
```bash
grep -rn "console.log" frontend/src/
```

---

### 9. Standardize Error Display

**Create:** `frontend/src/components/shared/ErrorMessage.tsx`

```typescript
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ErrorMessageProps {
  error: Error | unknown;
  title?: string;
}

export function ErrorMessage({ error, title = 'Error' }: ErrorMessageProps) {
  const message = error instanceof Error
    ? error.message
    : typeof error === 'string'
    ? error
    : 'An unexpected error occurred';

  return (
    <Alert variant="destructive">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

// Usage:
{mutation.isError && <ErrorMessage error={mutation.error} title="Failed to save" />}
```

---

### 10. Split Large Component Files

**Target files over 400 lines:**

**SubscriptionDetailPage.tsx (521 lines):**
Split into:
- `SubscriptionDetailPage.tsx` - Main page component
- `SubscriptionInfoCards.tsx` - Info card components
- `SubscriptionDeviceList.tsx` - Device list table
- `EditSubscriptionDialog.tsx` - Edit dialog
- `StatusChangeDialog.tsx` - Status change dialog

**DeviceListPage.tsx (437 lines):**
Split into:
- `DeviceListPage.tsx` - Main page
- `DeviceTable.tsx` - Table component
- `DeviceFilters.tsx` - Filter controls
- `DeviceActions.tsx` - Action buttons

---

## Verification

```bash
# TypeScript check
cd frontend && npm run type-check

# Lint check
npm run lint

# Build check
npm run build

# Run tests (after adding test infrastructure)
npm test
```

## Files Changed

- `frontend/src/services/api/client.ts`
- `frontend/src/services/api/types.ts`
- `frontend/src/lib/format.ts` (NEW)
- `frontend/src/components/ErrorBoundary.tsx` (NEW)
- `frontend/src/components/shared/StatusBadge.tsx`
- `frontend/src/components/shared/ErrorMessage.tsx` (NEW)
- `frontend/src/features/operator/SubscriptionDetailPage.tsx`
- `frontend/src/features/operator/SubscriptionsPage.tsx`
- `frontend/src/features/subscription/SubscriptionPage.tsx`
- `frontend/src/features/devices/DeviceListPage.tsx`
- `frontend/src/features/devices/DeviceEditModal.tsx`
- `frontend/src/App.tsx`
- Various component files (accessibility updates)
