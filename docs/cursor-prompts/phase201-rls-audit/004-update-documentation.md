# Task 4: Update Architecture Documentation

## Context

Phase 201 produced a complete RLS inventory and fixed any gaps. The architecture documentation must reference this.

## Files to Update

| File | What Changed |
|------|-------------|
| `docs/architecture/tenant-isolation.md` | Add link to the new `rls-inventory.md`. Update the RLS section to state coverage is now 100% for tenant data tables, with a maintained inventory file. |

## For Each File

1. Read the current content.
2. In the RLS section, add:
   - A reference to `docs/architecture/rls-inventory.md` as the authoritative table list
   - A note that new tables must follow the documented pattern
   - The current coverage status (X protected, Y exempt, 0 gaps)
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-20`
   - Add `201` to the `phases` array
   - Add `db/migrations/104_rls_gap_fixes.sql` to `sources`
4. Verify no stale information remains (e.g., "72% coverage" claims from earlier).
