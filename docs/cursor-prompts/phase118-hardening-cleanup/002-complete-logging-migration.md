# 002 — Complete `shared.logging` Migration

## Context

Two logging modules coexist:
- `services/shared/log.py` — defines `trace_id_var` (a `ContextVar`) and a thin `get_logger()`
- `services/shared/logging.py` — the real module with `JsonFormatter`, `configure_logging()`, `get_logger()`, `log_event()`, `log_exception()`. It imports `trace_id_var` from `shared.log` at line 9.

9 files still import from `shared.log`. After this task, `shared/log.py` is deleted and everything uses `shared/logging.py`.

## Step 1 — Move `trace_id_var` into `shared/logging.py`

**File**: `services/shared/logging.py`

Replace line 9:
```python
from shared.log import trace_id_var
```

With:
```python
from contextvars import ContextVar

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
```

Note: `ContextVar` is not currently imported in this file, so you must add the import. Place it right where line 9 was — the result should look like:

```python
"""Standardized JSON logging for all Pulse services."""
from __future__ import annotations

import json
import logging
import os
import time
from contextvars import ContextVar
from typing import Any, Optional

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class JsonFormatter(logging.Formatter):
    ...
```

## Step 2 — Update 8 files that import from `shared.log`

Make these exact replacements:

### `services/delivery_worker/worker.py` (line 26)
```python
# FROM:
from shared.log import trace_id_var
# TO:
from shared.logging import trace_id_var
```

### `services/ui_iot/middleware/trace.py` (line 12)
```python
# FROM:
from shared.log import trace_id_var
# TO:
from shared.logging import trace_id_var
```

### `services/ui_iot/routes/devices.py` (line 8)
```python
# FROM:
from shared.log import get_logger
# TO:
from shared.logging import get_logger
```

### `services/ingest_iot/ingest.py` (line 23)
```python
# FROM:
from shared.log import trace_id_var
# TO:
from shared.logging import trace_id_var
```

### `services/evaluator_iot/evaluator.py` (line 13)
```python
# FROM:
from shared.log import trace_id_var
# TO:
from shared.logging import trace_id_var
```

### `services/ops_worker/workers/jobs_worker.py` (line 3)
```python
# FROM:
from shared.log import get_logger, trace_id_var
# TO:
from shared.logging import get_logger, trace_id_var
```

### `services/ops_worker/workers/commands_worker.py` (line 3)
```python
# FROM:
from shared.log import get_logger, trace_id_var
# TO:
from shared.logging import get_logger, trace_id_var
```

### `services/ops_worker/main.py` (line 14)
```python
# FROM:
from shared.log import trace_id_var
# TO:
from shared.logging import trace_id_var
```

## Step 3 — Delete `shared/log.py`

```bash
rm services/shared/log.py
```

If it's tracked in git:
```bash
git rm services/shared/log.py
```

## Step 4 — Commit

```bash
git add services/shared/logging.py services/shared/log.py \
  services/delivery_worker/worker.py \
  services/ui_iot/middleware/trace.py \
  services/ui_iot/routes/devices.py \
  services/ingest_iot/ingest.py \
  services/evaluator_iot/evaluator.py \
  services/ops_worker/workers/jobs_worker.py \
  services/ops_worker/workers/commands_worker.py \
  services/ops_worker/main.py

git commit -m "refactor: complete shared.logging migration, delete shared/log.py"
```

## Verification

```bash
# No references to shared.log remain (except this prompt file)
grep -r "from shared.log " services/
# Should return nothing

# The module works
cd services && python -c "from shared.logging import trace_id_var, get_logger, configure_logging; print('OK')"
```
