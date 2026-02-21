# 006: Backend Code Cleanup

## Priority: MEDIUM

## Issues to Fix

### 1. Remove Dead Code

**File:** `services/ui_iot/routes/customer.py`

**Line 68 - Unused alias:**
```python
# REMOVE:
fetch_devices = fetch_devices_v2  # Never called
```

**Line 303-318 - Unused function:**
```python
# REMOVE entire function:
def generate_test_payload(...):
    # Never called, test payloads created inline
```

**File:** `services/ui_iot/app.py`

**Lines 173-196 - Unused function:**
```python
# REMOVE:
def get_settings():
    # Never called
```

**Lines 2-3 - Unnecessary sys.path manipulation:**
```python
# REMOVE (Docker sets paths correctly):
import sys
sys.path.insert(0, ...)
```

**File:** `services/ui_iot/middleware/tenant.py`

**Lines 22-44 - Unused helper functions:**
```python
# REMOVE if not used anywhere:
def get_tenant_id_or_none(): ...
def is_operator(): ...
def is_operator_admin(): ...

# Verify first with grep:
# grep -r "get_tenant_id_or_none\|is_operator\|is_operator_admin" services/
```

**File:** `services/ingest_iot/ingest.py`

**Lines 43-49 - Unused COUNTERS keys:**
```python
# Keep COUNTERS but verify all keys are read somewhere
# Remove any keys only written but never read
```

---

### 2. Consolidate Duplicate Code

**Create shared utility:** `services/shared/utils.py`

```python
"""Shared utilities across services."""
from datetime import datetime, timezone
from typing import Optional
import re
from uuid import UUID


def format_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO string with UTC timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def validate_uuid(value: str) -> bool:
    """Validate UUID string format."""
    try:
        UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def check_delete_result(result: str) -> bool:
    """Check if DELETE affected any rows."""
    if not result:
        return False
    parts = result.split()
    if len(parts) != 2 or parts[0] != "DELETE":
        return False
    try:
        return int(parts[1]) > 0
    except ValueError:
        return False


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not value:
        return ""
    # Remove control characters
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    # Truncate
    return value[:max_length].strip()
```

**Update customer.py to use shared utilities:**
```python
from services.shared.utils import format_timestamp, validate_uuid, check_delete_result

# Replace all inline UUID validation:
# BEFORE:
try:
    UUID(integration_id)
except ValueError:
    raise HTTPException(400, "Invalid ID")

# AFTER:
if not validate_uuid(integration_id):
    raise HTTPException(400, "Invalid ID")
```

---

### 3. Consolidate Duplicate Validation Logic

**Create validation dependency:** `services/ui_iot/dependencies.py`

```python
"""FastAPI dependencies for common validation patterns."""
from fastapi import Depends, HTTPException, Path, Query
from uuid import UUID
from typing import Optional


def valid_uuid(
    param_name: str = "id",
    description: str = "Resource ID"
):
    """Dependency for UUID path parameter validation."""
    def validator(value: str = Path(..., description=description)):
        try:
            UUID(value)
            return value
        except ValueError:
            raise HTTPException(400, f"Invalid {param_name} format")
    return validator


def pagination(
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
):
    """Pagination parameters dependency."""
    return {"limit": limit, "offset": offset}


ValidIntegrationId = Depends(valid_uuid("integration_id", "Integration ID"))
ValidDeviceId = Depends(valid_uuid("device_id", "Device ID"))
ValidAlertId = Depends(valid_uuid("alert_id", "Alert ID"))
```

**Usage in routes:**
```python
from services.ui_iot.dependencies import ValidIntegrationId, pagination

@router.get("/integrations/{integration_id}")
async def get_integration(integration_id: str = ValidIntegrationId):
    # No manual validation needed
    ...

@router.get("/devices")
async def list_devices(page: dict = Depends(pagination)):
    # page["limit"], page["offset"] available
    ...
```

---

### 4. Standardize Datetime Handling

**Find and replace inconsistent patterns:**

```bash
# Find all datetime.utcnow() usage
grep -rn "datetime.utcnow()" services/
```

**Replace all with timezone-aware:**
```python
# BEFORE:
from datetime import datetime
now = datetime.utcnow()

# AFTER:
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

---

### 5. Consolidate Database Pool Management

**File:** `services/ui_iot/routes/customer.py`

**Problem:** Creates own pool instead of using app.state.pool

**Fix:** Use FastAPI dependency injection:

```python
# In services/ui_iot/dependencies.py
from fastapi import Request

async def get_db_pool(request: Request):
    """Get database pool from app state."""
    return request.app.state.pool

# In routes:
from services.ui_iot.dependencies import get_db_pool

@router.get("/devices")
async def list_devices(pool = Depends(get_db_pool)):
    async with tenant_connection(pool, get_tenant_id()) as conn:
        ...
```

**Remove duplicate pool creation:**
```python
# REMOVE from customer.py:
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(...)
    return _pool
```

---

### 6. Consolidate Normalize Functions

**File:** `services/delivery_worker/worker.py`

**Lines 82-158 - Four nearly identical functions:**
- normalize_config_json
- normalize_snmp_config
- normalize_email_config
- normalize_mqtt_config

**Fix:** Create single generic function:
```python
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def normalize_config(
    config: dict | str | None,
    model: Type[T],
    defaults: dict | None = None
) -> T:
    """Normalize configuration to Pydantic model."""
    if config is None:
        config = {}
    elif isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError:
            config = {}

    if defaults:
        config = {**defaults, **config}

    return model(**config)


# Usage:
snmp_config = normalize_config(raw_config, SNMPConfig, {"version": "2c"})
email_config = normalize_config(raw_config, EmailConfig, {"port": 587})
```

---

### 7. Add Missing Type Hints

**Priority files:**
- `services/ui_iot/db/queries.py` - Add return types to all functions
- `services/delivery_worker/worker.py` - Add type hints throughout
- `services/subscription_worker/worker.py` - Add type hints

**Example:**
```python
# BEFORE:
async def fetch_devices(conn, tenant_id, limit, offset):
    ...

# AFTER:
from typing import List, Dict, Any

async def fetch_devices(
    conn: asyncpg.Connection,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    ...
```

---

### 8. Fix Inconsistent JSON Handling

**Problem:** Some places use manual json.dumps(), others use FastAPI auto-serialization.

**Fix:** Let FastAPI handle serialization:
```python
# BEFORE:
return Response(
    content=json.dumps({"data": result}, default=str),
    media_type="application/json"
)

# AFTER:
return {"data": result}  # FastAPI handles serialization

# For datetime serialization, use custom encoder in app config:
from fastapi.encoders import jsonable_encoder

app = FastAPI(
    json_encoder=jsonable_encoder,
)
```

---

### 9. Remove Commented-Out Code

Search and remove all commented-out code blocks:

```bash
# Find multi-line comments that look like code
grep -rn "^#.*def \|^#.*class \|^#.*async \|^#.*await " services/
```

If the code is needed for reference, move to documentation or version control history.

---

### 10. Standardize Error Logging

**Create logging utility:** `services/shared/logging.py`

```python
"""Standardized logging configuration."""
import logging
import json
from typing import Any, Optional

def get_logger(name: str) -> logging.Logger:
    """Get configured logger for service."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def log_exception(
    logger: logging.Logger,
    message: str,
    exception: Exception,
    context: Optional[dict] = None,
):
    """Log exception with context."""
    log_data = {
        "message": message,
        "error_type": type(exception).__name__,
        "error": str(exception),
    }
    if context:
        log_data["context"] = context

    logger.error(json.dumps(log_data))
```

---

## Verification

```bash
# Check for remaining dead code
vulture services/ --min-confidence 80

# Check type hints coverage
mypy services/ --ignore-missing-imports

# Run tests to ensure refactoring didn't break anything
pytest tests/ -v

# Lint check
ruff check services/
```

## Files Changed

- `services/ui_iot/routes/customer.py`
- `services/ui_iot/app.py`
- `services/ui_iot/middleware/tenant.py`
- `services/delivery_worker/worker.py`
- `services/ingest_iot/ingest.py`
- `services/shared/utils.py` (NEW)
- `services/shared/logging.py` (NEW)
- `services/ui_iot/dependencies.py` (NEW or UPDATE)
