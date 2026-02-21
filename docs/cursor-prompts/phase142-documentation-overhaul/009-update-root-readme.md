# Task 9: Update Root README.md

## Context

The root `README.md` has several inaccuracies:
- References `dispatcher/` and `delivery_worker/` services (deleted in Phase 138)
- Documentation section links to old flat files (now deleted/reorganized)
- Repository structure section lists stale directory descriptions
- Says "phases 1–92" for cursor-prompts (141 phases exist)

## Action

Rewrite `README.md` with accurate content. Keep the same general structure but fix all inaccuracies and update the documentation links.

## Specific Changes

### 1. Repository Structure — remove deleted services, add current ones

**Remove these lines:**
```
  dispatcher/         # Alert → delivery job routing (legacy pipeline)
  delivery_worker/    # Webhook/SNMP/email/MQTT delivery (legacy pipeline)
  maintenance/        # DB housekeeping
```

**Update ops_worker description:**
```
  ops_worker/         # Health monitoring, metrics collection, background jobs
                      #   (escalation, reports, export, OTA, certificates, commands)
```

**Update cursor-prompts line:**
```
  cursor-prompts/     # Phase-by-phase implementation history (phases 1–142)
```

**Add subscription_worker if missing from the listing.**

### 2. Documentation section — update all links

Replace the current documentation table with links to the new structure:

```markdown
## Documentation

All documentation lives in the [`docs/`](docs/index.md) directory, organized by topic:

| Section | What |
|---------|------|
| [Architecture](docs/architecture/overview.md) | System design, service map, tenant isolation |
| [API Reference](docs/api/overview.md) | Endpoints, authentication, Pulse Envelope spec |
| [Services](docs/services/ui-iot.md) | Per-service configuration and internals |
| [Features](docs/features/alerting.md) | Alerting, integrations, devices, dashboards, billing |
| [Operations](docs/operations/deployment.md) | Deployment, runbook, database, monitoring, security |
| [Development](docs/development/getting-started.md) | Getting started, testing, frontend, conventions |

Full index: [`docs/index.md`](docs/index.md)
```

### 3. Outbound Notifications section — update to current

Replace:
```markdown
### Outbound Notifications
- **Legacy delivery pipeline**: Webhook, SNMP (v2c/v3), Email (SMTP), MQTT
- **Phase 91+ routing engine**: Slack, PagerDuty (Events API v2), Microsoft Teams, generic HTTP
```

With:
```markdown
### Outbound Notifications
- Slack, PagerDuty (Events API v2), Microsoft Teams, generic HTTP webhook
- Per-channel routing rules with severity filter, alert type filter, and throttle
- HMAC signing for generic webhooks
```

(Remove the "legacy delivery pipeline" line — it no longer exists.)

### 4. Running Tests section — update commands

Update to match the current test invocation:

```markdown
## Running Tests

```bash
# Unit tests
pytest tests/unit/ -m unit -q

# With coverage
pytest -o addopts='' tests/unit/ -m unit --cov=services --cov-report=term-missing -q

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build
```

See [docs/development/testing.md](docs/development/testing.md) for full testing guide.
```

### 5. Applying Migrations section — update

```markdown
## Applying Migrations

```bash
# Apply all pending migrations (idempotent, versioned runner)
python db/migrate.py
```

See [docs/operations/database.md](docs/operations/database.md) for the full migration index (84 migrations).
```

## Verification

After updating README.md:
- [ ] No references to `dispatcher/` or `delivery_worker/`
- [ ] All doc links point to files that exist in the new structure
- [ ] Repository structure matches actual filesystem
- [ ] No "legacy pipeline" references
