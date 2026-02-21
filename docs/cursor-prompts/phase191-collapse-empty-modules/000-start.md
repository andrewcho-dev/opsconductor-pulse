# Phase 191 — Collapse Empty Expansion Modules

## Problem

Two issues on the Data tab:

1. **Empty slots shown for no reason** — All 4 expansion module slots have 0 modules assigned, yet the section lists every empty slot. The user doesn't need to see empty slots unless they're actively managing modules.
2. **Full-width stretching** — Each slot row uses `ml-auto` in a full-width flex container, pushing the count/button to the far right with ~800px of dead whitespace in the middle.

## Fix

1. When **no modules are assigned to any slot**, collapse the entire section behind a `<details>` element (closed by default). Summary line: "Expansion Modules — N slots available".
2. When **any modules ARE assigned**, show the section open by default.
3. Constrain the slot list to `max-w-2xl` so rows don't stretch across the full page width.

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-collapse-modules.md` | Fix expansion modules section |
| 2 | `002-update-docs.md` | Documentation updates |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- When 0 modules assigned: section is collapsed, shows one-line summary
- When modules assigned: section is open, slot list visible
- Slot list constrained to ~672px (max-w-2xl), no full-width stretching
- Click to expand still shows all slots with Assign buttons
