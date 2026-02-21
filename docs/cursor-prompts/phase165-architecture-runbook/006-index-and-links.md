# Task 6: Update Index and Cross-References

## Files to Modify

- `docs/index.md` — Add links to new docs, update descriptions
- Verify all `See Also` sections across modified docs

## What to Do

### 1. Update `docs/index.md`

Read the current content, then update:

**Architecture section:**
- Verify links to `architecture/overview.md`, `architecture/service-map.md`, `architecture/tenant-isolation.md`
- Update descriptions if needed (e.g., "EMQX + NATS JetStream architecture" instead of "Mosquitto-based architecture")

**Services section:**
- Add link to `services/route-delivery.md` — "Dedicated webhook and notification delivery service"
- Verify all existing service doc links are present

**Operations section:**
- Add link to `operations/kubernetes.md` (created in Phase 163) — "Kubernetes deployment guide"
- Add link to `operations/managed-postgres.md` (created in Phase 163) — "Managed PostgreSQL configuration"
- Verify links to deployment, runbook, monitoring, database, security docs

### 2. Verify cross-references

Check `See Also` sections in every doc modified in this phase. Ensure:
- `docs/architecture/overview.md` → links to service-map, tenant-isolation, API overview
- `docs/architecture/service-map.md` → links to overview, tenant-isolation, deployment
- `docs/architecture/tenant-isolation.md` → links to overview, security
- `docs/services/route-delivery.md` → links to monitoring, ingest, ui-iot
- `docs/operations/runbook.md` → links to deployment, database, monitoring, kubernetes
- `docs/operations/monitoring.md` → links to runbook, deployment, security
- `docs/operations/deployment.md` → links to kubernetes, runbook, database

### 3. Update YAML frontmatter

```yaml
---
last-verified: 2026-02-19
phases: [<existing phases>, 165]
---
```

### 4. Final verification

After all updates, scan for any remaining references to:
- "Mosquitto" (should be "EMQX" in all non-historical contexts)
- "local filesystem exports" (should be "S3/MinIO")
- Hard-coded pool sizes (should reference `PG_POOL_MIN`/`PG_POOL_MAX`)
- Missing NATS/JetStream mentions in data flow descriptions

Flag any stale references for correction.
