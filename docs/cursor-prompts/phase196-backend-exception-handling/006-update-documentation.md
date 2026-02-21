# Task 6: Update Documentation

## Context

Phase 196 fixed NATS initialization, audit logger lock contention, bare exception handlers, and duplicate definitions. These are internal reliability improvements with no external API changes.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/development/conventions.md` | Add exception handling guidelines established by this phase |

## For Each File

1. Read the current content.
2. If `docs/development/conventions.md` exists, add or update a section on exception handling:
   - Use specific exception types where possible
   - Never `pass` silently — always log
   - Infrastructure errors (DB, NATS) should be reraised, not swallowed
   - Always include `exc_info=True` and context extras in error logs
3. If the file does not exist, skip it (do not create new docs unless explicitly required).
4. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `196` to the `phases` array
5. Verify no stale information remains.
