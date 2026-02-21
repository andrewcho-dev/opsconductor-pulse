# Task 3: Finalize RLS Documentation

## Context

After Tasks 1 and 2, the RLS inventory file may have entries that were updated. This task finalizes the documentation to reflect the fixed state.

## Actions

1. Read `docs/architecture/rls-inventory.md`.

2. Update any tables that were fixed in Task 2 from `GAP` to `PROTECTED`.

3. For every `EXEMPT` table, ensure the Notes column explains WHY it is exempt. If any Notes are empty, fill them in.

4. Add a summary section at the top of the file:
   ```markdown
   ## Summary

   | Status | Count |
   |--------|-------|
   | PROTECTED | N |
   | EXEMPT | N |
   | REVIEW | N |
   | GAP (unfixed) | 0 |

   All tables with tenant data are now protected by RLS. Tables listed as EXEMPT
   contain no tenant-specific data and are intentionally excluded.
   ```

5. Add instructions for future developers:
   ```markdown
   ## Adding New Tables

   When creating a new table that contains tenant data:
   1. Always add `tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE`
   2. Always add `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;`
   3. Always add the standard `tenant_isolation` policy (see existing tables for the pattern)
   4. Add the table to this inventory file with status PROTECTED
   ```

6. Commit the document to the repository.

## Verification

The `docs/architecture/rls-inventory.md` file has:
- Zero rows with status `GAP`
- All `EXEMPT` rows have a populated Notes column
- A summary section showing total counts
