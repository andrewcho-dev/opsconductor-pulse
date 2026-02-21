# Phase 102 — Observability

## Goal

Add structured JSON logging with correlation IDs across all Python services.
Every HTTP request and every background task tick emits a JSON log line with
`trace_id`, `tenant_id`, `service`, `level`, `msg`, and timing.

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-structured-logging.md` | Shared logging module — JSON formatter + trace_id injection |
| `002-http-middleware.md` | FastAPI middleware: generate/propagate trace_id per request |
| `003-background-tasks.md` | Add trace_id to evaluator, ops_worker, delivery_worker ticks |
| `004-verify.md` | Run services, grep for JSON log lines, confirm fields |
