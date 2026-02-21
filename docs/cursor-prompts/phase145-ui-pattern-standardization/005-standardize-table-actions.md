# Task 5: Standardize Table Row Actions

## Context

Table row actions use 4 different patterns: inline text links, dropdown menus, icon buttons, and labeled buttons. The rule:

- **1-2 actions:** `<Button variant="ghost" size="sm">` with icon + short label
- **3+ actions:** `MoreHorizontal` dropdown menu. Destructive items after a separator.
- **Navigate to detail:** `<Link>` on the name/ID column text. NOT a separate View button.

## Step 1: Fix Operator Tenants table

**File:** `frontend/src/features/operator/OperatorTenantsPage.tsx`

Currently uses three separate icon-only ghost buttons: Eye (view), Pencil (edit), Trash2 (delete).

**Problems:** Eye button is unnecessary if the tenant name is a `<Link>`. Three icon-only buttons with no labels are hard to distinguish.

**Fix:**
1. Make the tenant name column a `<Link>`:
```tsx
<Link to={`/operator/tenants/${row.tenant_id}`} className="text-primary hover:underline">
  {row.name}
</Link>
```
2. Remove the Eye (view) icon button entirely.
3. Change Edit and Delete to a `MoreHorizontal` dropdown (3 actions including the now-removed View):

Actually, with View removed, only Edit + Delete remain (2 actions). Use inline ghost buttons:
```tsx
<div className="flex items-center gap-1">
  <Button variant="ghost" size="sm" onClick={() => handleEdit(row)}>
    <Pencil className="mr-1 h-3.5 w-3.5" />
    Edit
  </Button>
  <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(row)}>
    <Trash2 className="mr-1 h-3.5 w-3.5" />
    Delete
  </Button>
</div>
```

## Step 2: Fix Device List table actions

**File:** `frontend/src/features/devices/DeviceTable.tsx` or `DeviceListPage.tsx`

If using inline text links (`"Edit" / "Decommission"`), change to ghost buttons:
```tsx
<Button variant="ghost" size="sm" onClick={() => onEdit(device)}>
  <Pencil className="mr-1 h-3.5 w-3.5" />
  Edit
</Button>
```

Ensure the device ID/name is a `<Link>` for navigation.

## Step 3: Fix Alert Rules table actions

**File:** `frontend/src/features/alerts/AlertRulesPage.tsx`

Currently uses labeled outline buttons (`"Edit" / "Delete"`). Change to ghost buttons to match convention:
```tsx
<Button variant="ghost" size="sm" onClick={() => handleEdit(rule)}>
  <Pencil className="mr-1 h-3.5 w-3.5" />
  Edit
</Button>
<Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(rule)}>
  <Trash2 className="mr-1 h-3.5 w-3.5" />
  Delete
</Button>
```

## Step 4: Verify dropdown menu pattern for 3+ action tables

These pages already use MoreHorizontal dropdown correctly and should be left alone (just verify):
- `NotificationChannelsPage.tsx` — Test, Edit, History, Delete → correct pattern
- `UsersPage.tsx` — Edit, Manage Roles, Reset Password, Remove → correct pattern
- `OtaCampaignsPage.tsx` — View Details, Abort → correct pattern (but "View Details" should be removed if name is a Link)

For OtaCampaignsPage: remove the "View Details" dropdown item if the campaign name column is already a `<Link>`. That leaves only "Abort" which can be a single inline button:
```tsx
<Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleAbort(campaign)}>
  Abort
</Button>
```

## Step 5: Fix Escalation Policies table

Verify it uses the same ghost button pattern for Edit + Delete.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
