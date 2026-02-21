# Prompt 004 — Remove Extracted Tasks from `ui_iot/app.py`

## Context

`ops_worker` now runs both the health monitor and metrics collector (prompts 002-003). This prompt removes them from `services/ui_iot/app.py`. This is the most risky prompt — it modifies the production API service. Read carefully before making changes.

## Your Task

### Step 1: Read `services/ui_iot/app.py` fully before touching it

Understand every startup/shutdown hook and background task. Confirm exactly which code corresponds to:
- Health monitor (to remove)
- Metrics collector (to remove)
- Batch writer (to KEEP)
- Audit logger (to KEEP)

### Step 2: Remove health monitor and metrics collector

From `services/ui_iot/app.py`:
- Remove the health monitor coroutine/task and its startup/shutdown registration
- Remove the metrics collector coroutine/task and its startup/shutdown registration
- Remove any imports that are ONLY used by those two tasks and nothing else
- Do NOT touch the batch writer, audit logger, or any route handler

### Step 3: Remove now-unused module-level code

If the health monitor or metrics collector had module-level initialization (e.g., HTTP client instances, semaphores, config constants), remove them IF they are not used by anything else remaining in ui_iot.

### Step 4: Verify the API routes still work

The operator system dashboard routes in `services/ui_iot/routes/system.py` READ from the tables that ops_worker now WRITES. These routes must still function. Confirm:
- The routes do not call the health monitor or metrics collector functions directly
- The routes only query the DB tables (which ops_worker will populate)
- No import of the removed functions exists in `system.py` or anywhere else in ui_iot

### Step 5: Update `requirements.txt` for ui_iot (if applicable)

If any packages were ONLY used by the removed tasks and are no longer needed in ui_iot, remove them. Only remove packages you are certain are unused.

## Acceptance Criteria

- [ ] `services/ui_iot/app.py` no longer starts health monitor or metrics collector background tasks
- [ ] Batch writer and audit logger are untouched and still running
- [ ] No broken imports remain in ui_iot
- [ ] `pytest -m unit -v` passes with 0 failures
- [ ] `services/ui_iot/routes/system.py` is unchanged
