# Phase 84 — NOC Command Center Page

## Overview
Replace the current SystemDashboard + SystemMetricsPage with a single unified
NOC-grade command center page at `/operator/noc`. This is the "wall display"
screen that a network operations center would put on a large monitor.

Layout: full-width, minimal chrome, dark-biased, ECharts-heavy.
Data: all existing backend endpoints — no backend changes needed.

Backend endpoints available:
- GET /operator/system/health
- GET /operator/system/metrics/latest
- GET /operator/system/metrics/history?metric=X&minutes=N&service=X&rate=true
- GET /operator/system/metrics/history/batch
- GET /operator/system/aggregates
- GET /operator/system/capacity
- GET /operator/system/errors?hours=1

## Execution Order
1. 001-gauge-row.md — Top row: 4 ECharts gauge dials
2. 002-chart-grid.md — Middle: 4 time-series charts in 2×2 grid
3. 003-service-topology.md — Bottom: service health topology strip
4. 004-noc-page.md — Assemble full NOCPage, wire route + nav
5. 005-verify.md — Build check + checklist
