# Prompt 001 — Audit ui_iot Background Tasks

## Your Task

Read and map every background task in `services/ui_iot/app.py`. Do NOT change any code yet — only audit and document.

### Step 1: Read these files

- `services/ui_iot/app.py` — find all `asyncio.create_task()`, `@app.on_event("startup")`, `lifespan` context manager, or background task patterns
- `services/ui_iot/routes/system.py` — understand what tables/columns the operator system dashboard reads (these must remain populated by the extracted service)
- Any helper modules imported by app.py that contain the background task logic (e.g., `health_monitor.py`, `metrics_collector.py`, or inline functions in app.py)

### Step 2: For each background task, document:

Write your findings as a comment block at the top of `services/ui_iot/app.py` (do not remove existing code):

```python
# PHASE 43 AUDIT — Background Tasks
#
# Task 1: health_monitor
#   - Interval: every Xs
#   - What it does: [describe]
#   - Tables it writes: [list table names]
#   - External dependencies: [HTTP calls to other services? DB only?]
#   - Decision: EXTRACT to ops_worker / KEEP in ui_iot
#   - Reason: [why]
#
# Task 2: metrics_collector
#   - [same structure]
#
# Task 3: batch_writer
#   - [same structure]
#
# Task 4: audit_logger
#   - [same structure]
```

### Step 3: Confirm extraction candidates

Based on the audit, confirm:
- Health monitor → EXTRACT (it only reads external service endpoints and writes to DB — no dependency on request context)
- Metrics collector → EXTRACT (it only queries DB aggregates and writes summary rows — no dependency on request context)
- Batch writer → KEEP (tightly coupled to HTTP ingest path connection sharing)
- Audit logger → KEEP (flushes in-memory events from request context)

If the audit reveals a different coupling picture, update the decision and note it clearly.

## Acceptance Criteria

- [ ] All 4 background tasks are documented with the comment block in `app.py`
- [ ] Tables written by health monitor and metrics collector are listed (so ops_worker knows what to write)
- [ ] External HTTP dependencies of health monitor are listed (service endpoints it pings)
- [ ] Extraction decisions confirmed or updated with reasoning
- [ ] No code changed — audit only
