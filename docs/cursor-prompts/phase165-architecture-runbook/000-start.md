# Phase 165 — Architecture Docs & Runbook (R6)

## Goal

Update all platform documentation to reflect the rearchitected system (EMQX, NATS JetStream, Kubernetes, MinIO, new services). Every doc must accurately describe the post-migration state so engineers can onboard, debug, and operate the new platform without referencing legacy Mosquitto/monolithic architecture.

## Prerequisites

- Phase 160 (Foundation Hardening) complete
- Phase 161 (EMQX Migration) complete
- Phase 162 (NATS JetStream) complete
- Phase 163 (Kubernetes Readiness) complete
- Phase 164 (Operational Hardening) complete

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-architecture-overview.md` | Rewrite architecture overview for EMQX + NATS + K8s topology |
| 002  | `002-service-map.md` | Update service map with new services, ports, and data flows |
| 003  | `003-tenant-isolation.md` | Update tenant isolation doc for EMQX per-device ACLs and NATS subject scoping |
| 004  | `004-service-docs.md` | Update per-service docs (ingest, evaluator, ops-worker, ui-iot) + new route-delivery service |
| 005  | `005-operations-docs.md` | Update deployment, runbook, monitoring, database, and security docs |
| 006  | `006-index-and-links.md` | Update docs/index.md and verify all cross-references |
