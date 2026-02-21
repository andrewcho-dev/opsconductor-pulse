# Phase 198 — Backend Performance Fixes

## Goal

Fix three backend performance issues found in the code review: N+1 queries in the evaluator's rule-checking hot path, missing `statement_timeout` on the evaluator's database pool, and an unbounded in-memory buffer in the telemetry batch writer that can cause OOM under sustained write failures.

## Current State (problem)

1. **N+1 in evaluator** (`evaluator_iot/evaluator.py:1445-1460`): For each rule with group filters, one database query executes per rule per device. 100 group-filtered rules = 100 sequential queries per telemetry event.
2. **Missing statement_timeout on evaluator pool** (`evaluator_iot/evaluator.py:1212-1225`): Unlike `ui_iot` which sets `statement_timeout` via pool init callback, the evaluator pool has none. Long-running evaluation queries can hold connections indefinitely.
3. **Unbounded batch writer buffer** (`shared/ingest_core.py:118-143`): `TimescaleBatchWriter.batch` is an unbounded list. If flush fails repeatedly, it grows without limit until OOM.

## Target State

- Evaluator pre-fetches all device group memberships once per evaluation cycle and filters in memory.
- Evaluator pool sets `statement_timeout = 10s` via init callback, consistent with `ui_iot`.
- `TimescaleBatchWriter` has a configurable `max_buffer_size` (default 5,000 records). When exceeded, oldest records are dropped with a warning metric.

## Execution Order

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | `001-evaluator-statement-timeout.md` | Add statement_timeout to evaluator pool | — |
| 2 | `002-evaluator-n-plus-one.md` | Pre-fetch group memberships in evaluator | — |
| 3 | `003-batch-writer-buffer-limit.md` | Add max buffer size to TimescaleBatchWriter | — |
| 4 | `004-update-documentation.md` | Update affected docs | Steps 1–3 |

## Verification

```bash
# statement_timeout present in evaluator pool init
grep -n 'statement_timeout' services/evaluator_iot/evaluator.py
# Must show the timeout being set

# No per-rule group membership query in hot path
grep -n 'device_group_members' services/evaluator_iot/evaluator.py
# Should show a single batch fetch, not one per rule

# Buffer limit in batch writer
grep -n 'max_buffer_size\|MAX_BUFFER' services/shared/ingest_core.py
# Must show a defined limit
```

## Documentation Impact

- No external-facing docs change for this phase. Internal change only.
