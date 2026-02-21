# Task 1: Fix Dashboard Actions

## Context

The dashboard has an "Edit Layout" button sitting as a standalone content-area button in `DashboardBuilder.tsx`. The Settings gear icon already exists in `DashboardSettings.tsx` with Rename/Default/Share options. The edit toggle should be inside that gear menu — not a floating button.

## Step 1: Move Edit Layout into DashboardSettings

**File:** `frontend/src/features/dashboard/DashboardSettings.tsx`

The component currently receives only `dashboard` as props. Add the edit state and callbacks:

Change the interface:
```tsx
interface DashboardSettingsProps {
  dashboard: Dashboard;
  isEditing: boolean;
  onToggleEdit: () => void;
  onAddWidget: () => void;
}
```

Add new menu items BEFORE the Rename item (at the top of the dropdown):

```tsx
<DropdownMenuContent align="end">
  <DropdownMenuItem onClick={onToggleEdit}>
    {isEditing ? (
      <>
        <Lock className="h-4 w-4 mr-2" />
        Lock Layout
      </>
    ) : (
      <>
        <Pencil className="h-4 w-4 mr-2" />
        Edit Layout
      </>
    )}
  </DropdownMenuItem>

  {isEditing && (
    <DropdownMenuItem onClick={onAddWidget}>
      <Plus className="h-4 w-4 mr-2" />
      Add Widget
    </DropdownMenuItem>
  )}

  <DropdownMenuSeparator />

  {/* existing Rename, Set as Default, Share items below */}
```

Add `Lock`, `Plus` to the lucide imports.

## Step 2: Remove standalone buttons from DashboardBuilder

**File:** `frontend/src/features/dashboard/DashboardBuilder.tsx`

Remove the entire toolbar div (lines 121-152):
```tsx
// DELETE THIS ENTIRE BLOCK:
{canEdit && (
  <div className="flex items-center gap-2">
    <Button variant={isEditing ? "default" : "outline"} size="sm" onClick={handleToggleEdit}>
      ...
    </Button>
    {isEditing && (
      <Button variant="outline" size="sm" onClick={() => setShowAddWidget(true)}>
        ...
      </Button>
    )}
    {layoutMutation.isPending && (
      <span className="...">Saving...</span>
    )}
  </div>
)}
```

Keep the `handleToggleEdit` function and `isEditing` state — they're still needed. But expose them so the parent can pass them to DashboardSettings.

Change the component to expose edit state:
```tsx
interface DashboardBuilderProps {
  dashboard: Dashboard;
  canEdit: boolean;
  isEditing: boolean;
  onToggleEdit: () => void;
  onAddWidget: () => void;
}

export function DashboardBuilder({ dashboard, canEdit, isEditing, onToggleEdit, onAddWidget }: DashboardBuilderProps) {
```

Move the `isEditing` state, `handleToggleEdit`, and `showAddWidget` state up to `DashboardPage.tsx`.

## Step 3: Lift state to DashboardPage

**File:** `frontend/src/features/dashboard/DashboardPage.tsx`

Add state:
```tsx
const [isEditing, setIsEditing] = useState(false);
const [showAddWidget, setShowAddWidget] = useState(false);
```

Add toggle handler (simplified — the debounce flush logic stays in DashboardBuilder):
```tsx
const handleToggleEdit = useCallback(() => {
  setIsEditing(prev => !prev);
}, []);

const handleAddWidget = useCallback(() => {
  if (!isEditing) setIsEditing(true);
  setShowAddWidget(true);
}, [isEditing]);
```

Pass to both components:
```tsx
<DashboardSettings
  dashboard={dashboard}
  isEditing={isEditing}
  onToggleEdit={handleToggleEdit}
  onAddWidget={handleAddWidget}
/>

<DashboardBuilder
  dashboard={dashboard}
  canEdit={dashboard.is_owner}
  isEditing={isEditing}
  onToggleEdit={handleToggleEdit}
  onAddWidget={handleAddWidget}
/>
```

Note: The DashboardBuilder still needs to handle layout save on toggle off. Keep the flush logic inside handleToggleEdit in DashboardBuilder by having it call the parent's onToggleEdit after flushing. Alternatively, have DashboardBuilder accept `isEditing` as a prop and use a `useEffect` to detect transitions from editing→locked and flush at that point.

The cleanest approach: keep `isEditing` in DashboardPage, pass it down, and have DashboardBuilder `useEffect` on `isEditing` changing from true→false to trigger the layout save flush.

## Step 4: Show "Saving..." in the header area

Add the saving indicator next to the gear icon. In DashboardPage, if `layoutMutation.isPending` (you'll need to also lift this or pass a saving state), show a small spinner or text. This is a refinement — the core requirement is moving the buttons into the gear menu.

## Step 5: Fix the empty dashboard state

In the empty state block (DashboardBuilder.tsx line 154-169), keep the "Add Your First Widget" button since there's nothing else on screen. But change it to use the same `onAddWidget` callback.

## Checkpoint

```bash
cd frontend && npx tsc --noEmit
```
