Find every icon-only button in the frontend that is missing an accessible name.

Run this to find the offenders:

```bash
grep -rn 'size="icon"' frontend/src/ --include="*.tsx" -l | xargs grep -L 'aria-label'
```

That gives you every file that has icon-sized buttons but no aria-label anywhere in the file. Read each one and find the specific buttons.

For each icon-only button (a button containing only an icon component with no visible text), add an `aria-label` that describes the action:

```tsx
// Before
<Button variant="ghost" size="icon" onClick={handleDelete}>
  <Trash2 className="h-4 w-4" />
</Button>

// After
<Button variant="ghost" size="icon" onClick={handleDelete} aria-label="Delete device">
  <Trash2 className="h-4 w-4" />
</Button>
```

The label should describe the action, not the icon. "Delete device" not "trash icon". "Close dialog" not "X button".

Priority files to fix first (highest user impact):
- `frontend/src/components/layout/AppHeader.tsx` — search, notifications, user menu buttons
- `frontend/src/features/devices/` — any action buttons in the device list
- `frontend/src/features/alerts/` — acknowledge, close, silence buttons

After fixing, rerun the grep to confirm zero files remain without aria-label on icon buttons.
