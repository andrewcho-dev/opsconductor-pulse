# Task 3: Standardize Create/Add Button Labels

## Context

Create/add buttons use 4 different conventions:
- `"+ New Campaign"` (text prefix)
- `Plus` icon + `"Create Tenant"` (icon component)
- `"Add Channel"` (no icon, different verb)
- `"Add Rule"` (yet another verb)

The rule: ALL create buttons use the `Plus` icon component + `"Add {Noun}"` label. Always in PageHeader `action` prop.

## Step 1: Find all create buttons in page headers

Run: `grep -rn "action=" frontend/src/features/ --include="*.tsx" | grep -i "new\|create\|add"` and review each.

## Step 2: Standardize each one

### OtaCampaignsPage.tsx
```
BEFORE: <Button onClick={() => setShowCreate(true)}>+ New Campaign</Button>
AFTER:  <Button onClick={() => setShowCreate(true)}><Plus className="mr-1 h-4 w-4" />Add Campaign</Button>
```
Import `Plus` from lucide-react if not already.

### FirmwareListPage.tsx
```
BEFORE: <Button onClick={() => setShowUpload(true)}>+ Register Firmware</Button>
AFTER:  <Button onClick={() => setShowUpload(true)}><Plus className="mr-1 h-4 w-4" />Add Firmware</Button>
```

### NotificationChannelsPage.tsx
```
BEFORE: <Button onClick={() => { setEditing(null); setOpen(true); }}>Add Channel</Button>
AFTER:  <Button onClick={() => { setEditing(null); setOpen(true); }}><Plus className="mr-1 h-4 w-4" />Add Channel</Button>
```
(Just add the icon — label is already correct.)

### AlertRulesPage.tsx
```
BEFORE: <Button onClick={() => { setEditingRule(null); setDialogOpen(true); }}>Add Rule</Button>
AFTER:  <Button onClick={() => { setEditingRule(null); setDialogOpen(true); }}><Plus className="mr-1 h-4 w-4" />Add Rule</Button>
```

### EscalationPoliciesPage.tsx
Find the create button and apply same pattern:
```
<Button onClick={...}><Plus className="mr-1 h-4 w-4" />Add Policy</Button>
```

### JobsPage.tsx
```
BEFORE: anything with "Create Job" or "+ Create Job"
AFTER:  <Button onClick={...}><Plus className="mr-1 h-4 w-4" />Add Job</Button>
```

### DeviceListPage.tsx / DeviceActions component
The DeviceActions component has multiple buttons. The primary should be:
```
<Button onClick={onCreate}><Plus className="mr-1 h-4 w-4" />Add Device</Button>
```
Secondary actions (Guided Setup, Import) should be `variant="outline"`.

### RolesPage.tsx
```
BEFORE: anything with "New Role"
AFTER:  <Button onClick={...}><Plus className="mr-1 h-4 w-4" />Add Role</Button>
```

### UsersPage.tsx
```
BEFORE: anything with "Invite User"
AFTER:  <Button onClick={...}><Plus className="mr-1 h-4 w-4" />Add User</Button>
```

### OperatorTenantsPage.tsx
```
BEFORE: anything with "Create Tenant"
AFTER:  <Button onClick={...}><Plus className="mr-1 h-4 w-4" />Add Tenant</Button>
```

## Step 3: Verify consistency

```bash
# All page header create buttons should now have Plus icon + "Add" verb
grep -rn "Plus.*Add\|Add.*Plus" frontend/src/features/ --include="*.tsx" | head -20
```

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
