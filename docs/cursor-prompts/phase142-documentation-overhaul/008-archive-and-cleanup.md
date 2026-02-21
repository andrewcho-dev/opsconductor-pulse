# Task 8: Archive Old Files and Clean Up

## Context

After Tasks 2-7 have created the new organized docs, the old flat files in `docs/` need to be moved or deleted. The content has been consolidated into the new structure — keeping the old files would create confusion about which is authoritative.

## Actions

### 1. Move strategic memos to `docs/reference/`

These are planning documents, not technical references. Move them:

```bash
mv docs/OpsConductor-Pulse_Software_Strategy_Gap_Analysis_Priorities_2026-02-12.md \
   docs/reference/gap-analysis-2026-02-12.md

mv docs/Reply_to_OpsConductor-Pulse_Software_Strategy_Gap_Analysis_Priorities_2026-02-12.md \
   docs/reference/gap-analysis-reply-2026-02-12.md

mv docs/Reply_to_OpsConductor-Pulse_Software_Strategy_Gap_Analysis_Priorities_2026-02-14.md \
   docs/reference/gap-analysis-reply-2026-02-14.md

mv docs/api-migration-v2-to-customer.md \
   docs/reference/api-migration-v2-to-customer.md
```

### 2. Delete old docs that have been consolidated

Every one of these has been fully merged into the new structure. Delete them:

```bash
rm docs/ARCHITECTURE.md
rm docs/REFERENCE_ARCHITECTURE.md
rm docs/PROJECT_MAP.md
rm docs/CUSTOMER_PLANE_ARCHITECTURE.md
rm docs/TENANT_CONTEXT_CONTRACT.md
rm docs/API_REFERENCE.md
rm docs/INTEGRATIONS_AND_DELIVERY.md
rm docs/PULSE_ENVELOPE_V1.md
rm docs/RUNBOOK.md
```

### 3. Delete root-level docs that have been consolidated

```bash
rm SANITY_TEST_CHECKLIST.md
```

The sanity test checklist content has been merged into `docs/operations/deployment.md` (Post-Deployment Verification section).

### 4. Delete stale subdirectory docs

```bash
rm tests/coverage_requirements.md
```

Coverage requirements have been merged into `docs/development/testing.md`.

### 5. Replace `frontend/README.md` with a pointer

Replace the generic Vite boilerplate `frontend/README.md` with a short redirect:

```markdown
# Frontend

See [docs/development/frontend.md](../docs/development/frontend.md) for complete frontend documentation.
```

### 6. Update `db/README.md` with a pointer

Replace `db/README.md` content with a pointer to the comprehensive database doc:

```markdown
# Database Migrations

See [docs/operations/database.md](../docs/operations/database.md) for the complete migration index, schema overview, and database operations guide.

## Quick Reference

```bash
# Apply all pending migrations (idempotent)
python db/migrate.py

# Apply a specific migration manually
psql "$DATABASE_URL" -f db/migrations/NNN_name.sql
```
```

### 7. Verify no broken references

After all moves/deletes, search for references to old filenames:

```bash
grep -r "ARCHITECTURE.md\|REFERENCE_ARCHITECTURE.md\|PROJECT_MAP.md\|CUSTOMER_PLANE_ARCHITECTURE.md\|TENANT_CONTEXT_CONTRACT.md\|API_REFERENCE.md\|INTEGRATIONS_AND_DELIVERY.md\|PULSE_ENVELOPE_V1.md\|RUNBOOK.md" \
  --include="*.md" docs/ README.md
```

Fix any found references to point to the new paths.

## What Stays

- `docs/diagrams/` — kept as-is (Mermaid sources + renders)
- `docs/cursor-prompts/` — kept as-is (implementation history)
- `CLAUDE.md` — operational config (updated in Task 11)
- `.github/` files — GitHub-specific, stay in place
- `.windsurf/` files — Windsurf-specific, stay in place
