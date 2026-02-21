# Task 001: Global Search Command Palette (Cmd+K)

## Commit message
```
feat(ui): add Cmd+K global search command palette
```

## Overview
Install the `cmdk` package, create a Shadcn-style Command component wrapper, build a `CommandPalette` component with search across devices/alerts/users/pages, and mount it in `AppShell.tsx`.

---

## Step 1: Install cmdk

```bash
cd frontend && npm install cmdk
```

Verify it appears in `frontend/package.json` under `dependencies`.

---

## Step 2: Create `frontend/src/components/ui/command.tsx`

This is the standard Shadcn UI Command component wrapping `cmdk`. Follow the exact Shadcn pattern used by other components in `frontend/src/components/ui/` (e.g., `dialog.tsx`).

Create the file with these exports:

```typescript
"use client";

import * as React from "react";
import { Command as CommandPrimitive } from "cmdk";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

const Command = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive>
>(({ className, ...props }, ref) => (
  <CommandPrimitive
    ref={ref}
    className={cn(
      "flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground",
      className
    )}
    {...props}
  />
));
Command.displayName = CommandPrimitive.displayName;

function CommandDialog({
  children,
  ...props
}: React.ComponentProps<typeof Dialog>) {
  return (
    <Dialog {...props}>
      <DialogContent className="overflow-hidden p-0">
        <DialogTitle className="sr-only">Search</DialogTitle>
        <Command className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]]:px-2 [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-input-wrapper]_svg]:h-5 [&_[cmdk-input-wrapper]_svg]:w-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:h-5 [&_[cmdk-item]_svg]:w-5">
          {children}
        </Command>
      </DialogContent>
    </Dialog>
  );
}

const CommandInput = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Input>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Input>
>(({ className, ...props }, ref) => (
  <div className="flex items-center border-b px-3" cmdk-input-wrapper="">
    <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
    <CommandPrimitive.Input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  </div>
));
CommandInput.displayName = CommandPrimitive.Input.displayName;

const CommandList = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.List>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.List
    ref={ref}
    className={cn("max-h-[300px] overflow-y-auto overflow-x-hidden", className)}
    {...props}
  />
));
CommandList.displayName = CommandPrimitive.List.displayName;

const CommandEmpty = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Empty>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Empty>
>((props, ref) => (
  <CommandPrimitive.Empty
    ref={ref}
    className="py-6 text-center text-sm"
    {...props}
  />
));
CommandEmpty.displayName = CommandPrimitive.Empty.displayName;

const CommandGroup = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Group>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Group>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Group
    ref={ref}
    className={cn(
      "overflow-hidden p-1 text-foreground [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground",
      className
    )}
    {...props}
  />
));
CommandGroup.displayName = CommandPrimitive.Group.displayName;

const CommandSeparator = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 h-px bg-border", className)}
    {...props}
  />
));
CommandSeparator.displayName = CommandPrimitive.Separator.displayName;

const CommandItem = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Item>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex cursor-default gap-2 select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none data-[disabled=true]:pointer-events-none data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground data-[disabled=true]:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
      className
    )}
    {...props}
  />
));
CommandItem.displayName = CommandPrimitive.Item.displayName;

const CommandShortcut = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => {
  return (
    <span
      className={cn(
        "ml-auto text-xs tracking-widest text-muted-foreground",
        className
      )}
      {...props}
    />
  );
};
CommandShortcut.displayName = "CommandShortcut";

export {
  Command,
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
  CommandSeparator,
};
```

---

## Step 3: Create `frontend/src/components/shared/CommandPalette.tsx`

This is the main command palette component. Key behaviors:

### Keyboard shortcut
- Listen for `Cmd+K` (Mac) / `Ctrl+K` (Windows) globally to toggle open/close.
- `useEffect` with `keydown` listener on `document`.
- Detect Mac via `navigator.userAgent` or `navigator.platform`.

### State management
- `open` state (boolean) for dialog visibility.
- `query` state (string) for search input, debounced 300ms before firing API calls.
- Use `useDebouncedValue` hook from `@/hooks/useDebouncedValue` (already exists in the codebase).

### Search categories with API calls

Use TanStack React Query for each category, enabled only when `debouncedQuery.length >= 2`:

1. **Devices**: Call `fetchDevices({ q: debouncedQuery, limit: 5 })` from `@/services/api/devices`.
   - Display: device_id + status badge
   - On select: `navigate(`/devices/${device.device_id}`)`

2. **Alerts**: Call `fetchAlerts("OPEN", 5, 0)` from `@/services/api/alerts`. Filter client-side by query matching `device_id` or `alert_type`.
   - Display: alert_type + device_id + severity badge
   - On select: `navigate("/alerts")`

3. **Users** (operator only): Call `fetchOperatorUsers(debouncedQuery, undefined, 5)` from `@/services/api/users`. Only include this category when `isOperator` is true.
   - Display: username + email
   - On select: `navigate(`/operator/users/${user.id}`)`

4. **Pages** (static, always shown): Hardcoded list of navigable pages filtered by query match on label. Include:
   ```typescript
   const pages = [
     { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
     { label: "Devices", href: "/devices", icon: Cpu },
     { label: "Alerts", href: "/alerts", icon: Bell },
     { label: "Alert Rules", href: "/alert-rules", icon: ShieldAlert },
     { label: "Sites", href: "/sites", icon: Building2 },
     { label: "Device Groups", href: "/device-groups", icon: Layers },
     { label: "Escalation Policies", href: "/escalation-policies", icon: ShieldAlert },
     { label: "Notifications", href: "/notifications", icon: Webhook },
     { label: "On-Call", href: "/oncall", icon: Users },
     { label: "Maintenance Windows", href: "/maintenance-windows", icon: CalendarOff },
     { label: "Metrics", href: "/metrics", icon: Gauge },
     { label: "Reports", href: "/reports", icon: ScrollText },
     { label: "Delivery Log", href: "/delivery-log", icon: Activity },
     { label: "Subscription", href: "/subscription", icon: CreditCard },
     { label: "Users", href: "/users", icon: Users },
     { label: "Roles", href: "/roles", icon: Shield },
   ];
   ```
   - On select: `navigate(page.href)`

### Recent searches
- Store last 5 selected items in localStorage key `pulse_cmd_recent`.
- Each entry: `{ label: string, href: string, type: "device" | "alert" | "user" | "page" }`.
- Show "Recent" group at the top when query is empty.
- On select from any category, push to recent and navigate.

### Navigation
- Use `useNavigate()` from `react-router-dom`.
- After navigation, close the dialog (`setOpen(false)`) and reset query.

### Component structure

```typescript
import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command";
import {
  LayoutDashboard, Cpu, Bell, ShieldAlert, Building2, Layers,
  Webhook, Users, CalendarOff, Gauge, ScrollText, Activity,
  CreditCard, Shield, Search, Clock,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/services/auth/AuthProvider";
import { fetchDevices } from "@/services/api/devices";
import { fetchAlerts } from "@/services/api/alerts";
import { fetchOperatorUsers } from "@/services/api/users";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";

const RECENT_KEY = "pulse_cmd_recent";
const MAX_RECENT = 5;

interface RecentItem {
  label: string;
  href: string;
  type: "device" | "alert" | "user" | "page";
}

function getRecent(): RecentItem[] { /* read from localStorage, parse, return array */ }
function addRecent(item: RecentItem): void { /* prepend, dedupe by href, truncate to MAX_RECENT, save */ }

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 300);
  const navigate = useNavigate();
  const { isOperator, isCustomer } = useAuth();

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const shouldSearch = debouncedQuery.length >= 2;

  // Device search query
  const { data: deviceData } = useQuery({
    queryKey: ["cmd-devices", debouncedQuery],
    queryFn: () => fetchDevices({ q: debouncedQuery, limit: 5 }),
    enabled: shouldSearch && isCustomer,
  });

  // Alert search query
  const { data: alertData } = useQuery({
    queryKey: ["cmd-alerts", debouncedQuery],
    queryFn: () => fetchAlerts("OPEN", 5, 0),
    enabled: shouldSearch && isCustomer,
    select: (data) => ({
      ...data,
      alerts: data.alerts.filter(
        (a) =>
          a.device_id.toLowerCase().includes(debouncedQuery.toLowerCase()) ||
          a.alert_type.toLowerCase().includes(debouncedQuery.toLowerCase())
      ),
    }),
  });

  // User search query (operator only)
  const { data: userData } = useQuery({
    queryKey: ["cmd-users", debouncedQuery],
    queryFn: () => fetchOperatorUsers(debouncedQuery, undefined, 5),
    enabled: shouldSearch && isOperator,
  });

  const handleSelect = useCallback(
    (href: string, label: string, type: RecentItem["type"]) => {
      addRecent({ label, href, type });
      setOpen(false);
      setQuery("");
      navigate(href);
    },
    [navigate]
  );

  const recent = getRecent();

  // Pages list -- filtered by query
  // ... (static list from above, filtered with .filter(p => p.label.toLowerCase().includes(...)))

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="Search devices, alerts, pages..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Recent searches (only when query is empty) */}
        {!query && recent.length > 0 && (
          <CommandGroup heading="Recent">
            {recent.map((item) => (
              <CommandItem
                key={item.href}
                onSelect={() => handleSelect(item.href, item.label, item.type)}
              >
                <Clock className="mr-2 h-4 w-4 text-muted-foreground" />
                <span>{item.label}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Devices */}
        {deviceData?.devices && deviceData.devices.length > 0 && (
          <CommandGroup heading="Devices">
            {deviceData.devices.map((device) => (
              <CommandItem
                key={device.device_id}
                onSelect={() =>
                  handleSelect(`/devices/${device.device_id}`, device.device_id, "device")
                }
              >
                <Cpu className="mr-2 h-4 w-4" />
                <span>{device.device_id}</span>
                <Badge variant="outline" className="ml-auto text-xs">
                  {device.status}
                </Badge>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Alerts */}
        {alertData?.alerts && alertData.alerts.length > 0 && (
          <CommandGroup heading="Alerts">
            {alertData.alerts.map((alert) => (
              <CommandItem
                key={alert.alert_id}
                onSelect={() =>
                  handleSelect("/alerts", `${alert.alert_type} - ${alert.device_id}`, "alert")
                }
              >
                <Bell className="mr-2 h-4 w-4" />
                <span>{alert.alert_type}</span>
                <span className="text-muted-foreground ml-1">({alert.device_id})</span>
                <Badge variant="destructive" className="ml-auto text-xs">
                  S{alert.severity}
                </Badge>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Users (operator only) */}
        {userData?.users && userData.users.length > 0 && (
          <CommandGroup heading="Users">
            {userData.users.map((user) => (
              <CommandItem
                key={user.id}
                onSelect={() =>
                  handleSelect(`/operator/users/${user.id}`, user.username, "user")
                }
              >
                <Users className="mr-2 h-4 w-4" />
                <span>{user.username}</span>
                <span className="text-muted-foreground ml-1">{user.email}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {/* Pages (always shown, filtered) */}
        <CommandGroup heading="Pages">
          {/* filtered pages.map(...) */}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
```

### Important implementation notes

- The `CommandDialog` uses the existing `Dialog` from `@/components/ui/dialog.tsx`. Make sure `DialogTitle` with `className="sr-only"` is included for accessibility (already in the command.tsx wrapper above).
- The `cmdk` library handles keyboard navigation (arrow keys, enter to select) automatically.
- The `onValueChange` prop on `CommandInput` is from cmdk -- it sets the internal search value and triggers filtering.
- For the Pages group, cmdk's built-in filtering will work if the `value` prop on each `CommandItem` matches the label text. You can set `value={page.label}` explicitly on each page `CommandItem`.

---

## Step 4: Mount in AppShell.tsx

Edit `frontend/src/components/layout/AppShell.tsx`:

```typescript
// Add import
import { CommandPalette } from "@/components/shared/CommandPalette";

// Inside the return, add CommandPalette as a sibling of the layout div:
export default function AppShell() {
  useWebSocket();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <div className="flex flex-1 flex-col">
          <AppHeader />
          <SubscriptionBanner />
          <main className="flex-1 p-6 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
      <CommandPalette />
    </SidebarProvider>
  );
}
```

The `CommandPalette` must be inside `SidebarProvider` so it has access to React context, but it renders a portal dialog so visual placement does not matter.

---

## Step 5: Add keyboard hint to AppHeader (optional but recommended)

In `frontend/src/components/layout/AppHeader.tsx`, add a small search trigger button before the theme toggle:

```typescript
import { Search } from "lucide-react";

// Inside AppHeader, in the flex items-center gap-2 div, before <ConnectionStatus />:
<Button
  variant="outline"
  size="sm"
  className="hidden sm:flex items-center gap-2 text-muted-foreground text-xs h-8 px-2"
  onClick={() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }))}
>
  <Search className="h-3.5 w-3.5" />
  <span>Search...</span>
  <kbd className="pointer-events-none ml-1 inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
    <span className="text-xs">⌘</span>K
  </kbd>
</Button>
```

**Alternative approach**: Instead of dispatching a synthetic keyboard event, export a `useCommandPalette` store (zustand or simple context) from `CommandPalette.tsx` that exposes `{ open, setOpen }`, and call `setOpen(true)` from the button. This is cleaner. Choose whichever approach you prefer, but document which one you use.

---

## Verification

1. `cd frontend && npm run build` -- zero errors.
2. Open the app in browser. Press `Cmd+K` (Mac) or `Ctrl+K` (Windows). Dialog opens.
3. Type a device ID (e.g., "SENSOR"). Device results appear under "Devices" group.
4. Press Enter or click a device result. Dialog closes, navigates to `/devices/{device_id}`.
5. Press `Cmd+K` again with empty query. "Recent" group shows the device you just selected.
6. Type "dash" -- "Dashboard" appears under "Pages" group.
7. As operator, type a username -- "Users" group shows operator user results.
8. Press Escape or click outside -- dialog closes.

---

## Files Created/Modified

| Action | File |
|--------|------|
| CREATE | `frontend/src/components/ui/command.tsx` |
| CREATE | `frontend/src/components/shared/CommandPalette.tsx` |
| MODIFY | `frontend/src/components/layout/AppShell.tsx` |
| MODIFY | `frontend/src/components/layout/AppHeader.tsx` (optional search hint button) |
| MODIFY | `frontend/package.json` (cmdk dependency added by npm install) |
