# Task 010: Fix Operator Routing — Hide Customer Pages from Operators

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

When an operator user logs in, the SPA shows customer nav items (Dashboard, Devices, Alerts, Alert Rules, Integrations) alongside operator nav items. Clicking any customer page triggers `/api/v2/*` calls that return 403 because those endpoints require `customer_admin` or `customer_viewer` role.

The operator pages (`/operator/*`) use separate `/operator/*` backend endpoints that already work correctly with the operator role. The fix is to hide customer nav from operators and redirect operators to `/operator` on login.

**Read first**:
- `frontend/src/components/layout/AppSidebar.tsx` — sidebar nav with unconditional customer sections
- `frontend/src/app/router.tsx` — index route always redirects to `/dashboard`
- `frontend/src/services/auth/AuthProvider.tsx` — `isOperator` and `isCustomer` flags

---

## Task

### 10.1 Fix sidebar — show only relevant nav items per role

**File**: `frontend/src/components/layout/AppSidebar.tsx`

Wrap the customer nav sections (Monitoring and Integrations) so they only show for non-operator users. The operator section already has `{isOperator && (...)}`.

Also add `isCustomer` to the destructured auth values and update the header link.

Change the `AppSidebar` function to:

```tsx
export function AppSidebar() {
  const location = useLocation();
  const { isOperator, isCustomer } = useAuth();

  function isActive(href: string) {
    if (href === "/dashboard") {
      return (
        location.pathname === "/dashboard" ||
        location.pathname === "/" ||
        location.pathname === ""
      );
    }
    if (href === "/operator") {
      return location.pathname === "/operator";
    }
    return location.pathname.startsWith(href);
  }

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Link to={isOperator ? "/operator" : "/dashboard"} className="flex items-center gap-2 no-underline">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Monitor className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <div className="text-sm font-bold text-sidebar-foreground">OpsConductor</div>
            <div className="text-xs text-muted-foreground">Pulse</div>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {isCustomer && (
          <SidebarGroup>
            <SidebarGroupLabel>Monitoring</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {customerNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {isCustomer && (
          <SidebarGroup>
            <SidebarGroupLabel>Integrations</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {integrationNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}

        {isOperator && (
          <SidebarGroup>
            <SidebarGroupLabel>Operator</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {operatorNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive(item.href)}>
                      <Link to={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="p-4">
        <div className="text-xs text-muted-foreground">
          OpsConductor Pulse v18
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
```

### 10.2 Fix router — redirect based on role

**File**: `frontend/src/app/router.tsx`

The router is defined statically so it can't use hooks. Create a `HomeRedirect` component that reads the auth context and redirects accordingly.

Replace the file contents with:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import AlertListPage from "@/features/alerts/AlertListPage";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import WebhookPage from "@/features/integrations/WebhookPage";
import SnmpPage from "@/features/integrations/SnmpPage";
import EmailPage from "@/features/integrations/EmailPage";
import MqttPage from "@/features/integrations/MqttPage";
import OperatorDashboard from "@/features/operator/OperatorDashboard";
import OperatorDevices from "@/features/operator/OperatorDevices";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import { useAuth } from "@/services/auth/AuthProvider";

function HomeRedirect() {
  const { isOperator } = useAuth();
  return <Navigate to={isOperator ? "/operator" : "/dashboard"} replace />;
}

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <HomeRedirect /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "devices", element: <DeviceListPage /> },
        { path: "devices/:deviceId", element: <DeviceDetailPage /> },
        { path: "alerts", element: <AlertListPage /> },
        { path: "alert-rules", element: <AlertRulesPage /> },
        { path: "integrations/webhooks", element: <WebhookPage /> },
        { path: "integrations/snmp", element: <SnmpPage /> },
        { path: "integrations/email", element: <EmailPage /> },
        { path: "integrations/mqtt", element: <MqttPage /> },
        // Operator routes
        { path: "operator", element: <OperatorDashboard /> },
        { path: "operator/devices", element: <OperatorDevices /> },
        { path: "operator/audit-log", element: <AuditLogPage /> },
        { path: "operator/settings", element: <SettingsPage /> },
      ],
    },
  ],
  { basename: "/app" }
);
```

### 10.3 Verify `isCustomer` is exported from AuthProvider

**File**: `frontend/src/services/auth/AuthProvider.tsx`

Check that `isCustomer` is available in the auth context. If the `useAuth()` hook already returns `isCustomer`, no changes needed. If not, add it to the context value.

The auth provider should compute `isCustomer` as:
```typescript
const isCustomer = role === "customer_admin" || role === "customer_viewer";
```

And include it in the context value alongside `isOperator`.

### 10.4 Rebuild frontend and restart

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
cd /home/opsconductor/simcloud/compose && docker compose restart ui
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `frontend/src/components/layout/AppSidebar.tsx` | Hide customer nav from operators, fix header link |
| MODIFY | `frontend/src/app/router.tsx` | Role-aware home redirect |
| VERIFY | `frontend/src/services/auth/AuthProvider.tsx` | Ensure `isCustomer` is in auth context (add if missing) |

---

## Test

### Step 1: Verify TypeScript compiles

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 2: Verify build succeeds

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 3: Deploy and verify

```bash
cd /home/opsconductor/simcloud/compose && docker compose restart ui
```

### Step 4: Visual verification

1. Open `https://192.168.10.53/` and log in as **operator1**
   - Should redirect to `/app/operator` (operator dashboard)
   - Sidebar should only show Operator section (Overview, All Devices, Audit Log, Settings)
   - No customer nav items (Dashboard, Devices, Alerts, etc.)

2. Open `https://192.168.10.53/` and log in as **customer1**
   - Should redirect to `/app/dashboard` (customer dashboard)
   - Sidebar should show Monitoring and Integrations sections
   - No Operator section

---

## Commit

```
Fix operator routing — hide customer pages from operator role

Operators were seeing customer nav items that call /api/v2/* endpoints
requiring customer role. Now sidebar shows only role-appropriate nav
and the index route redirects operators to /operator dashboard.
```
