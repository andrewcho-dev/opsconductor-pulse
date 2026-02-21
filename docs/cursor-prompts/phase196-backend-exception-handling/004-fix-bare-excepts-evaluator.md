# Task 4: Fix Bare Exception Handlers in `evaluator_iot`

## Context

`services/evaluator_iot/evaluator.py` has bare `except Exception` blocks at lines ~249-254 and elsewhere. The evaluator is the critical alert engine — silent failures here mean alerts are missed.

Additionally, this file has two duplicate definitions: `COUNTERS` dict (defined twice at lines ~59-64 and ~77-82) and `health_handler` function (defined twice at lines ~84-96 and ~163-175). These should be deduplicated as part of this cleanup.

## Actions

1. Read `services/evaluator_iot/evaluator.py` in full.

2. **Fix duplicate definitions:**
   - Find both `COUNTERS = {...}` definitions. Keep the second (more complete) one and delete the first.
   - Find both `health_handler` definitions. Keep the second (more complete) one and delete the first.
   - Confirm nothing else is duplicated.

3. **Fix bare exception handlers** using the same three-pattern approach from Task 3:
   - Per-rule evaluation errors (one rule failing should not stop other rules): catch, log with rule context, continue.
   - Infrastructure errors (database pool, NATS): log and reraise.
   - Unknown errors in the main evaluation loop: log as critical and allow the loop to restart (the outer loop likely has a restart mechanism).

4. For each exception handler in the file, add `extra={"tenant_id": tenant_id, "device_id": device_id}` to the log call where those variables are in scope. The evaluator is multi-tenant — every error log must include tenant context.

5. Do not change any rule evaluation logic.

## Verification

```bash
# No duplicate dict literals named COUNTERS
grep -n '^COUNTERS' services/evaluator_iot/evaluator.py
# Should appear exactly once

# No duplicate health_handler
grep -n 'def health_handler' services/evaluator_iot/evaluator.py
# Should appear exactly once
```
