# Phase 14: High-Performance Flexible Ingestion

## Overview

Phase 14 transforms the ingest pipeline from per-message processing to a high-throughput batch architecture. It also removes hardcoded telemetry field names so devices can send arbitrary metrics.

## Execution Order

Execute tasks in strict order. Each builds on the previous.

| # | File | Description |
|---|------|-------------|
| 1 | `001-device-auth-cache.md` | TTL-based auth cache to eliminate per-message PG lookups |
| 2 | `002-flexible-telemetry-schema.md` | Accept arbitrary numeric/boolean metrics in telemetry |
| 3 | `003-batched-influxdb-writes.md` | Buffer line protocol and flush in batches |
| 4 | `004-multi-worker-pipeline.md` | N async workers consuming from shared queue |
| 5 | `005-evaluator-dynamic-metrics.md` | Evaluator discovers metrics dynamically via SELECT * |
| 6 | `006-tests-simulator-benchmarks.md` | Unit tests, simulator update, documentation |

## How to Execute

For each task, paste into Cursor:

```
Read docs/cursor-prompts/phase14-flexible-ingestion/001-device-auth-cache.md and execute the task.
```

Commit after each task passes its acceptance criteria. Do not skip ahead.
