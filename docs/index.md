---
last-verified: 2026-02-19
sources:
  - docs/development/frontend.md
  - docs/features/device-management.md
phases: [142, 143, 144, 145, 146, 147, 148, 163, 165, 170, 173, 174, 175, 176, 177]
---

# OpsConductor-Pulse Documentation

> Central index for all project documentation.

## Architecture

- [System Overview](architecture/overview.md) — Services, data flow, technology choices
- [Service Map](architecture/service-map.md) — Topology, ports, dependencies, network flows
- [Tenant Isolation](architecture/tenant-isolation.md) — Auth model, RLS, context propagation

## API Reference

- [API Overview](api/overview.md) — Authentication, versioning, Pulse Envelope spec
- [Customer Endpoints](api/customer-endpoints.md) — Tenant-scoped REST API
- [Operator Endpoints](api/operator-endpoints.md) — Cross-tenant admin API
- [Ingestion Endpoints](api/ingest-endpoints.md) — HTTP + MQTT telemetry ingestion
- [Provisioning Endpoints](api/provisioning-endpoints.md) — Device provisioning admin API
- [WebSocket Protocol](api/websocket-protocol.md) — Real-time WS/SSE specifications

## Services

- [ui-iot](services/ui-iot.md) — Main API gateway and UI backend
- [evaluator](services/evaluator.md) — Alert rule evaluation engine
- [ingest](services/ingest.md) — NATS JetStream telemetry ingestion
- [route-delivery](services/route-delivery.md) — Asynchronous webhook + MQTT republish delivery
- [ops-worker](services/ops-worker.md) — Health monitoring and background jobs
- [subscription-worker](services/subscription-worker.md) — Subscription lifecycle
- [provision-api](services/provision-api.md) — Device provisioning service
- [keycloak](services/keycloak.md) — Identity provider configuration

## Features

- [Alerting](features/alerting.md) — Rules, escalation, notification channels, on-call
- [Integrations](features/integrations.md) — Webhook, SNMP, email, MQTT delivery
- [Device Management](features/device-management.md) — Provisioning, templates, modules/sensors/transports, twin, commands, OTA, Getting Started guide
- Home landing page with fleet health overview
- Hub pages: Alerts, Analytics, Updates, Notifications, Team
- Flat sidebar navigation with section labels
- Settings page with subcategory navigation (Account, Configuration, Access Control)
- [Dashboards](features/dashboards.md) — Dashboard system, widgets, TV/NOC mode
- [Billing](features/billing.md) — Subscriptions, metering, device limits
- [Reporting](features/reporting.md) — SLA reports, CSV exports

## Operations

- [Deployment](operations/deployment.md) — Docker Compose setup, env vars, production checklist
- [Kubernetes](operations/kubernetes.md) — Helm chart deployment guide
- [Managed PostgreSQL](operations/managed-postgres.md) — Managed DB migration path
- [Runbook](operations/runbook.md) — Troubleshooting, common issues, recovery procedures
- [Database](operations/database.md) — Migrations, schema overview, backup/restore
- [Monitoring](operations/monitoring.md) — Prometheus, Grafana, health endpoints, dashboards
- [Security](operations/security.md) — Secrets management, TLS, RBAC, hardening

## Development

- [Getting Started](development/getting-started.md) — Clone → run → verify (developer onboarding)
- [Testing](development/testing.md) — Strategy, running tests, coverage targets
- [Frontend](development/frontend.md) — React/Vite patterns, component library, conventions
- [Conventions](development/conventions.md) — Code style, commit format, PR process

## Reference

- [API Migration: v2 → customer](reference/api-migration-v2-to-customer.md) — Deprecation timeline and endpoint mapping
- [Gap Analysis (2026-02-12)](reference/gap-analysis-2026-02-12.md) — Strategic planning
- [Gap Analysis Reply (2026-02-12)](reference/gap-analysis-reply-2026-02-12.md) — Follow-up
- [Gap Analysis Reply (2026-02-14)](reference/gap-analysis-reply-2026-02-14.md) — Follow-up

## Implementation History

Phase-by-phase implementation prompts are archived in [cursor-prompts/](cursor-prompts/) (phases 1–142).

