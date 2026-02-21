# Phase 142 — Documentation Overhaul

## Goal

Consolidate all project documentation into a single, hierarchical `docs/` tree with consistent structure, 100% accuracy against the current codebase, and built-in mechanisms to keep docs current as future phases land.

## Current State (problems)

- 14 docs dumped flat in `docs/` with overlapping topics (4 architecture docs, no cross-referencing)
- Strategic memos mixed with technical references
- No per-service documentation (7 backend services undocumented)
- No developer onboarding guide
- `db/README.md` lists migrations only through 040 (84 exist)
- Root `README.md` references deleted services (`dispatcher/`, `delivery_worker/`)
- `frontend/README.md` is generic Vite boilerplate
- `INTEGRATIONS_AND_DELIVERY.md` describes "legacy" pipeline without noting Phase 138 removal
- No monitoring/observability docs despite Phase 139 adding Prometheus+Grafana
- `cursor-prompts/` says "phases 1–92" but 141 phases exist
- Empty `docs/specs/` directory
- No mechanism to keep docs updated as phases land

## Target Structure

```
docs/
├── index.md                         ← Documentation hub / table of contents
├── architecture/
│   ├── overview.md                  ← Consolidated system architecture (one source of truth)
│   ├── service-map.md               ← Service topology, ports, dependencies, data flow
│   └── tenant-isolation.md          ← Merged TENANT_CONTEXT_CONTRACT + CUSTOMER_PLANE
├── api/
│   ├── overview.md                  ← Auth model, versioning, envelope spec (v1)
│   ├── customer-endpoints.md        ← Customer-facing REST API
│   ├── operator-endpoints.md        ← Operator/admin REST API
│   ├── ingest-endpoints.md          ← Device telemetry HTTP + MQTT ingestion
│   ├── provisioning-endpoints.md    ← Device provisioning API
│   └── websocket-protocol.md        ← WS/SSE realtime specs
├── services/
│   ├── ui-iot.md
│   ├── evaluator.md
│   ├── ingest.md
│   ├── ops-worker.md
│   ├── subscription-worker.md
│   ├── provision-api.md
│   └── keycloak.md
├── features/
│   ├── alerting.md
│   ├── integrations.md
│   ├── device-management.md
│   ├── dashboards.md
│   ├── billing.md
│   └── reporting.md
├── operations/
│   ├── deployment.md
│   ├── runbook.md
│   ├── database.md
│   ├── monitoring.md
│   └── security.md
├── development/
│   ├── getting-started.md
│   ├── testing.md
│   ├── frontend.md
│   └── conventions.md
├── reference/
│   ├── api-migration-v2-to-customer.md
│   ├── gap-analysis-2026-02-12.md
│   ├── gap-analysis-reply-2026-02-12.md
│   └── gap-analysis-reply-2026-02-14.md
├── diagrams/                        ← Kept as-is
└── cursor-prompts/                  ← Kept as-is (implementation history)
```

## Maintenance Mechanisms (baked in)

### Mechanism 1: CLAUDE.md rule
Prompt 011 adds a hard constraint to CLAUDE.md requiring every future phase to identify affected docs and include a documentation update task.

### Mechanism 2: Freshness metadata
Every doc gets a YAML frontmatter header with `last-verified`, `sources` (key source files), and `phases` (which phases contributed). This makes staleness visible.

### Mechanism 3: Phase template
Prompt 012 creates a standard phase template where the final task is always "Update documentation." Every future `000-start.md` includes this by default.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-directory-skeleton.md` | Create dir structure + index.md + doc template | — |
| 2 | `002-consolidate-architecture.md` | Merge 4 arch docs → 3 files | Step 1 |
| 3 | `003-reorganize-api-docs.md` | Split API_REFERENCE by audience | Step 1 |
| 4 | `004-write-service-docs.md` | 7 per-service docs | Steps 2-3 |
| 5 | `005-write-feature-docs.md` | 6 feature area docs | Steps 2-3 |
| 6 | `006-expand-operations-docs.md` | 5 operations docs | Steps 2-3 |
| 7 | `007-write-development-docs.md` | 4 development docs | Steps 2-3 |
| 8 | `008-archive-and-cleanup.md` | Move old files, delete stale ones | Steps 2-7 |
| 9 | `009-update-root-readme.md` | Rewrite README.md with new doc links | Step 8 |
| 10 | `010-cross-reference-pass.md` | Verify links, add freshness metadata | Step 9 |
| 11 | `011-update-claude-md.md` | Add doc maintenance rule to CLAUDE.md | — |
| 12 | `012-phase-template.md` | Create standard phase template with doc task | Step 11 |

## Consistent Document Structure

Every doc MUST follow this template:

```markdown
---
last-verified: YYYY-MM-DD
sources:
  - path/to/key/source1.py
  - path/to/key/source2.py
phases: [N, M, ...]
---

# Title

> One-line summary of what this document covers.

## Overview
What this is, why it matters, how it fits into the platform.

## [Topic Sections]
The substance — varies per doc type.

## Configuration
Env vars, settings, tunables (where applicable).

## Troubleshooting
Common issues and resolutions (where applicable).

## See Also
- [Related Doc 1](../relative/path.md)
- [Related Doc 2](../relative/path.md)
```

## Accuracy Rules

- Every env var documented must match what the code actually reads
- Every API endpoint must match the actual route decorator in the source
- Every service description must match the current codebase (not what existed 50 phases ago)
- The migration index must list all 84 current migrations, not stop at 040
- Deleted services (dispatcher, delivery_worker) must not be referenced as current
- The Phase 91+ notification routing engine is the current system; legacy delivery is removed
