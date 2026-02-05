# Task 003: App Shell — Sidebar, Header, Router, Page Stubs

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

Task 2 added Keycloak auth. Now we build the app shell — the sidebar navigation, header bar, React Router routes, and stub pages for every section. After this task, the user can navigate between all pages in the app (even though most just show a title).

**Read first**:
- `frontend/src/App.tsx` — current app with AuthProvider
- `frontend/src/services/auth/AuthProvider.tsx` — provides `useAuth()` hook
- `frontend/src/components/ui/` — available shadcn components (sidebar, button, badge, etc.)

**Navigation links to implement** (from existing Jinja2 base.html):

Customer pages:
- Dashboard → `/app/dashboard`
- Devices → `/app/devices`
- Alerts → `/app/alerts`
- Alert Rules → `/app/alert-rules`
- Webhooks → `/app/integrations/webhooks`
- SNMP → `/app/integrations/snmp`
- Email → `/app/integrations/email`
- MQTT → `/app/integrations/mqtt`

Operator pages (shown only if `isOperator` is true):
- Operator Dashboard → `/app/operator`
- Operator Devices → `/app/operator/devices`
- Audit Log → `/app/operator/audit-log`
- Settings → `/app/operator/settings`

---

## Task

### 3.1 Install React Router

```bash
cd /home/opsconductor/simcloud/frontend
npm install react-router-dom
```

### 3.2 Create page stub components

Each page gets a minimal stub that shows the page title. These will be fleshed out in later tasks.

**File**: `frontend/src/features/dashboard/DashboardPage.tsx` (NEW)

```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-muted-foreground">Dashboard content will be implemented in Phase 19.</p>
    </div>
  );
}
```

Create similar stub files for ALL these pages. Each follows the same pattern — just change the title and description text:

| File | Title | Description |
|------|-------|-------------|
| `frontend/src/features/dashboard/DashboardPage.tsx` | Dashboard | Dashboard content (Phase 19) |
| `frontend/src/features/devices/DeviceListPage.tsx` | Devices | Device list (Task 4) |
| `frontend/src/features/devices/DeviceDetailPage.tsx` | Device Detail | Device detail (Phase 20) |
| `frontend/src/features/alerts/AlertListPage.tsx` | Alerts | Alert list (Task 4) |
| `frontend/src/features/alerts/AlertRulesPage.tsx` | Alert Rules | Alert rules management (Phase 21) |
| `frontend/src/features/integrations/WebhookPage.tsx` | Webhook Integrations | Webhook management (Phase 21) |
| `frontend/src/features/integrations/SnmpPage.tsx` | SNMP Integrations | SNMP management (Phase 21) |
| `frontend/src/features/integrations/EmailPage.tsx` | Email Integrations | Email management (Phase 21) |
| `frontend/src/features/integrations/MqttPage.tsx` | MQTT Integrations | MQTT management (Phase 21) |
| `frontend/src/features/operator/OperatorDashboard.tsx` | Operator Dashboard | Operator dashboard (Phase 21) |
| `frontend/src/features/operator/OperatorDevices.tsx` | Operator Devices | All devices cross-tenant (Phase 21) |
| `frontend/src/features/operator/AuditLogPage.tsx` | Audit Log | Operator audit log (Phase 21) |
| `frontend/src/features/operator/SettingsPage.tsx` | Settings | System settings (Phase 21) |

For `DeviceDetailPage.tsx`, it should also read the device ID from the URL param:

```tsx
import { useParams } from "react-router-dom";

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Device: {deviceId}</h1>
      <p className="text-muted-foreground">Device detail with charts will be implemented in Phase 20.</p>
    </div>
  );
}
```

### 3.3 Create route definitions

**File**: `frontend/src/app/router.tsx` (NEW)

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

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to="/app/dashboard" replace /> },
        { path: "app/dashboard", element: <DashboardPage /> },
        { path: "app/devices", element: <DeviceListPage /> },
        { path: "app/devices/:deviceId", element: <DeviceDetailPage /> },
        { path: "app/alerts", element: <AlertListPage /> },
        { path: "app/alert-rules", element: <AlertRulesPage /> },
        { path: "app/integrations/webhooks", element: <WebhookPage /> },
        { path: "app/integrations/snmp", element: <SnmpPage /> },
        { path: "app/integrations/email", element: <EmailPage /> },
        { path: "app/integrations/mqtt", element: <MqttPage /> },
        // Operator routes
        { path: "app/operator", element: <OperatorDashboard /> },
        { path: "app/operator/devices", element: <OperatorDevices /> },
        { path: "app/operator/audit-log", element: <AuditLogPage /> },
        { path: "app/operator/settings", element: <SettingsPage /> },
      ],
    },
  ],
);
```

### 3.4 Create AppShell layout

**File**: `frontend/src/components/layout/AppShell.tsx` (NEW)

This is the root layout component. It renders the sidebar, header, and page content area. It uses the shadcn/ui `SidebarProvider` if available, or a custom flex layout.

```tsx
import { Outlet } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";

export default function AppShell() {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <div className="flex flex-1 flex-col">
          <AppHeader />
          <main className="flex-1 p-6 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
```

### 3.5 Create AppSidebar

**File**: `frontend/src/components/layout/AppSidebar.tsx` (NEW)

The sidebar uses shadcn/ui's Sidebar component. It shows customer navigation by default, and operator navigation when the user has an operator role.

Use icons from `lucide-react`:
- Dashboard: `LayoutDashboard`
- Devices: `Cpu`
- Alerts: `Bell`
- Alert Rules: `ShieldAlert`
- Webhooks: `Webhook`
- SNMP: `Network`
- Email: `Mail`
- MQTT: `Radio`
- Operator Dashboard: `Monitor`
- Operator Devices: `Server`
- Audit Log: `FileText`
- Settings: `Settings`

```tsx
import { useLocation, Link } from "react-router-dom";
import {
  LayoutDashboard,
  Cpu,
  Bell,
  ShieldAlert,
  Webhook,
  Network,
  Mail,
  Radio,
  Monitor,
  Server,
  FileText,
  Settings,
} from "lucide-react";
import { useAuth } from "@/services/auth/AuthProvider";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";

const customerNav = [
  { label: "Dashboard", href: "/app/dashboard", icon: LayoutDashboard },
  { label: "Devices", href: "/app/devices", icon: Cpu },
  { label: "Alerts", href: "/app/alerts", icon: Bell },
  { label: "Alert Rules", href: "/app/alert-rules", icon: ShieldAlert },
];

const integrationNav = [
  { label: "Webhooks", href: "/app/integrations/webhooks", icon: Webhook },
  { label: "SNMP", href: "/app/integrations/snmp", icon: Network },
  { label: "Email", href: "/app/integrations/email", icon: Mail },
  { label: "MQTT", href: "/app/integrations/mqtt", icon: Radio },
];

const operatorNav = [
  { label: "Overview", href: "/app/operator", icon: Monitor },
  { label: "All Devices", href: "/app/operator/devices", icon: Server },
  { label: "Audit Log", href: "/app/operator/audit-log", icon: FileText },
  { label: "Settings", href: "/app/operator/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { isOperator } = useAuth();

  function isActive(href: string) {
    if (href === "/app/dashboard") {
      return location.pathname === "/app/dashboard" || location.pathname === "/app/" || location.pathname === "/app";
    }
    return location.pathname.startsWith(href);
  }

  return (
    <Sidebar>
      <SidebarHeader className="p-4">
        <Link to="/app/dashboard" className="flex items-center gap-2 no-underline">
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

**Note on shadcn Sidebar component**: If the shadcn sidebar component was not installed in Task 1 or has a different API, adapt the code to match the installed version. The key requirements are:
- Collapsible sidebar on the left
- Three groups: Monitoring, Integrations, Operator (conditional)
- Active state highlighting based on current route
- Icons from lucide-react
- Logo/brand in the header

If the sidebar component is unavailable, implement a simple custom sidebar using `<nav>` with Tailwind classes (bg-sidebar-background, border-r border-sidebar-border, w-64, etc.).

### 3.6 Create AppHeader

**File**: `frontend/src/components/layout/AppHeader.tsx` (NEW)

The header bar shows the tenant badge, user email, and logout button. It also includes the shadcn `SidebarTrigger` for mobile.

```tsx
import { useAuth } from "@/services/auth/AuthProvider";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { Separator } from "@/components/ui/separator";

export function AppHeader() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border px-4 bg-card">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="h-6" />

      <div className="flex-1" />

      {user?.tenantId && (
        <Badge variant="secondary" className="font-mono text-xs">
          {user.tenantId}
        </Badge>
      )}

      {user?.email && (
        <span className="text-sm text-muted-foreground hidden sm:inline">
          {user.email}
        </span>
      )}

      <Button variant="ghost" size="sm" onClick={logout} title="Logout">
        <LogOut className="h-4 w-4" />
      </Button>
    </header>
  );
}
```

### 3.7 Create shared components

**File**: `frontend/src/components/shared/StatusBadge.tsx` (NEW)

```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

const statusStyles: Record<string, string> = {
  ONLINE: "bg-green-900/30 text-green-400 border-green-700",
  STALE: "bg-orange-900/30 text-orange-400 border-orange-700",
  OFFLINE: "bg-red-900/30 text-red-400 border-red-700",
  REVOKED: "bg-gray-900/30 text-gray-400 border-gray-700",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn(statusStyles[status] || "text-muted-foreground", className)}
    >
      {status}
    </Badge>
  );
}
```

**File**: `frontend/src/components/shared/SeverityBadge.tsx` (NEW)

```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SeverityBadgeProps {
  severity: number;
  className?: string;
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  let style = "text-muted-foreground";
  let label = String(severity);

  if (severity >= 5) {
    style = "bg-red-900/30 text-red-400 border-red-700";
    label = `${severity} Critical`;
  } else if (severity >= 3) {
    style = "bg-orange-900/30 text-orange-400 border-orange-700";
    label = `${severity} Warning`;
  } else {
    style = "bg-blue-900/30 text-blue-400 border-blue-700";
    label = `${severity} Info`;
  }

  return (
    <Badge variant="outline" className={cn(style, className)}>
      {label}
    </Badge>
  );
}
```

**File**: `frontend/src/components/shared/EmptyState.tsx` (NEW)

```tsx
import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {icon && <div className="mb-4 text-muted-foreground">{icon}</div>}
      <h3 className="text-lg font-medium text-foreground">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-muted-foreground max-w-md">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
```

**File**: `frontend/src/components/shared/PageHeader.tsx` (NEW)

```tsx
import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
```

**File**: `frontend/src/components/shared/index.ts` (NEW)

```typescript
export { StatusBadge } from "./StatusBadge";
export { SeverityBadge } from "./SeverityBadge";
export { EmptyState } from "./EmptyState";
export { PageHeader } from "./PageHeader";
```

### 3.8 Update App.tsx with Router

**File**: `frontend/src/App.tsx` (MODIFY)

Replace the entire content:

```tsx
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "@/services/auth/AuthProvider";
import { router } from "@/app/router";

function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}

export default App;
```

**Important**: If TypeScript complains about `RouterProvider` inside `AuthProvider` (because `createBrowserRouter` returns a router that `RouterProvider` needs), you may need to restructure slightly. The auth provider must wrap the router so all route components can access `useAuth()`. If the `createBrowserRouter` approach conflicts, switch to `<BrowserRouter>` + `<Routes>` pattern:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "@/services/auth/AuthProvider";
import AppShell from "@/components/layout/AppShell";
// ... import all page components

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/app/dashboard" replace />} />
            <Route path="app/dashboard" element={<DashboardPage />} />
            {/* ... all other routes */}
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

Choose whichever pattern compiles. Both are correct.

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/app/router.tsx` | Route definitions |
| CREATE | `frontend/src/components/layout/AppShell.tsx` | Root layout with sidebar + header + outlet |
| CREATE | `frontend/src/components/layout/AppSidebar.tsx` | Sidebar navigation |
| CREATE | `frontend/src/components/layout/AppHeader.tsx` | Header bar |
| CREATE | `frontend/src/components/shared/StatusBadge.tsx` | Device status badge |
| CREATE | `frontend/src/components/shared/SeverityBadge.tsx` | Alert severity badge |
| CREATE | `frontend/src/components/shared/EmptyState.tsx` | Empty state component |
| CREATE | `frontend/src/components/shared/PageHeader.tsx` | Page header component |
| CREATE | `frontend/src/components/shared/index.ts` | Shared component exports |
| CREATE | `frontend/src/features/dashboard/DashboardPage.tsx` | Dashboard page stub |
| CREATE | `frontend/src/features/devices/DeviceListPage.tsx` | Device list page stub |
| CREATE | `frontend/src/features/devices/DeviceDetailPage.tsx` | Device detail page stub |
| CREATE | `frontend/src/features/alerts/AlertListPage.tsx` | Alert list page stub |
| CREATE | `frontend/src/features/alerts/AlertRulesPage.tsx` | Alert rules page stub |
| CREATE | `frontend/src/features/integrations/WebhookPage.tsx` | Webhook page stub |
| CREATE | `frontend/src/features/integrations/SnmpPage.tsx` | SNMP page stub |
| CREATE | `frontend/src/features/integrations/EmailPage.tsx` | Email page stub |
| CREATE | `frontend/src/features/integrations/MqttPage.tsx` | MQTT page stub |
| CREATE | `frontend/src/features/operator/OperatorDashboard.tsx` | Operator dashboard stub |
| CREATE | `frontend/src/features/operator/OperatorDevices.tsx` | Operator devices stub |
| CREATE | `frontend/src/features/operator/AuditLogPage.tsx` | Audit log stub |
| CREATE | `frontend/src/features/operator/SettingsPage.tsx` | Settings stub |
| MODIFY | `frontend/src/App.tsx` | Add RouterProvider |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors.

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify all page stubs exist

```bash
find /home/opsconductor/simcloud/frontend/src/features -name "*.tsx" | sort
```

Should list all 13 page component files.

### Step 4: Verify shared components exist

```bash
ls /home/opsconductor/simcloud/frontend/src/components/shared/
```

Should show: StatusBadge.tsx, SeverityBadge.tsx, EmptyState.tsx, PageHeader.tsx, index.ts

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] React Router configured with all routes under `/app/`
- [ ] AppShell renders sidebar + header + outlet
- [ ] Sidebar shows Monitoring group (Dashboard, Devices, Alerts, Alert Rules)
- [ ] Sidebar shows Integrations group (Webhooks, SNMP, Email, MQTT)
- [ ] Sidebar shows Operator group only when `isOperator` is true
- [ ] Active route highlighted in sidebar
- [ ] Header shows tenant badge, user email, logout button
- [ ] SidebarTrigger for mobile toggle
- [ ] All 13 page stubs created and routable
- [ ] DeviceDetailPage reads `:deviceId` from URL params
- [ ] SharedComponents: StatusBadge, SeverityBadge, EmptyState, PageHeader
- [ ] Root `/` redirects to `/app/dashboard`
- [ ] Icons from lucide-react on all nav items
- [ ] All Python tests pass

---

## Commit

```
Add app shell with sidebar navigation and route stubs

Collapsible sidebar with Monitoring, Integrations, and Operator
groups. Header with tenant badge and user info. React Router
with 13 page stubs. Shared StatusBadge and SeverityBadge
components.

Phase 18 Task 3: App Shell
```
