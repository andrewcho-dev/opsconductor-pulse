# Prompt 002 — Create `ops_worker` Service with Health Monitor

## Context

Based on the audit in prompt 001, create the new `services/ops_worker/` service and implement the health monitor loop. The metrics collector will be added in prompt 003.

## Your Task

### Step 1: Create the service structure

```
services/ops_worker/
├── main.py          ← entry point, asyncio event loop
├── health_monitor.py ← extracted from ui_iot/app.py
├── requirements.txt  ← same deps as ui_iot minus FastAPI/uvicorn
└── Dockerfile        ← copy pattern from services/ingest_iot/Dockerfile
```

### Step 2: Implement `health_monitor.py`

Copy the health monitor logic from `services/ui_iot/app.py` exactly — do NOT redesign or refactor it. The goal is a mechanical extraction, not an improvement. Requirements:
- Same interval as the original (read from audit prompt 001 findings)
- Same tables written to (read from audit prompt 001 findings)
- Same external HTTP endpoints polled (read from audit prompt 001 findings)
- Import DB pool from `services/shared/` or replicate the pool pattern used elsewhere in the codebase
- If the health monitor imports anything from `services/ui_iot/`, refactor that import to use `services/shared/` instead, OR copy the minimal needed code directly into `ops_worker/` — do NOT import across service directories

### Step 3: Implement `main.py`

Plain asyncio — no FastAPI, no HTTP server. Pattern:

```python
import asyncio
import logging
from health_monitor import run_health_monitor

async def main():
    await asyncio.gather(
        run_health_monitor(),
        # metrics_collector added in prompt 003
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: `requirements.txt`

Include only what `ops_worker` actually needs:
- `asyncpg` (DB)
- `httpx` (HTTP health checks to other services)
- `python-dotenv` or equivalent for env vars
- Do NOT include FastAPI, uvicorn, or any web framework

### Step 5: `Dockerfile`

Follow the pattern of `services/ingest_iot/Dockerfile` exactly. Use the same base image and structure.

## Acceptance Criteria

- [ ] `services/ops_worker/` directory exists with all 4 files
- [ ] `health_monitor.py` is a direct extraction of the health monitor from `app.py` — same logic, same intervals, same tables written
- [ ] `main.py` starts the health monitor loop cleanly
- [ ] No cross-service imports (ops_worker does not import from ui_iot)
- [ ] `pytest -m unit -v` still passes (no regressions — ui_iot not changed yet)
