# 007 — Roles Management Page + Permission Grid

## Task

Create a roles management page at `/settings/roles` (or `/roles`) where tenant admins can view system roles, create/edit/delete custom roles with a permission checkbox grid. Create three new files:
- `frontend/src/features/roles/RolesPage.tsx`
- `frontend/src/features/roles/CreateRoleDialog.tsx`
- `frontend/src/features/roles/PermissionGrid.tsx`

## Context

### Available hooks (from prompt 005)

```typescript
import { useRoles, useCreateRole, useUpdateRole, useDeleteRole, usePermissionsList } from "@/hooks/use-roles";
import { usePermissions } from "@/services/auth";
```

### UI components available

shadcn/ui components in `frontend/src/components/ui/`:
- `dialog`, `button`, `input`, `label`, `badge`, `skeleton`, `table`
- `card` (if exists — check; if not, use `div` with `rounded-md border p-4`)
- `checkbox` (if exists — needed for permission grid; if not, create a basic one)

Icons from `lucide-react`: `Plus`, `Pencil`, `Trash2`, `Shield`, `ChevronDown`, `ChevronRight`, `Lock`

### Page patterns

See `frontend/src/features/users/UsersPage.tsx` for the standard page layout:
```tsx
<PageHeader title="..." description="..." action={<Button>...</Button>} />
```

`PageHeader` is imported from `@/components/shared`.

## Create File: `frontend/src/features/roles/PermissionGrid.tsx`

### Purpose

Reusable checkbox grid component for selecting permissions, grouped by category.

### Props

```typescript
interface PermissionGridProps {
  permissions: Permission[];         // All available permissions
  selectedIds: Set<number>;          // Currently selected permission IDs
  onChange: (ids: Set<number>) => void;
  disabled?: boolean;               // For read-only view of system roles
}
```

### UI Layout

```
┌─ devices ────────────────────────────────┐
│ ☑ devices.read      View devices         │
│ ☑ devices.write     Edit device props    │
│ ☑ devices.create    Register devices     │
│ ☐ devices.delete    Decommission devices │
│ ☐ devices.commands  Send commands        │
├─ alerts ─────────────────────────────────┤
│ ☑ alerts.read       View alerts          │
│ ☐ alerts.acknowledge Acknowledge alerts  │
│ ☐ alerts.close      Close/resolve alerts │
│ ☑ alerts.rules.read View alert rules     │
│ ☐ alerts.rules.write Create/edit rules   │
├─ ... (more categories)                   │
└──────────────────────────────────────────┘
```

### Implementation

1. Group permissions by `category` using `useMemo`
2. Each category gets a section header with a "select all in category" checkbox
3. Each permission is a row with checkbox + action name + description
4. When a checkbox toggles, call `onChange` with updated Set
5. Category "select all" toggles all permissions in that category

```tsx
export function PermissionGrid({ permissions, selectedIds, onChange, disabled }: PermissionGridProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, Permission[]>();
    for (const p of permissions) {
      const list = map.get(p.category) || [];
      list.push(p);
      map.set(p.category, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permissions]);

  const togglePermission = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  };

  const toggleCategory = (permsInCategory: Permission[]) => {
    const next = new Set(selectedIds);
    const allSelected = permsInCategory.every((p) => next.has(p.id));
    for (const p of permsInCategory) {
      if (allSelected) next.delete(p.id);
      else next.add(p.id);
    }
    onChange(next);
  };

  // Render grouped sections...
}
```

## Create File: `frontend/src/features/roles/CreateRoleDialog.tsx`

### Purpose

Dialog for creating or editing a custom role. Used for both create and edit modes.

### Props

```typescript
interface CreateRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
  editRole?: Role;  // If provided, edit mode instead of create
}
```

### Implementation

1. **Fetch all permissions:** `usePermissionsList()`
2. **State:** `name: string`, `description: string`, `selectedPermissionIds: Set<number>`
3. **If editRole:** Initialize state from the role's current values
4. **Save:** Call `useCreateRole()` or `useUpdateRole()` depending on mode
5. **Validation:** Name required, at least one permission required

### UI Layout

```
┌─────────────────────────────────────────────┐
│ Create Custom Role  (or "Edit Role")        │
├─────────────────────────────────────────────┤
│ Name:        [__________________]           │
│ Description: [__________________]           │
│                                             │
│ Permissions:                                │
│ ┌─ PermissionGrid ───────────────────────┐  │
│ │ (full checkbox grid here)              │  │
│ └────────────────────────────────────────┘  │
│                                             │
│ Selected: 12 of 28 permissions              │
│                                             │
│                 [Cancel] [Create Role]       │
└─────────────────────────────────────────────┘
```

Make the dialog larger to fit the grid: `className="sm:max-w-2xl max-h-[80vh] overflow-y-auto"`

## Create File: `frontend/src/features/roles/RolesPage.tsx`

### Implementation

```tsx
export default function RolesPage() {
  const { hasPermission } = usePermissions();
  const { data, isLoading, error } = useRoles();
  const deleteMutation = useDeleteRole();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editRole, setEditRole] = useState<Role | null>(null);

  // Guard — should already be route-guarded, but belt-and-suspenders
  if (!hasPermission("users.roles")) {
    return <div className="p-6 text-muted-foreground">You don't have permission to manage roles.</div>;
  }

  const systemRoles = data?.roles?.filter((r) => r.is_system) ?? [];
  const customRoles = data?.roles?.filter((r) => !r.is_system) ?? [];

  // ... render
}
```

### UI Layout

```
┌──────────────────────────────────────────────────┐
│ Roles & Permissions                              │
│ Manage role bundles for your organization        │
│                                     [+ New Role] │
├──────────────────────────────────────────────────┤
│                                                  │
│ System Roles (read-only)                         │
│ ┌────────────────────────────────────────────┐   │
│ │ 🔒 Viewer          11 permissions  [View]  │   │
│ │ 🔒 Device Manager  15 permissions  [View]  │   │
│ │ 🔒 Alert Manager   15 permissions  [View]  │   │
│ │ 🔒 Integration Mgr 13 permissions  [View]  │   │
│ │ 🔒 Team Admin      15 permissions  [View]  │   │
│ │ 🔒 Full Admin      28 permissions  [View]  │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ Custom Roles                                     │
│ ┌────────────────────────────────────────────┐   │
│ │ Device Operator     8 permissions          │   │
│ │                            [Edit] [Delete] │   │
│ │ Monitoring Lead    14 permissions          │   │
│ │                            [Edit] [Delete] │   │
│ └────────────────────────────────────────────┘   │
│ (or "No custom roles yet" empty state)           │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Expandable permission view

Each role row should be expandable (click to see its permissions as badges). Use a simple open/close toggle state, or a Collapsible component.

When expanded:
```
│ 🔒 Viewer          11 permissions  [View ▼]  │
│   dashboard.read  devices.read  alerts.read  │
│   alerts.rules.read  integrations.read       │
│   users.read  reports.read  sites.read       │
│   subscriptions.read  maintenance.read       │
│   settings.read                              │
```

### Delete confirmation

Use `window.confirm()` before deleting (consistent with the pattern in UsersPage).

### Edit flow

Click "Edit" → open `CreateRoleDialog` with `editRole` prop pre-filled. System roles have no Edit button (only View which shows permissions read-only).

## Register the route

### Modify `frontend/src/app/router.tsx`

1. Add import at the top:
```typescript
import RolesPage from "@/features/roles/RolesPage";
```

2. Add the route. It should be inside the `RequireCustomer` children (or a new permission-based guard). For now, put it inside RequireCustomer since the page has its own permission check:

Inside the `RequireCustomer` children array (after the `subscription` routes, around line 106):
```typescript
{ path: "roles", element: <RolesPage /> },
```

## Verification

- `/roles` page shows 6 system roles with correct permission counts
- System roles cannot be edited or deleted (no Edit/Delete buttons, or buttons are hidden)
- "New Role" opens CreateRoleDialog with full permission grid
- Creating a custom role shows it in the Custom Roles section
- Editing a custom role pre-fills the dialog
- Deleting a custom role removes it from the list
- Expanding a role shows its permissions as badges
