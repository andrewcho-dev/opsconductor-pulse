# Task 5: Update Documentation

## Context

Phase 202 removed the deprecated `breadcrumbs` prop, introduced a structured logger, fixed `useEffect` dependency arrays, and normalized localStorage boolean handling.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/development/frontend.md` (or conventions file) | Document: (1) use `logger` from `@/lib/logger` instead of `console.*`, (2) do not put `form` object from react-hook-form directly in useEffect deps — destructure stable methods, (3) use JSON.parse/stringify for non-string localStorage values |

## For Each File

1. Read the current content.
2. If a frontend conventions or development guide exists, add the three conventions above.
3. Update YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `202` to `phases` array
4. Verify no stale information remains.

## Note on logger

The `logger` utility created in Task 2 (`frontend/src/lib/logger.ts`) is intentionally minimal. A future phase should integrate it with an error tracking service (Sentry, Datadog, etc.) when observability requirements for the frontend are defined. Do not add that integration in this phase.
