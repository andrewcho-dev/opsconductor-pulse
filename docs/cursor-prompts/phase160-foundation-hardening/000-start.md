# Phase 160 — Foundation Hardening (R1)

## Goal

Fix critical reliability gaps before the EMQX/NATS migration. These issues will cause data loss and worker stalls at scale regardless of broker choice.

## Why This Must Come First

- **Graceful shutdown:** Every deploy currently loses buffered telemetry records (batch writer has `.stop()` but it's never called)
- **Webhook blocking:** A single slow webhook stalls an ingest worker for 10s, backing up the queue for all tenants
- **Hard-coded pool sizes:** Cannot tune DB concurrency per service without code changes

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 001  | `001-graceful-shutdown.md` | Add SIGTERM/SIGINT handlers to ingest_iot, drain queue, flush batch writer |
| 002  | `002-configurable-db-pools.md` | Replace all hard-coded `min_size=2, max_size=10` with env vars |
| 003  | `003-decouple-route-delivery.md` | Move webhook/MQTT route delivery out of db_worker into async delivery queue |
| 004  | `004-update-docs.md` | Update documentation |

## Verification

```bash
# 1. Graceful shutdown test
cd services/ingest_iot && timeout 5 python -c "
import asyncio, signal
from ingest import Ingestor
# Verify signal handlers are registered
" 2>&1 | head -5

# 2. Pool config test — check env vars are read
grep -n 'PG_POOL_MIN\|PG_POOL_MAX' services/ingest_iot/ingest.py services/evaluator_iot/evaluator.py services/ops_worker/main.py services/ui_iot/app.py

# 3. Route delivery — verify delivery runs in separate task pool
grep -n 'route_delivery\|_delivery_queue\|delivery_worker' services/ingest_iot/ingest.py
```
