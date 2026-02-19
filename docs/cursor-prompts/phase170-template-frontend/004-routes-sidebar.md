# Task 4: Wire Routes and Sidebar Navigation

## Modify file: `frontend/src/app/router.tsx`

### Add Imports

At the top of the file, add:
```typescript
import TemplateListPage from "@/features/templates/TemplateListPage";
import TemplateDetailPage from "@/features/templates/TemplateDetailPage";
```

### Add Routes

Inside the `RequireCustomer` children array, add template routes **before** the devices routes (since templates are a prerequisite concept):

```typescript
// After the sites routes and before the devices routes:
{ path: "templates", element: <TemplateListPage /> },
{ path: "templates/:templateId", element: <TemplateDetailPage /> },
```

Place them around line 102-103, before the `{ path: "devices", ... }` entry.

## Modify file: `frontend/src/components/layout/AppSidebar.tsx`

### Add Import

Add the `LayoutTemplate` icon import:
```typescript
import { LayoutTemplate } from "lucide-react";
```

(Check existing lucide imports and add to that import statement.)

### Add Sidebar Entry

Find the **Fleet** navigation group (the collapsible section containing Devices, Sensors, Device Groups, Fleet Map, OTA Updates, Firmware, Sites).

Add "Device Templates" as the **first item** in the Fleet group (above Devices):

```tsx
{
  label: "Device Templates",
  href: "/templates",
  icon: LayoutTemplate,
},
```

Follow the exact pattern used by the other nav items in the same group. Each item typically has:
- `label`: Display text
- `href`: Route path
- `icon`: Lucide icon component

### Active Route Detection

Ensure the active route detection logic works for `/templates` and `/templates/:id`. The sidebar likely uses `useLocation()` and compares `pathname.startsWith(href)` — verify this pattern handles the new routes.

## Verification

1. Navigate to `/app/templates` → TemplateListPage renders
2. Navigate to `/app/templates/1` → TemplateDetailPage renders
3. "Device Templates" appears in sidebar under Fleet group
4. Clicking the sidebar link navigates correctly
5. Active state highlights correctly on both list and detail pages
6. `npx tsc --noEmit` passes
