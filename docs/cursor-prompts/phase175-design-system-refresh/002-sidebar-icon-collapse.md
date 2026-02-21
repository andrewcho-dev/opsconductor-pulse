# Task 2: Sidebar Icon-Only Collapse Mode

## Objective

Enable the shadcn/ui sidebar's built-in icon-only collapse mode (instead of the current offcanvas hide), add tooltips to all nav items, add SidebarRail for drag-to-toggle, and style the active item with a primary-colored indicator.

## Files to Modify

- `frontend/src/components/layout/AppSidebar.tsx` — main changes
- `frontend/src/components/layout/AppShell.tsx` — minor: read persisted state

## Current State

### AppSidebar.tsx

The `<Sidebar>` component (line 241) uses default `collapsible="offcanvas"` which completely hides the sidebar when collapsed. When collapsed, no icons are visible.

The `renderNavItem` function (lines 193-219) renders `<SidebarMenuButton>` without the `tooltip` prop, so collapsed icon mode would show icons with no text explanation.

### sidebar.tsx (reference, do not modify)

The shadcn/ui sidebar component already fully supports `collapsible="icon"`:
- `SIDEBAR_WIDTH_ICON = "3rem"` (line 32)
- Icon mode hides text labels, shows only icons at 3rem width
- `SidebarMenuButton` accepts a `tooltip` prop that shows a tooltip on hover when collapsed
- `SidebarRail` provides a clickable rail at the sidebar edge for toggle
- `SidebarGroupLabel` auto-hides in icon mode (line 409: `group-data-[collapsible=icon]:-mt-8 group-data-[collapsible=icon]:opacity-0`)

### AppShell.tsx

`SidebarProvider` on line 15 uses `defaultOpen={true}`. The sidebar component internally persists state to a cookie (`sidebar_state`).

## Changes

### AppSidebar.tsx

#### Step 1: Change Sidebar collapsible prop

On the `<Sidebar>` component (line 241), add `collapsible="icon"`:

```tsx
<Sidebar collapsible="icon">
```

#### Step 2: Add SidebarRail

Import `SidebarRail` from `@/components/ui/sidebar` (add to existing import on line 42-53).

Add `<SidebarRail />` as the last child inside `<Sidebar>`, just before the closing `</Sidebar>` tag (after `<SidebarFooter>`, around line 486):

```tsx
      <SidebarFooter className="p-2" />
      <SidebarRail />
    </Sidebar>
```

#### Step 3: Add tooltip prop to renderNavItem

Update the `renderNavItem` function (line 193) to pass the `tooltip` prop to `SidebarMenuButton`. This makes the label appear as a tooltip when the sidebar is in icon-only mode:

Change line 198 from:
```tsx
<SidebarMenuButton asChild isActive={isActive(item.href)}>
```
To:
```tsx
<SidebarMenuButton asChild isActive={isActive(item.href)} tooltip={item.label}>
```

This applies to ALL nav items rendered by `renderNavItem` automatically.

#### Step 4: Add tooltip to Getting Started item

The Getting Started nav item (inside the Fleet collapsible, added in Phase 174) is rendered inline, not via `renderNavItem`. Add the `tooltip` prop there too:

```tsx
<SidebarMenuButton asChild isActive={isActive("/fleet/getting-started")} tooltip="Getting Started">
```

#### Step 5: Style active sidebar items with primary accent

The current active item styling uses `data-[active=true]:bg-sidebar-accent` which is a neutral gray. EMQX uses a primary-colored highlight for active items.

This is controlled by the CSS tokens updated in Task 1 (`--sidebar-accent` changed to a violet tint). No additional component changes needed — the token change in Task 1 handles this.

However, to add a **left border indicator** for the active item (like EMQX), add a custom class override. In the `renderNavItem` function, update the `SidebarMenuButton` to include a left border when active:

```tsx
<SidebarMenuButton
  asChild
  isActive={isActive(item.href)}
  tooltip={item.label}
  className={isActive(item.href) ? "border-l-2 border-l-primary" : ""}
>
```

#### Step 6: Ensure collapsible group labels hide in icon mode

The `SidebarGroupLabel` component already has `group-data-[collapsible=icon]:opacity-0` built in (sidebar.tsx line 409). The Phase 174 sub-group labels ("Setup", "Monitor", "Maintain") are raw `<div>` elements — they need to be hidden in icon mode too.

Add `group-data-[collapsible=icon]:hidden` to each sub-group label div. For example:

```tsx
<div className="px-2 pt-3 pb-1 group-data-[collapsible=icon]:hidden">
  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Setup</span>
</div>
```

Apply this to all three sub-group labels (Setup, Monitor, Maintain).

#### Step 7: Ensure SidebarHeader works in icon mode

The current SidebarHeader (lines 242-257) contains the logo + "OpsConductor / Pulse" text. In icon mode, the text should hide and only the logo icon should be visible.

Wrap the text in a container that hides in icon mode:

```tsx
<SidebarHeader className="p-4">
  <Link
    to={isOperator ? "/operator" : "/dashboard"}
    className="flex items-center gap-2 no-underline"
  >
    <img
      src="/app/opsconductor_logo_clean_PROPER.svg"
      alt="OpsConductor Pulse"
      className="h-8 w-8 shrink-0"
    />
    <div className="group-data-[collapsible=icon]:hidden">
      <div className="text-sm font-semibold text-sidebar-foreground">OpsConductor</div>
      <div className="text-sm text-muted-foreground">Pulse</div>
    </div>
  </Link>
</SidebarHeader>
```

Add `shrink-0` to the logo `<img>` so it doesn't shrink in icon mode.

### AppShell.tsx

No changes needed. The `SidebarProvider` already handles state persistence via cookies. The `defaultOpen={true}` means the sidebar starts expanded on first visit, which is correct.

## Verification

- `npx tsc --noEmit` passes
- Sidebar renders in expanded mode by default
- Clicking the SidebarTrigger (hamburger) in the header collapses the sidebar to icon-only mode
- In icon mode: only icons visible, hovering shows tooltip with the label
- SidebarRail visible at the right edge of the sidebar — clicking it toggles collapse
- Cmd+B keyboard shortcut toggles sidebar
- Active item has a subtle violet background tint + left border indicator
- Sub-group labels (Setup/Monitor/Maintain) hidden in icon mode
- Logo text hidden in icon mode, logo icon remains visible
- Collapsible group headers (Fleet, Monitoring, etc.) work correctly in both modes
- State persists across page reloads (via cookie)
