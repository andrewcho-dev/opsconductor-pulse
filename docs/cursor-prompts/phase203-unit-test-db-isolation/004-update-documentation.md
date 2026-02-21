# Task 4: Update Documentation

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/development/testing.md` | Add rule: unit tests must never make real DB connections. Mock at the route/dependency level. Tests requiring a real DB are integration tests. |
| `docs/api/websocket.md` | Remove any mention of `?token=` as an auth method. Only `?ticket=` is valid now. |

## For Each File

1. Read the current content.
2. Update the relevant sections.
3. Update YAML frontmatter: set `last-verified` to `2026-02-20`, add `203` to `phases` array.
4. Verify no stale information remains.
