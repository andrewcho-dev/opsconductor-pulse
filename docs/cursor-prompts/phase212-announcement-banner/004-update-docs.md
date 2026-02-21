# Task 4: Update Documentation

## Files to update
- `docs/development/frontend.md`
- `docs/features/` — create or update a broadcasts/announcements doc if relevant

## What to do
1. Read `docs/development/frontend.md`
2. Add section describing the AnnouncementBanner component:
   - How it works (fetches from /api/v1/customer/broadcasts/banner)
   - Dismiss behavior (localStorage key: dismissed_banner_{id})
   - Severity types and colors
3. Update YAML frontmatter: `last-verified: 2026-02-21`, add `212` to phases array
