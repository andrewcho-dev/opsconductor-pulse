# Task 5: Update Documentation

## Status: COMPLETE (applied 2026-02-21)

## Files to Update
- `docs/development/frontend.md` — update layout architecture section
- `docs/architecture/tenant-isolation.md` — no change needed (not UI layout)

## For docs/development/frontend.md
1. Read current content
2. Update or add an "App Shell Layout" section describing:
   - `AppShell` renders a flex column: `AppHeader` (full-width, h-12) on top,
     `SidebarProvider` below containing `AppSidebar` + content column
   - `AppSidebar` uses shadcn `collapsible="icon"` with `!top-12` offset to
     clear the full-width header
   - Logo in header links to `/home` (customer) or `/operator` (operator)
   - Breadcrumb auto-generates from the current route path
3. Update YAML frontmatter:
   - Set `last-verified` to 2026-02-21
   - Add 214 to the `phases` array
4. Verify no stale references to the old layout (header inside sidebar row)
