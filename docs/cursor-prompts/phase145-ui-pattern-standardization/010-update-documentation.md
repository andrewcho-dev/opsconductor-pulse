# Task 10: Update Documentation

## Context

Phase 145 established a UI pattern convention rulebook. Document it so future development follows these rules.

## Files to Update

### 1. `docs/development/frontend.md`

Add a **"UI Pattern Conventions"** section after the Design System section. Include:

#### Page Header Actions
- All pages MUST use the `<PageHeader>` component
- Primary create action: `<Button>` with `Plus` icon + `"Add {Noun}"` label in the `action` prop
- Secondary actions: `<Button variant="outline">` in flex container
- Settings/config: Gear icon `<DropdownMenu>` — never standalone buttons

#### Table Row Actions
- 1-2 actions: `<Button variant="ghost" size="sm">` with icon + short label
- 3+ actions: `MoreHorizontal` `<DropdownMenu>` with destructive items after separator
- Navigate to detail: `<Link>` on name/ID column text — no separate View buttons

#### Breadcrumbs
- ALL detail pages MUST have breadcrumbs via PageHeader `breadcrumbs` prop
- Format: `[{ label: "Parent", href: "/parent" }, { label: itemName }]`
- No standalone "Back" buttons

#### Modals & Dialogs
- ALL modals use Shadcn `<Dialog>` component — no custom div overlays
- Props: `open` + `onOpenChange` — not `isOpen`, `onClose`, etc.
- State: `const [open, setOpen] = useState(false)` for simple boolean
- State: `const [editing, setEditing] = useState<T | null>(null)` for compound
- ALL form modals should use `useFormDirtyGuard` for unsaved-change protection
- Destructive confirms: `<AlertDialog>` — never `window.confirm()`

#### Prohibited Patterns
- Raw `<button>` HTML — always use `<Button>` component
- Raw `<div className="fixed inset-0">` overlays — always use `<Dialog>`
- `window.confirm()` — always use `<AlertDialog>`
- Custom page header layouts — always use `<PageHeader>`
- Standalone "Back" buttons — always use breadcrumbs
- "New" or "Create" verbs in button labels — always use "Add"

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-17)
- Add `145` to the `phases` array

### 2. `docs/index.md`

Update YAML frontmatter:
- Set `last-verified` to today's date (2026-02-17)
- Add `145` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "145" docs/development/frontend.md
```
