# Task 11: Update CLAUDE.md — Documentation Maintenance Rule

## Context

This is **Maintenance Mechanism 1**: Add a hard constraint to CLAUDE.md requiring every future phase to identify affected documentation and include a doc-update task.

## Action

Edit `/home/opsconductor/simcloud/CLAUDE.md` to add a new section after "## Task Tracking".

### Add this section at the end of CLAUDE.md:

```markdown
## Documentation Maintenance (NEVER skip)

Every phase that changes behavior, adds features, modifies APIs, or alters configuration MUST:

1. **Identify affected docs** — List which files in `docs/` are impacted by this phase's changes
2. **Include a documentation update task** — The final numbered prompt in every phase MUST be a doc-update task
3. **Update freshness metadata** — Bump `last-verified` date and add the phase number to the `phases` array in the YAML frontmatter of every doc touched

### Doc update task template

The final prompt in every phase should follow this pattern:

```
# Task N: Update Documentation

## Files to Update
- docs/[section]/[file].md — [what changed]

## For Each File
1. Read the current content
2. Update the relevant sections to reflect this phase's changes
3. Update the YAML frontmatter:
   - Set `last-verified` to today's date
   - Add this phase number to the `phases` array
   - Add/update `sources` if new source files are relevant
4. Verify no stale information remains

## Verify
grep -c "last-verified: YYYY-MM-DD" docs/[section]/[file].md
```

### Documentation structure

All project documentation lives in `docs/` with this hierarchy:

```
docs/
├── index.md              ← Hub linking to everything
├── architecture/         ← System design, service map, tenant isolation
├── api/                  ← Endpoint references by audience
├── services/             ← Per-service configuration and internals
├── features/             ← Feature area guides
├── operations/           ← Deployment, runbook, database, monitoring, security
├── development/          ← Getting started, testing, frontend, conventions
├── reference/            ← Archived strategic/planning docs
├── diagrams/             ← Mermaid sources + rendered images
└── cursor-prompts/       ← Phase-by-phase implementation history
```

### Freshness metadata format

Every doc (except cursor-prompts and reference/) uses this YAML frontmatter:

```yaml
---
last-verified: YYYY-MM-DD
sources:
  - path/to/key/source.py
phases: [1, 23, 45, ...]
---
```
```

## Why

Without this rule, documentation will drift out of sync with the codebase — exactly what happened with the pre-Phase 142 docs. Making it a hard constraint in CLAUDE.md means every phase planned through this architect role will automatically include documentation maintenance.
