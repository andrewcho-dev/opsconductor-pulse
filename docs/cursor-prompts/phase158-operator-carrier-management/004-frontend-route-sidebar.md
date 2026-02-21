# Task 4: Frontend — Wire Route + Sidebar

## Files to Modify

1. `frontend/src/app/router.tsx`
2. `frontend/src/components/layout/AppSidebar.tsx`

## Part A: Add Route

### File: `frontend/src/app/router.tsx`

#### Step 1: Add import

Add this import near the other operator page imports (around lines 15-30):

```typescript
import OperatorCarriersPage from "@/features/operator/OperatorCarriersPage";
```

Check the import style — if other operator pages use `lazy()` imports, match that style. If they use direct imports (which they appear to based on the existing code), use a direct import.

#### Step 2: Add route entry

Inside the operator `children` array (around line 161, after the `account-tiers` route), add:

```typescript
{ path: "carriers", element: <OperatorCarriersPage /> },
```

Place it after `account-tiers` to keep it grouped with the tenant-management routes. The full operator children block should look like:

```typescript
children: [
  { index: true, element: <OperatorDashboard /> },
  { path: "devices", element: <OperatorDevices /> },
  { path: "tenants", element: <TenantListPage /> },
  { path: "tenant-matrix", element: <TenantHealthMatrix /> },
  { path: "tenants/:tenantId", element: <TenantDetailPage /> },
  { path: "users", element: <OperatorUsersPage /> },
  { path: "users/:userId", element: <UserDetailPage /> },
  { path: "subscriptions", element: <SubscriptionsPage /> },
  { path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
  { path: "device-plans", element: <DeviceTiersPage /> },
  { path: "account-tiers", element: <AccountTiersPage /> },
  { path: "carriers", element: <OperatorCarriersPage /> },  // ← NEW
  { path: "certificates", element: <CertificateOverviewPage /> },
  // ... rest
],
```

## Part B: Add Sidebar Entry

### File: `frontend/src/components/layout/AppSidebar.tsx`

#### Step 1: Add Radio icon import

Check the existing lucide-react import at the top of the file. Add `Radio` if it's not already imported:

```typescript
import {
  // ... existing icons ...
  Radio,
  // ... rest
} from "lucide-react";
```

#### Step 2: Add nav item

Add to the `operatorTenantNav` array (around line 101, after the "Account Tiers" entry):

```typescript
{ label: "Carrier Integrations", href: "/operator/carriers", icon: Radio },
```

The full `operatorTenantNav` should become:

```typescript
const operatorTenantNav: NavItem[] = [
  { label: "Tenants", href: "/operator/tenants", icon: Building2 },
  { label: "Health Matrix", href: "/operator/tenant-matrix", icon: LayoutGrid },
  { label: "Subscriptions", href: "/operator/subscriptions", icon: CreditCard },
  { label: "Device Plans", href: "/operator/device-plans", icon: Layers },
  { label: "Account Tiers", href: "/operator/account-tiers", icon: Shield },
  { label: "Carrier Integrations", href: "/operator/carriers", icon: Radio },  // ← NEW
];
```

## Important Notes

- The `Radio` icon from lucide-react represents wireless/signal connectivity — appropriate for carrier integrations
- The route must be under the `operator` path prefix which is guarded by `RequireOperator`
- The sidebar entry uses the `NavItem` type: `{ label: string; href: string; icon: typeof LayoutDashboard }`
- The `isActive` function in AppSidebar uses `pathname.startsWith(item.href)` — so `/operator/carriers` will correctly highlight when visiting that path

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Then manual verification:
1. Log in as operator
2. Sidebar should show "Carrier Integrations" under the "Tenants" collapsible group
3. Clicking it should navigate to `/operator/carriers`
4. The page should load without errors
