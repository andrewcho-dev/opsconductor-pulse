# Task 6: Expand Operations Documentation

## Context

Operations documentation is minimal — just `RUNBOOK.md` (~200 lines) and `SANITY_TEST_CHECKLIST.md` (phases 80-83 only). Need 5 comprehensive operations docs.

## Actions

### File 1: `docs/operations/deployment.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - compose/docker-compose.yml
  - compose/.env
  - compose/.env.example
  - compose/caddy/Caddyfile
phases: [114, 115, 139, 142]
---
```

**Content — read the actual compose files to build this:**

- Quick start (from README.md)
- Docker Compose service list (all services in docker-compose.yml)
- Environment variables reference: read `compose/.env.example` and list every variable with its purpose and default
- Caddy TLS configuration
- Production checklist:
  - Replace default passwords (PG_PASS, KEYCLOAK_ADMIN_PASSWORD, ADMIN_KEY)
  - Configure CORS_ORIGINS for production domains
  - Set ENV=PROD
  - Configure real TLS certificates
  - Set up external SMTP for email notifications
  - Configure backup strategy
- Profiles: `--profile simulator` for device simulator
- Volume mounts and data persistence
- Rebuilding after changes (from RUNBOOK.md)
- Merge the sanity test checklist content (from SANITY_TEST_CHECKLIST.md) into a "Post-Deployment Verification" section

**Structure:**
```markdown
# Deployment
> Docker Compose setup, environment configuration, and production checklist.

## Quick Start
## Docker Compose Services
## Environment Variables
## TLS Configuration
## Profiles
## Data Persistence
## Rebuilding After Changes
## Production Checklist
## Post-Deployment Verification
## See Also
```

### File 2: `docs/operations/runbook.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - compose/docker-compose.yml
phases: [45, 114, 142]
---
```

**Content — expand from current RUNBOOK.md:**

- Service health checks: how to verify each service is running
- Log inspection: `docker compose logs -f <service>`
- Common failure scenarios and resolution:
  - Keycloak not starting (DB not ready)
  - PgBouncer connection issues
  - MQTT broker TLS failures
  - Ingest backpressure (queue full)
  - Evaluator falling behind (POLL_SECONDS tuning)
  - Frontend build failures
  - Migration failures
- Restart procedures
- Emergency procedures (service crash loops)
- Performance tuning knobs (from ARCHITECTURE.md operational knobs section)

**Structure:**
```markdown
# Runbook
> Troubleshooting guide and operational procedures.

## Service Health Checks
## Log Inspection
## Common Issues
### Keycloak
### PostgreSQL / PgBouncer
### MQTT Broker
### Ingestion Pipeline
### Evaluator
### Frontend
## Restart Procedures
## Performance Tuning
## Emergency Procedures
## See Also
```

### File 3: `docs/operations/database.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - db/migrate.py
  - db/migrations/
phases: [20, 21, 34, 137, 142]
---
```

**Content:**

- Database architecture: PostgreSQL 15 + TimescaleDB extension
- PgBouncer connection pooling configuration
- Schema overview: list ALL tables grouped by domain (devices, alerts, telemetry, subscriptions, integrations, users/auth, system)
- Migration system:
  - How to run: `python db/migrate.py` (idempotent, versioned)
  - Manual: `psql -f db/migrations/NNN_name.sql`
  - Migration index: **list ALL 84 migrations** (000 through 098) — read `db/migrations/` directory listing to build this table. The current `db/README.md` only goes to 040, which is incomplete.
- TimescaleDB specifics: hypertables (telemetry, system_metrics), compression policies, retention policies
- Backup/restore guidance
- Connection string format

**Structure:**
```markdown
# Database
> PostgreSQL + TimescaleDB schema, migrations, and maintenance.

## Architecture
## Connection Pooling (PgBouncer)
## Schema Overview
### Device & Fleet Tables
### Alert Tables
### Telemetry Tables
### Subscription & Billing Tables
### Integration Tables
### User & Auth Tables
### System Tables
## Migrations
### Running Migrations
### Migration Index
## TimescaleDB
### Hypertables
### Compression Policies
### Retention Policies
## Backup & Restore
## See Also
```

**Critical:** Read `ls db/migrations/*.sql` output to list all 84 migrations. Do NOT copy from `db/README.md` which stops at 040.

### File 4: `docs/operations/monitoring.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - compose/prometheus/prometheus.yml
  - compose/prometheus/alert_rules.yml
  - compose/grafana/provisioning/
  - compose/grafana/dashboards/
phases: [58, 102, 139, 142]
---
```

**Content — read the Prometheus and Grafana config files:**

- Prometheus setup: scrape configuration, targets, scrape interval
- Alert rules: read `compose/prometheus/alert_rules.yml` and document each rule
- Grafana dashboards: list all pre-provisioned dashboards from `compose/grafana/dashboards/` directory:
  - api-overview.json
  - service-health.json
  - device-fleet.json
  - alert-pipeline.json
  - database.json
  - auth-security.json
- Health endpoints: list every /health or /healthz endpoint across all services
- Prometheus metrics: list key custom metrics exposed by services (from shared/metrics.py)
- Access: Prometheus on port 9090, Grafana on port 3001

**Structure:**
```markdown
# Monitoring
> Prometheus metrics, Grafana dashboards, and health endpoints.

## Overview
## Prometheus
### Configuration
### Scrape Targets
### Alert Rules
## Grafana
### Access
### Pre-Provisioned Dashboards
## Health Endpoints
## Custom Metrics
### Ingestion Metrics
### Evaluator Metrics
### Database Pool Metrics
### Processing Duration Metrics
## See Also
```

### File 5: `docs/operations/security.md`

```yaml
---
last-verified: 2026-02-17
sources:
  - services/ui_iot/middleware/auth.py
  - compose/mosquitto/mosquitto.tls.conf
  - compose/mosquitto/acl.conf
  - compose/caddy/Caddyfile
phases: [36, 97, 110, 112, 113, 114, 115, 120, 131, 142]
---
```

**Content:**

- Authentication: Keycloak OIDC/PKCE, JWT validation, role-based access
- Secrets management: which secrets exist, where they're configured, rotation guidance
- TLS: Caddy auto-TLS for HTTPS, Mosquitto TLS for MQTT (device certificates)
- MQTT ACLs: topic-level access control per tenant
- RBAC: role hierarchy (customer → tenant-admin → operator → operator-admin)
- Row-Level Security: PostgreSQL RLS policies enforcing tenant isolation
- SSRF protection: URL validation for webhook destinations (blocks internal IPs in PROD)
- CSRF protection: cookie + header token
- Rate limiting: per-tenant and per-device rate limits
- Audit logging: operator access audit, system audit log
- X.509 device certificates: CA management, CRL

**Structure:**
```markdown
# Security
> Secrets management, TLS, RBAC, and hardening.

## Authentication
## Secrets Management
## TLS
### HTTPS (Caddy)
### MQTT (Mosquitto)
### Device Certificates (X.509)
## Authorization
### Role-Based Access Control
### Row-Level Security (PostgreSQL)
### MQTT ACLs
## API Security
### SSRF Protection
### CSRF Protection
### Rate Limiting
## Audit Logging
## See Also
```

## Accuracy Rules

- Read the actual config files (prometheus.yml, alert_rules.yml, Caddyfile, mosquitto.tls.conf, acl.conf) before writing.
- The migration index MUST list all 84 migrations from the db/migrations/ directory.
- Grafana dashboard names must match the actual JSON files in compose/grafana/dashboards/.
