# Phase 201 — RLS Audit and Gap Documentation

## Goal

Audit all database tables for Row-Level Security (RLS) coverage, document the intent for each table, and fix any gaps where tenant data is accessible without RLS protection.

## Current State (problem)

The security review found approximately 56 of 78 tables with RLS enabled (~72%). There is no authoritative document listing which tables intentionally bypass RLS and why. This makes it impossible to verify that multi-tenant isolation is complete.

## Target State

- Every table in the database has its RLS status explicitly recorded in a tracking document.
- Tables without RLS have a documented justification (e.g., "operator-only, no tenant data", "global config", "write-only audit log").
- Any table with tenant data but missing RLS has RLS added via a migration.
- A migration comment convention is established: tables that intentionally bypass RLS are tagged with `-- RLS: EXEMPT (reason)`.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-rls-inventory.md` | Build complete RLS status table | — |
| 2 | `002-rls-migration-gaps.md` | Write migration to enable RLS on gap tables | Step 1 |
| 3 | `003-rls-documentation.md` | Document RLS status for all tables | Steps 1–2 |
| 4 | `004-update-documentation.md` | Update architecture docs | Step 3 |

## Verification

```bash
# Check the database directly (requires running DB):
psql $DATABASE_URL -c "
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
"
# Every table should have rowsecurity = true OR appear in the exemptions doc

# No undocumented exempt tables
grep -c 'RLS: EXEMPT' db/migrations/*.sql
```

## Documentation Impact

- `docs/architecture/tenant-isolation.md` — Add complete RLS coverage table
