# Phase 145 — UI Pattern Standardization

## Goal

Eliminate inconsistent UI element choices across the app by defining and enforcing a convention rulebook for actions, navigation, modals, and controls.

## Problem Statement

The app was built across 140+ phases without a UI pattern rulebook. The result:
- 6 different patterns for page header actions
- 4 different patterns for table row actions
- 4 different naming conventions for "Create" buttons
- 4 different approaches to detail page navigation
- Breadcrumbs on only 2 of 8 detail pages
- Raw HTML `<button>` used alongside the `<Button>` component
- One custom div-based modal instead of Shadcn Dialog
- Dashboard "Edit Layout" as a standalone content button instead of a gear menu item
- `window.confirm()` mixed with `AlertDialog` for destructive actions
- Only 2 of 8 form modals have unsaved-change protection

## The Convention Rulebook

| Pattern | Rule |
|---------|------|
| Primary create action | `<Button>` with `Plus` icon + `"Add {Noun}"` label. In PageHeader `action` prop. |
| Secondary page actions | `<Button variant="outline">` in flex container next to primary. |
| Settings/config actions | Gear icon `<DropdownMenu>` — never a standalone button. |
| Table row actions (1-2) | `<Button variant="ghost" size="sm">` with icon + short label |
| Table row actions (3+) | `MoreHorizontal` `<DropdownMenu>`. Destructive after separator. |
| Navigate to detail | `<Link>` on the name/ID column text. No row click, no separate button. |
| All detail pages | Must have breadcrumbs via PageHeader `breadcrumbs` prop. |
| All pages | Must use `<PageHeader>` component. No custom header layouts. |
| All modals | Shadcn `<Dialog>`. Props: `open` + `onOpenChange`. |
| All form modals | Must use `useFormDirtyGuard` for unsaved-change protection. |
| Destructive confirms | Always `<AlertDialog>`. Never `window.confirm()`. |
| State naming | `const [open, setOpen]` for simple. `const [editing, setEditing]` for compound. |

## Execution Order

| Task | File | Description |
|------|------|-------------|
| 001 | `001-fix-dashboard-actions.md` | Move Edit Layout into gear menu, clean up controls |
| 002 | `002-standardize-page-headers.md` | All pages must use PageHeader. Fix raw HTML buttons. |
| 003 | `003-standardize-create-buttons.md` | All create/add buttons → `"Add {Noun}"` with Plus icon |
| 004 | `004-add-breadcrumbs.md` | Add breadcrumbs to all 6 detail pages missing them |
| 005 | `005-standardize-table-actions.md` | Normalize row actions to one of two patterns |
| 006 | `006-fix-alert-list-controls.md` | Fix Alert List raw HTML, custom tabs → proper components |
| 007 | `007-migrate-campaign-dialog.md` | CreateCampaignDialog: custom div → Shadcn Dialog |
| 008 | `008-fix-confirm-dialogs.md` | Replace `confirm()` with AlertDialog everywhere |
| 009 | `009-verify-and-fix.md` | Build verification and regression fix |
| 010 | `010-update-documentation.md` | Document the convention rulebook in frontend.md |

## Rules

- Run `cd frontend && npx tsc --noEmit` after EVERY task
- Always use `<Button>` component, never raw `<button>` HTML
- Always use `<Dialog>` component, never custom div overlays
- Always use `<AlertDialog>` for destructive confirms, never `window.confirm()`
- Keep existing functionality — only change how the UI elements are presented
