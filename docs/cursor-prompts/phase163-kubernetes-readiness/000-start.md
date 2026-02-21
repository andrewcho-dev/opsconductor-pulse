# Phase 163 — Kubernetes Readiness (R4)

## Goal

Make the entire stack deployable to any Kubernetes cluster (EKS, AKS, GKE, self-managed). This phase creates the deployment manifests and ensures all services are K8s-friendly.

## Prerequisites

- Phase 162 (NATS JetStream) complete

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-helm-chart-structure.md` | Create Helm chart with all services as subcharts |
| 002  | `002-health-probes.md` | Add readiness/liveness probes to all services |
| 003  | `003-horizontal-scaling.md` | HPA configs for ingest and route-delivery workers |
| 004  | `004-managed-postgres.md` | Document managed PostgreSQL migration (RDS/Cloud SQL) |
| 005  | `005-update-docs.md` | Update documentation |

## Key Decisions

- **Helm (not raw manifests)** — templated, parameterized, reusable across environments
- **Official subcharts** for EMQX (`emqx/emqx`) and NATS (`nats/nats`) — don't reinvent
- **ConfigMaps** for non-secret config, **Secrets** for credentials
- **Docker Compose kept** for local development — K8s is for staging/production
