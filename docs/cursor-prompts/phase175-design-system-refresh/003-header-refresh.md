# Task 3: Header Refresh

## Objective

Transform AppHeader into a clean, EMQX-style top bar: sidebar trigger + breadcrumbs on the left, search + notification bell + user avatar dropdown on the right. Remove the raw email/logout buttons and tenant badge.

## Files to Modify

- `frontend/src/components/layout/AppHeader.tsx` — complete rewrite
- `frontend/src/components/shared/PageHeader.tsx` — remove breadcrumbs (moved to header)

## Current State

### AppHeader.tsx (lines 49-97)

Current layout: `SidebarTrigger | separator | flex spacer | [search button, ConnectionStatus, ThemeToggle] | tenant badge | email text | logout button`

Problems:
- Raw email text and logout button look unprofessional
- Tenant badge is developer-facing info that shouldn't be prominent
- No notification bell
- No user avatar
- No breadcrumbs in the header
- ConnectionStatus indicator takes up space but isn't critical

### PageHeader.tsx (lines 1-44)

Currently renders breadcrumbs above the page title. These should move to the header bar for consistent navigation context (like EMQX's breadcrumb bar in the header).

## Changes

### AppHeader.tsx — Complete Rewrite

Replace the entire component with a clean EMQX-inspired layout.

#### New imports needed:

```tsx
import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/services/auth/AuthProvider";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ConnectionStatus } from "@/components/shared/ConnectionStatus";
import { useUIStore } from "@/stores/ui-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Bell, Search, Sun, Moon, Monitor, LogOut, UserCircle, Building2, ChevronRight } from "lucide-react";
import { fetchAlerts } from "@/services/api/alerts";
```

#### Breadcrumb helper

Add a `useBreadcrumbs` helper that derives breadcrumbs from the current route path. This replaces the per-page breadcrumb pattern:

```tsx
function useBreadcrumbs(): { label: string; href?: string }[] {
  const location = useLocation();
  const parts = location.pathname.split("/").filter(Boolean);

  // Map known route segments to labels
  const labelMap: Record<string, string> = {
    dashboard: "Dashboard",
    devices: "Devices",
    sites: "Sites",
    templates: "Templates",
    map: "Fleet Map",
    "device-groups": "Device Groups",
    alerts: "Alerts",
    "alert-rules": "Alert Rules",
    "escalation-policies": "Escalation Policies",
    oncall: "On-Call",
    "maintenance-windows": "Maintenance Windows",
    notifications: "Notifications",
    "delivery-log": "Delivery Log",
    "dead-letter": "Dead Letter",
    analytics: "Analytics",
    reports: "Reports",
    subscription: "Subscription",
    billing: "Billing",
    settings: "Settings",
    users: "Team",
    roles: "Roles",
    ota: "OTA",
    fleet: "Fleet",
    operator: "Operator",
    "getting-started": "Getting Started",
    campaigns: "Campaigns",
    firmware: "Firmware",
    profile: "Profile",
    organization: "Organization",
    carrier: "Carrier Integrations",
    import: "Import",
    wizard: "Wizard",
  };

  const crumbs: { label: string; href?: string }[] = [];
  let path = "";
  for (const part of parts) {
    path += `/${part}`;
    const label = labelMap[part];
    if (label) {
      crumbs.push({ label, href: path });
    } else if (/^[0-9a-f-]{8,}$/i.test(part) || /^\d+$/.test(part)) {
      // UUID or numeric ID — show abbreviated
      crumbs.push({ label: part.length > 12 ? `${part.slice(0, 8)}...` : part });
    }
  }

  // Last crumb has no href (current page)
  if (crumbs.length > 0) {
    delete crumbs[crumbs.length - 1].href;
  }

  return crumbs;
}
```

#### Notification bell

Query open alert count (reuse the pattern already in AppSidebar):

```tsx
const { data: alertData } = useQuery({
  queryKey: ["header-alert-count"],
  queryFn: () => fetchAlerts("OPEN", 1, 0),
  refetchInterval: 30000,
  enabled: isCustomer,
});
const openAlertCount = alertData?.total ?? 0;
```

#### User avatar dropdown

Replace the raw email + logout button with a dropdown:

```tsx
function UserMenu() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useUIStore();

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "U";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-medium">
            {initials}
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="text-sm font-medium">{user?.email ?? "User"}</div>
          {user?.tenantId && (
            <div className="text-xs text-muted-foreground font-mono">{user.tenantId}</div>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/settings/profile">
            <UserCircle className="mr-2 h-4 w-4" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/settings/organization">
            <Building2 className="mr-2 h-4 w-4" />
            Organization
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark")}>
          {theme === "dark" ? <Moon className="mr-2 h-4 w-4" /> : theme === "light" ? <Sun className="mr-2 h-4 w-4" /> : <Monitor className="mr-2 h-4 w-4" />}
          Theme: {theme === "system" ? "System" : theme === "dark" ? "Dark" : "Light"}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

#### Full AppHeader render

```tsx
export function AppHeader() {
  const { user, logout, isCustomer } = useAuth();
  const breadcrumbs = useBreadcrumbs();

  // Alert count for notification bell
  const { data: alertData } = useQuery({
    queryKey: ["header-alert-count"],
    queryFn: () => fetchAlerts("OPEN", 1, 0),
    refetchInterval: 30000,
    enabled: isCustomer,
  });
  const openAlertCount = alertData?.total ?? 0;

  return (
    <header className="flex h-12 items-center gap-2 border-b border-border px-3 bg-card">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="h-5" />

      {/* Breadcrumbs */}
      <nav className="flex items-center gap-1 text-sm text-muted-foreground overflow-hidden" aria-label="Breadcrumb">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="flex items-center gap-1 shrink-0">
            {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
            {crumb.href ? (
              <Link to={crumb.href} className="hover:text-foreground transition-colors truncate max-w-[120px]">
                {crumb.label}
              </Link>
            ) : (
              <span className="text-foreground font-medium truncate max-w-[200px]">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>

      <div className="flex-1" />

      {/* Right side actions */}
      <div className="flex items-center gap-1">
        {/* Search */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() =>
            document.dispatchEvent(
              new KeyboardEvent("keydown", { key: "k", metaKey: true })
            )
          }
          title="Search (⌘K)"
        >
          <Search className="h-4 w-4" />
        </Button>

        {/* Connection status */}
        <ConnectionStatus />

        {/* Notification bell */}
        {isCustomer && (
          <Button variant="ghost" size="icon" className="relative h-8 w-8" asChild>
            <Link to="/alerts">
              <Bell className="h-4 w-4" />
              {openAlertCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-white">
                  {openAlertCount > 99 ? "99+" : openAlertCount}
                </span>
              )}
            </Link>
          </Button>
        )}

        {/* User avatar dropdown */}
        <UserMenu />
      </div>
    </header>
  );
}
```

Note: Header height reduced from `h-14` to `h-12` for a more compact, EMQX-like feel.

### PageHeader.tsx — Remove Breadcrumbs

Since breadcrumbs now live in the header (derived from the URL), remove the breadcrumbs rendering from `PageHeader`. Keep the `breadcrumbs` prop in the interface for backward compatibility (pages that pass it won't break), but don't render them:

**Current** (lines 16-44):
```tsx
export function PageHeader({ title, description, action, breadcrumbs }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="mb-1 flex items-center gap-1.5 text-sm text-muted-foreground" aria-label="Breadcrumb">
            ...
          </nav>
        )}
        <h1 className="text-lg font-semibold">{title}</h1>
```

**Updated:**
```tsx
export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-lg font-semibold">{title}</h1>
```

Keep the `breadcrumbs` in the `PageHeaderProps` interface but mark it as deprecated with a comment. Don't render it. The `breadcrumbs` prop can be removed from calling pages in a later cleanup pass — it's not urgent.

## Verification

- `npx tsc --noEmit` passes
- Header renders: sidebar trigger | breadcrumbs | spacer | search icon | connection status | bell | avatar
- Breadcrumbs auto-derive from URL path (e.g., `/devices/abc-123` shows "Devices > abc-12...")
- ChevronRight separators between breadcrumb segments
- Notification bell shows red badge with open alert count
- Clicking bell navigates to `/alerts`
- Avatar shows user initials, clicking opens dropdown
- Dropdown contains: email, tenant ID, Profile link, Organization link, Theme toggle, Log out
- Theme toggle cycles: Light → System → Dark
- Log out works
- Search icon opens CommandPalette (Cmd+K)
- Page headers no longer show duplicate breadcrumbs
- Header height is compact (h-12)
