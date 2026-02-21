# Task 2: Consolidate Architecture Documentation

## Context

Four separate docs cover overlapping architecture topics:
- `docs/ARCHITECTURE.md` (~440 lines) — Full system architecture, data flow, workers, security
- `docs/REFERENCE_ARCHITECTURE.md` (~650 lines) — Big-picture view with ASCII diagrams
- `docs/PROJECT_MAP.md` (~196 lines) — Quick-reference topology, tables, flows
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (~500 lines) — Auth model, tenant isolation, RLS
- `docs/TENANT_CONTEXT_CONTRACT.md` (~65 lines) — Tenant identity invariants

These get consolidated into 3 files:

| Old Files | New File | What It Covers |
|-----------|----------|----------------|
| ARCHITECTURE.md + REFERENCE_ARCHITECTURE.md | `architecture/overview.md` | One authoritative system architecture |
| PROJECT_MAP.md | `architecture/service-map.md` | Quick-reference topology and data flows |
| CUSTOMER_PLANE_ARCHITECTURE.md + TENANT_CONTEXT_CONTRACT.md | `architecture/tenant-isolation.md` | Auth, tenant context, RLS, isolation |

## Actions

### File 1: `docs/architecture/overview.md`

Create this file by consolidating ARCHITECTURE.md and REFERENCE_ARCHITECTURE.md. Follow these rules:

1. **Start with the YAML frontmatter:**
```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/app.py
  - services/evaluator_iot/evaluator.py
  - services/ingest_iot/ingest.py
  - services/ops_worker/main.py
  - compose/docker-compose.yml
phases: [1, 23, 43, 88, 98, 99, 122, 128, 138, 142]
---
```

2. **Use REFERENCE_ARCHITECTURE.md as the structural backbone** — it has the most complete view.

3. **Merge in unique content from ARCHITECTURE.md** — specifically the worker task details (escalation_worker, report_worker, batch_writer, audit_logger), the notification routing engine description, and operational knobs.

4. **Remove all references to deleted services:**
   - `dispatcher` service — removed in Phase 138
   - `delivery_worker` service — removed in Phase 138
   - The "legacy delivery pipeline" is gone. The Phase 91+ notification routing engine (in `services/ui_iot/notifications/`) is the current system.

5. **Update the ASCII architecture diagram** to reflect current services:
   - ui_iot (FastAPI)
   - ingest_iot (MQTT + HTTP)
   - evaluator_iot (rules engine)
   - ops_worker (health monitor, metrics collector, background jobs)
   - subscription_worker (lifecycle management)
   - provision_api (device provisioning)
   - Keycloak, PostgreSQL/TimescaleDB, PgBouncer, Mosquitto, Caddy
   - Prometheus + Grafana (added Phase 139)

6. **Include the technology stack table** from README.md.

7. **Structure:**
```markdown
# System Architecture
> One authoritative reference for the OpsConductor-Pulse platform architecture.

## Overview
## Architecture Diagram
## Services
### ui_iot (API Gateway + UI Backend)
### ingest_iot (Telemetry Ingestion)
### evaluator_iot (Alert Rule Engine)
### ops_worker (Background Operations)
### subscription_worker (Subscription Lifecycle)
### provision_api (Device Provisioning)
## Infrastructure
### PostgreSQL + TimescaleDB
### PgBouncer
### Keycloak
### Mosquitto (MQTT)
### Caddy (Reverse Proxy)
### Prometheus + Grafana
## Data Flow
### Telemetry Ingestion Pipeline
### Alert Evaluation Loop
### Notification Routing
### Escalation Flow
## Background Workers
## Technology Stack
## Configuration
## See Also
```

### File 2: `docs/architecture/service-map.md`

Create from PROJECT_MAP.md content with these changes:

1. **Add YAML frontmatter:**
```yaml
---
last-verified: 2026-02-17
sources:
  - compose/docker-compose.yml
  - compose/caddy/Caddyfile
phases: [88, 98, 138, 139, 142]
---
```

2. **Update the network topology** — remove dispatcher/delivery_worker, add Prometheus/Grafana.

3. **Update the database tables section** to reflect all 84 migrations (not just through 040).

4. **Add a port reference table:**

| Service | Internal Port | External Port | Protocol |
|---------|--------------|---------------|----------|
| ui_iot | 8000 | 443 (via Caddy) | HTTPS |
| ingest_iot | 8080 | — | HTTP (internal) |
| evaluator_iot | 8080 | — | HTTP (internal) |
| ops_worker | — | — | Background only |
| subscription_worker | — | — | Background only |
| provision_api | 8081 | 8081 | HTTP |
| Keycloak | 8080 | 443 (via Caddy) | HTTPS |
| PostgreSQL | 5432 | 5432 | TCP |
| PgBouncer | 6432 | — | TCP |
| Mosquitto | 1883/9001 | 8883 (TLS) | MQTT/WS |
| Prometheus | 9090 | 9090 | HTTP |
| Grafana | 3000 | 3001 | HTTP |

5. **Structure:**
```markdown
# Service Map
> Quick-reference topology, ports, dependencies, and data flows.

## Network Topology
## Port Reference
## Service Dependencies
## Core Data Flow
## Database Tables (by domain)
## API Route Mapping
## See Also
```

### File 3: `docs/architecture/tenant-isolation.md`

Create by merging CUSTOMER_PLANE_ARCHITECTURE.md and TENANT_CONTEXT_CONTRACT.md:

1. **Add YAML frontmatter:**
```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/middleware/auth.py
  - services/ui_iot/middleware/tenant.py
  - services/ui_iot/db/pool.py
phases: [4, 36, 43, 96, 97, 142]
---
```

2. **Use CUSTOMER_PLANE_ARCHITECTURE.md as the backbone** — it's the most detailed.

3. **Inline the 10 invariants from TENANT_CONTEXT_CONTRACT.md** as a "Tenant Context Invariants" section.

4. **Structure:**
```markdown
# Tenant Isolation
> Authentication model, tenant context propagation, and database enforcement.

## Overview
## Authentication Model
### Keycloak Integration
### JWT Claims
### User Roles
## Tenant Context Propagation
### HTTP → App (middleware)
### App → DB (SET LOCAL)
## Database Enforcement (RLS)
## Operator Access Model
## Tenant Context Invariants
## UI Route Binding
## Device Identity
## Rate Limiting
## Failure Modes
## See Also
```

## Accuracy Checks

After writing each file, verify:
- [ ] No references to `dispatcher` or `delivery_worker` services
- [ ] Notification routing described as Phase 91+ engine (Slack/PD/Teams/HTTP), not legacy webhook/SNMP/email delivery jobs
- [ ] Prometheus + Grafana included in infrastructure sections
- [ ] All cross-links use correct relative paths (e.g., `../services/ui-iot.md`)
