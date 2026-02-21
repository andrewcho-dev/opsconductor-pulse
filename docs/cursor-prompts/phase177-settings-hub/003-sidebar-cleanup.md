# Task 3: Sidebar — Replace Settings Group with Single Link

## Objective

Replace the 4-item Settings group in the customer sidebar with a single "Settings" link. This reduces the sidebar from ~16 items to ~12 items.

## File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

## Changes

### 1. Replace the Settings SidebarGroup

Find the Settings section (currently around lines 267-281):

```tsx
{/* Settings section */}
<SidebarGroup>
  <SidebarGroupLabel>Settings</SidebarGroupLabel>
  <SidebarGroupContent>
    <SidebarMenu>
      {renderNavItem({ label: "Notifications", href: "/notifications", icon: Webhook })}
      {canManageUsers && renderNavItem({ label: "Team", href: "/team", icon: Users })}
      {renderNavItem({ label: "Billing", href: "/billing", icon: CreditCard })}
      {renderNavItem({
        label: "Integrations",
        href: "/settings/carrier",
        icon: Radio,
      })}
    </SidebarMenu>
  </SidebarGroupContent>
</SidebarGroup>
```

Replace with a single standalone item (no group label needed):

```tsx
{/* Settings — single link */}
<SidebarGroup>
  <SidebarGroupContent>
    <SidebarMenu>
      {renderNavItem({ label: "Settings", href: "/settings", icon: Settings })}
    </SidebarMenu>
  </SidebarGroupContent>
</SidebarGroup>
```

### 2. Update `isActive` function

The Settings link at `/settings` should be active when the user is at ANY `/settings/*` route. The existing `isActive` function already handles this via `location.pathname.startsWith(href)`, so `/settings` will match `/settings/general`, `/settings/billing`, etc.

However, verify there are no conflicts — the current sidebar has no other items starting with `/settings`.

### 3. Remove unused permission check

The `canManageUsers` variable was used for the Team sidebar item. Since the Team link is now inside the Settings page (which handles its own permission checks), the `canManageUsers` variable may no longer be needed in AppSidebar.

Check if `canManageUsers` is used elsewhere in the file. If not, remove:
```tsx
const canManageUsers = hasPermission("users.read");
```

And potentially the `usePermissions` import and `hasPermission` destructuring if no other permission checks remain in the sidebar.

### 4. Clean up unused icon imports

Remove icons from the lucide-react import that are no longer used in the sidebar:
- `Webhook` (was Notifications icon)
- `CreditCard` (was Billing icon)
- `Users` (was Team icon)
- `Radio` (was Integrations icon — BUT check if it's still used for Updates icon)

Keep `Settings` (it's the new Settings link icon).

Actually, check each icon's usage carefully before removing. `Radio` is used for Updates, so keep it. `Users` might be used elsewhere. Only remove icons that have zero remaining references in this file.

## Resulting Sidebar Structure

```
Home
── MONITORING ──
  Dashboard
  Alerts
  Analytics
── FLEET ──
  Getting Started  (conditional)
  Devices
  Sites
  Templates
  Fleet Map
  Device Groups
  Updates
Settings              ← single link, replaces 4-item group
```

~12 items total (11 when Getting Started is dismissed).

## Verification

- `npx tsc --noEmit` passes
- Customer sidebar shows "Settings" as a single item below Fleet
- No "SETTINGS" group label — it's a standalone item like "Home"
- Clicking "Settings" navigates to `/settings`
- "Settings" highlights when at any `/settings/*` route
- Operator sidebar is unchanged
- No unused imports remain
