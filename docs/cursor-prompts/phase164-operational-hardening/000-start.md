# Phase 164 — Operational Hardening (R5)

## Goal

Production-grade observability and operational tooling for the rearchitected platform.

## Prerequisites

- Phase 163 (Kubernetes Readiness) complete

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-s3-export-storage.md` | Replace local filesystem exports with S3/MinIO |
| 002  | `002-per-tenant-metrics.md` | Add tenant_id labels to all Prometheus metrics + Grafana dashboards |
| 003  | `003-infrastructure-alerting.md` | Alert rules for NATS lag, batch write latency, EMQX connections, DLQ depth |
| 004  | `004-update-docs.md` | Update documentation |
