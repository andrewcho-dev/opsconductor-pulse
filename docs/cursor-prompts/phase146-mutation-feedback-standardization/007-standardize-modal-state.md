# Task 7: Standardize Modal State Naming

## Context

Modal open state uses inconsistent naming: `open`, `showCreate`, `showEdit`, `openCreate`, `showAbortConfirm`, etc. Standardize to a consistent convention.

## Convention

### Simple boolean (open/close a single dialog):
```typescript
const [open, setOpen] = useState(false);
```

### Multiple dialogs in one component (add suffix):
```typescript
const [createOpen, setCreateOpen] = useState(false);
const [editOpen, setEditOpen] = useState(false);
const [deleteOpen, setDeleteOpen] = useState(false);
```

### Compound state (editing an item — null means closed):
```typescript
const [editing, setEditing] = useState<ItemType | null>(null);
// Open: setEditing(item)
// Close: setEditing(null)
// Dialog: <Dialog open={editing !== null} onOpenChange={(o) => { if (!o) setEditing(null); }}>
```

## Files to update

### Pattern: `showCreate` / `setShowCreate` → `createOpen` / `setCreateOpen`

**`frontend/src/features/ota/OtaCampaignsPage.tsx`:**
- `showCreate` → `createOpen`
- `setShowCreate` → `setCreateOpen`

**`frontend/src/features/operator/SubscriptionsPage.tsx`:**
- `showCreate` → `createOpen`
- `setShowCreate` → `setCreateOpen`

**`frontend/src/features/jobs/JobsPage.tsx`:**
- `showCreate` → `createOpen`
- `setShowCreate` → `setCreateOpen`

### Pattern: `showEdit` / `setShowEdit` → `editOpen` / `setEditOpen`

**`frontend/src/features/operator/OperatorTenantDetailPage.tsx`:**
- `showEdit` → `editOpen`
- `setShowEdit` → `setEditOpen`
- `showSubscriptionCreate` → `subscriptionCreateOpen`
- `setShowSubscriptionCreate` → `setSubscriptionCreateOpen`
- `showBulkAssign` → `bulkAssignOpen`
- `setShowBulkAssign` → `setBulkAssignOpen`

**`frontend/src/features/operator/SubscriptionDetailPage.tsx`:**
- `showEdit` → `editOpen`
- `setShowEdit` → `setEditOpen`
- `showStatusChange` → `statusChangeOpen`
- `setShowStatusChange` → `setStatusChangeOpen`

### Pattern: `openCreate` / `setOpenCreate` → `createOpen` / `setCreateOpen`

**`frontend/src/features/operator/UserListPage.tsx`:**
- `openCreate` → `createOpen`
- `setOpenCreate` → `setCreateOpen`
- `openAssignRole` → `assignRoleOpen`
- `setOpenAssignRole` → `setAssignRoleOpen`
- `openAssignTenant` → `assignTenantOpen`
- `setOpenAssignTenant` → `setAssignTenantOpen`

### Pattern: `showAbortConfirm` → `abortOpen`

**`frontend/src/features/ota/OtaCampaignDetailPage.tsx`:**
- `showAbortConfirm` → `abortOpen`
- `setShowAbortConfirm` → `setAbortOpen`

### Pattern: `showCreateDialog` → `createOpen`

**`frontend/src/features/dashboard/DashboardSelector.tsx`:**
- `showCreateDialog` → `createOpen`
- `setShowCreateDialog` → `setCreateOpen`

### Pattern: `showAddWidget` → `addWidgetOpen`

**`frontend/src/features/dashboard/DashboardPage.tsx`:**
- `showAddWidget` → `addWidgetOpen`
- `setShowAddWidget` → `setAddWidgetOpen`

### Pattern: `showRename` → `renameOpen`

**`frontend/src/features/dashboard/DashboardSettings.tsx`:**
- `showRename` → `renameOpen`
- `setShowRename` → `setRenameOpen`

### Pattern: `showForm` → `formOpen`

**`frontend/src/features/devices/DeviceCommandPanel.tsx`:**
- `showForm` → `formOpen`
- `setShowForm` → `setFormOpen`

## How to rename

For each file:
1. Open the file
2. Find-and-replace the old variable name with the new one (including in JSX props, onClick handlers, conditional rendering, etc.)
3. Make sure the Dialog/AlertDialog `open` prop and `onOpenChange` prop use the new names

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
