# Task 9: Update Documentation

## Context

Phase 143 established the design system foundation. Update the relevant docs.

## Files to Update

### 1. `docs/development/frontend.md`

Add a "Design System" section covering:
- Spacing scale (4px base grid, space-y-6 for page sections, gap-4 for card grids)
- Typography hierarchy (h1=text-xl, h2=text-base, h3=text-sm, body=text-sm, small=text-xs)
- Border radius rule (rounded-lg for cards, rounded-md for inputs/buttons)
- Card containment (1px border, no shadow)
- Background strategy (light gray page, white cards, dark mode unchanged)
- Status color tokens (--status-online, --status-critical, etc.)
- 12px minimum text size rule
- Page layout rule: top-level wrapper is always space-y-6, no extra padding wrappers

Update the YAML frontmatter:
- Set `last-verified` to today's date
- Add `143` to the `phases` array

### 2. `docs/index.md`

No structural changes needed — `development/frontend.md` is already linked.

Update the YAML frontmatter:
- Set `last-verified` to today's date
- Add `143` to the `phases` array

## Verify

```bash
grep "last-verified" docs/development/frontend.md
grep "143" docs/development/frontend.md
```
