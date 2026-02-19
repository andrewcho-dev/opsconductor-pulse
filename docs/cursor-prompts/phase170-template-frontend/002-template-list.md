# Task 2: Template List Page

## Create file: `frontend/src/features/templates/TemplateListPage.tsx`

Build a list page for templates. Follow the patterns from existing list pages (e.g., `AlertRulesPage`, `SitesPage`, `DeviceListPage`).

### Component Structure

```
TemplateListPage
├── Page header ("Device Templates") + "Create Template" button
├── Filter bar
│   ├── Category dropdown (All, Gateway, Edge Device, Standalone Sensor, Controller, Expansion Module)
│   ├── Source filter (All, System, Tenant)
│   └── Search input
├── DataTable
│   ├── Columns: Name, Category, Source (badge), Manufacturer, Model, Metrics count, Slots count, Actions
│   ├── Row click → navigate to /templates/{id}
│   └── Actions column: Clone (for system), Edit (for tenant), Delete (for tenant)
└── Create Template Dialog (or navigate to detail page in create mode)
```

### Key Implementation Details

1. **Data fetching**: Use TanStack Query (React Query) to fetch templates:
   ```typescript
   const { data: templates, isLoading } = useQuery({
     queryKey: ["templates", { category, source, search }],
     queryFn: () => listTemplates({ category, source, search }),
   });
   ```

2. **Source badge**: System templates show a `<Badge variant="secondary">System</Badge>` with a lock icon; tenant templates show `<Badge>Custom</Badge>`.

3. **Category display**: Use a mapping to human-readable labels:
   ```typescript
   const categoryLabels: Record<string, string> = {
     gateway: "Gateway",
     edge_device: "Edge Device",
     standalone_sensor: "Standalone Sensor",
     controller: "Controller",
     expansion_module: "Expansion Module",
   };
   ```

4. **Actions**:
   - **Clone**: Show on system templates. Calls `cloneTemplate(id)`, then invalidates query and navigates to the new template.
   - **Edit**: Show on tenant templates (not locked). Navigates to `/templates/{id}`.
   - **Delete**: Show on tenant templates. Confirmation dialog, then calls `deleteTemplate(id)`.

5. **Create Template Dialog**: Either a simple modal with the TemplateCreate fields, or navigate to `/templates/new`. Simpler approach: use a Dialog component with a form containing name, slug (auto-generated from name), category dropdown, and optional fields. On submit, call `createTemplate()` and navigate to the new detail page.

6. **Slug generation**: Auto-generate slug from name using a helper:
   ```typescript
   function slugify(name: string): string {
     return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
   }
   ```
   Let user edit the auto-generated slug.

### UI Components to Use

- `data-table.tsx` from `@/components/ui/data-table` (or build with TanStack Table)
- `Badge` from `@/components/ui/badge`
- `Button` from `@/components/ui/button`
- `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle` from `@/components/ui/dialog`
- `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` from `@/components/ui/select`
- `Input` from `@/components/ui/input`
- Icons: `LayoutTemplate`, `Lock`, `Copy`, `Trash2`, `Plus` from `lucide-react`

### Empty state

When no templates match the filters, show a centered empty state:
```
No templates found.
[Create your first template] button
```

## Verification

1. Page renders with system templates from seed data
2. Filters work (category, source, search)
3. Clone creates a tenant copy and navigates to it
4. Create template dialog works
5. Delete confirmation dialog works
