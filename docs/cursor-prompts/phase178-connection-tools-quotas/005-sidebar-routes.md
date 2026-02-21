# Task 5: Sidebar, Routes, CommandPalette, Breadcrumbs

## Objective

Add "Tools" to the Fleet sidebar section, register the `/fleet/tools` route, update the CommandPalette page list, and add breadcrumb labels.

---

## 1. Install mqtt.js

Before any frontend changes, install the mqtt package:

```bash
cd frontend && npm install mqtt
```

If TypeScript types are missing (check if `node_modules/mqtt/dist/mqtt.d.ts` exists), also install:

```bash
cd frontend && npm install -D @types/mqtt
```

(mqtt.js v5+ includes types natively — check before installing `@types/mqtt`)

---

## 2. Sidebar — Add "Tools" to Fleet section

### File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

### Changes

**1. Add import:**

```tsx
import { Wrench } from "lucide-react";
```

(Add `Wrench` to the existing lucide-react import statement)

**2. Add "Tools" nav item to the Fleet section** — place it after "Updates" (the last item):

```tsx
{renderNavItem({ label: "Tools", href: "/fleet/tools", icon: Wrench })}
```

The Fleet section should now be:
```
Getting Started (conditional)
Devices
Sites
Templates
Fleet Map
Device Groups
Updates
Tools        ← NEW
```

---

## 3. Routes — Add `/fleet/tools` route

### File to Modify

`frontend/src/app/router.tsx`

### Changes

**1. Add import:**

```tsx
import ToolsHubPage from "@/features/fleet/ToolsHubPage";
```

**2. Add route** inside the `RequireCustomer` children array, near the other fleet routes (after `fleet/getting-started`):

```tsx
{ path: "fleet/tools", element: <ToolsHubPage /> },
```

---

## 4. CommandPalette — Add Tools entries

### File to Modify

`frontend/src/components/shared/CommandPalette.tsx`

### Changes

**1. Add import:**

Add `Wrench` to the lucide-react import:

```tsx
import { ..., Wrench } from "lucide-react";
```

**2. Add entries to the `pages` array** (inside the `useMemo`):

```tsx
{ label: "Tools", href: "/fleet/tools", icon: Wrench },
{ label: "Connection Guide", href: "/fleet/tools?tab=guide", icon: Wrench },
{ label: "MQTT Test Client", href: "/fleet/tools?tab=mqtt", icon: Wrench },
```

---

## 5. Breadcrumbs — Add label for "tools"

### File to Modify

`frontend/src/components/layout/AppHeader.tsx`

### Changes

Add `tools` to the `labelMap` in `useBreadcrumbs()`:

```tsx
tools: "Tools",
```

Place it alongside the other fleet-related entries. The breadcrumbs will auto-derive: **Fleet > Tools**.

---

## 6. Sidebar `isActive` — Add Tools match

### File to Modify

`frontend/src/components/layout/AppSidebar.tsx`

### Changes

The existing `isActive` function uses `location.pathname.startsWith(href)` as the default case. Since `/fleet/tools` starts with `/fleet/tools`, the default behavior will work correctly — no special case needed.

However, verify that the "Getting Started" link (`/fleet/getting-started`) doesn't inadvertently match `/fleet/tools` — it won't, because `startsWith("/fleet/getting-started")` is checked against the getting-started href specifically.

**No changes needed to `isActive`** — the default `startsWith` behavior handles this correctly.

---

## Verification

- `npx tsc --noEmit` passes
- `npm install mqtt` completes without errors
- "Tools" appears in the Fleet sidebar section (after "Updates")
- Clicking "Tools" navigates to `/fleet/tools` and shows the Tools hub with 2 tabs
- CommandPalette (Cmd+K) finds "Tools", "Connection Guide", "MQTT Test Client"
- Breadcrumbs show "Fleet > Tools" when on the Tools page
- Sidebar highlights "Tools" when on `/fleet/tools`
