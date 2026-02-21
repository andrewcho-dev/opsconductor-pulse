# Task 3: Update CommandPalette Navigation

## File

`frontend/src/components/shared/CommandPalette.tsx`

## Current State

Lines 144-151 in the `pages` array reference hub tabs that no longer exist:

```tsx
{ label: "Sites", href: "/devices?tab=sites", icon: Building2 },
{ label: "Device Groups", href: "/devices?tab=groups", icon: Layers },
{ label: "Connection Guide", href: "/devices?tab=guide", icon: Wrench },
{ label: "MQTT Test Client", href: "/devices?tab=mqtt", icon: Wrench },
```

## Changes

Update these 4 entries to point to their new standalone routes:

```tsx
// OLD:
{ label: "Sites", href: "/devices?tab=sites", icon: Building2 },
{ label: "Device Groups", href: "/devices?tab=groups", icon: Layers },
{ label: "Connection Guide", href: "/devices?tab=guide", icon: Wrench },
{ label: "MQTT Test Client", href: "/devices?tab=mqtt", icon: Wrench },

// NEW:
{ label: "Sites", href: "/sites", icon: Building2 },
{ label: "Device Groups", href: "/device-groups", icon: Layers },
{ label: "Connection Guide", href: "/fleet/tools", icon: Wrench },
{ label: "MQTT Test Client", href: "/fleet/mqtt-client", icon: Wrench },
```

No other changes needed — the labels, icons, and surrounding entries remain the same.

## Verification

```bash
cd frontend && npx tsc --noEmit
```

- Open CommandPalette (Cmd+K / Ctrl+K)
- Search for "Sites" → navigates to `/sites` (standalone page, not hub tab)
- Search for "Device Groups" → navigates to `/device-groups`
- Search for "Connection Guide" → navigates to `/fleet/tools`
- Search for "MQTT" → navigates to `/fleet/mqtt-client`
