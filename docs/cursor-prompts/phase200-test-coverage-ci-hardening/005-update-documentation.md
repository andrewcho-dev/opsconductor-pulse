# Task 5: Update Documentation

## Context

Phase 200 expanded coverage to more microservices, fixed skipped tests, strengthened integration assertions, and made MyPy blocking.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/development/testing.md` | Update coverage targets: list which services are now in scope, their thresholds, and the plan to raise them. Document that MyPy is now a blocking CI check. |

## For Each File

1. Read the current content.
2. Update the coverage section to list all services now in scope with their thresholds.
3. Add a note that integration tests must assert specific status codes and validate response body shape.
4. Add a note that MyPy is enforced (with baseline if applicable).
5. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `200` to the `phases` array
6. Verify no stale information remains.
