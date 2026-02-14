# Phase 98 — Extract Workers from ui_iot into ops_worker

## Problem

`escalation_worker` and `report_worker` run as background tasks inside the ui_iot process
(the same process that serves all API traffic and WebSocket connections). If either worker
crashes or hangs, it can degrade the API. They also cannot be scaled, restarted, or deployed
independently.

An `ops_worker` service already exists as a standalone container (`iot-ops-worker`). It already
handles health polling and metrics collection. The escalation and report workers belong there.

## Fix

Move `escalation_worker` and `report_worker` out of ui_iot's startup and into ops_worker.

## What stays in ui_iot

- All API routes (devices, alerts, metrics, exports, customer, operator, notifications, oncall, escalation, etc.)
- WebSocket server
- Batch writer (must stay co-located with HTTP ingest path)
- Audit logger

## What moves to ops_worker

- `run_escalation_tick()` — 60s interval
- `run_report_tick()` — 86400s interval (daily)

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-ops-worker.md` | Add escalation + report ticks to ops_worker service |
| `002-ui-remove-workers.md` | Remove escalation + report tasks from ui_iot app.py |
| `003-verify.md` | Verify both workers run in ops_worker, API is clean |
