# Phase 23.1: Extract Shared Ingest Core Module

## Task

Create `services/shared/ingest_core.py` by extracting protocol-agnostic logic from `services/ingest_iot/ingest.py`.

## Step 1: Create the shared module

Create `services/shared/__init__.py` (empty file).

Create `services/shared/ingest_core.py` with these components extracted from `services/ingest_iot/ingest.py`:

**Functions to copy:**
- `parse_ts()` (lines 40-46)
- `sha256_hex()` (lines 48-49)
- `_escape_tag_value()` (lines 51-53)
- `_escape_field_key()` (lines 56-58)
- `_build_line_protocol()` (lines 61-97)

**Classes to copy:**
- `TokenBucket` (lines 167-171)
- `DeviceAuthCache` (lines 173-209)
- `InfluxBatchWriter` (lines 212-291)

**Add new code at the end:**

```python
@dataclass
class IngestResult:
    success: bool
    reason: str | None = None
    line_protocol: str | None = None

async def validate_and_prepare(
    pool,
    auth_cache: DeviceAuthCache,
    rate_buckets: dict,
    tenant_id: str,
    device_id: str,
    site_id: str,
    msg_type: str,
    provision_token: str | None,
    payload: dict,
    max_payload_bytes: int,
    rps: float,
    burst: float,
    require_token: bool,
) -> IngestResult:
```

This function consolidates validation from `ingest.py` db_worker (lines 507-585):
1. Check payload size → return `IngestResult(False, "PAYLOAD_TOO_LARGE")`
2. Check rate limit using TokenBucket → return `IngestResult(False, "RATE_LIMITED")`
3. Query auth_cache, then DB if miss
4. Check device exists → return `IngestResult(False, "UNREGISTERED_DEVICE")`
5. Check status ACTIVE → return `IngestResult(False, "DEVICE_REVOKED")`
6. Check site_id matches → return `IngestResult(False, "SITE_MISMATCH")`
7. If require_token: verify hash → return `IngestResult(False, "TOKEN_INVALID")` or `"TOKEN_MISSING"`
8. Success: return `IngestResult(True, line_protocol=_build_line_protocol(...))`

**Required imports:**
```python
import asyncio
import hashlib
import time
import json
from datetime import datetime, timezone
from dateutil import parser as dtparser
from dataclasses import dataclass
```

## Step 2: Update ingest.py

Modify `services/ingest_iot/ingest.py`:
1. Add: `from shared.ingest_core import parse_ts, sha256_hex, _escape_tag_value, _escape_field_key, _build_line_protocol, TokenBucket, DeviceAuthCache, InfluxBatchWriter`
2. Delete local definitions (lines 40-53, 56-58, 61-97, 167-171, 173-209, 212-291)
3. Keep MQTT-specific code (Ingestor, topic_extract, DDL, utcnow)

## Verification

```bash
cd /home/opsconductor/simcloud && python3 -c "from services.shared.ingest_core import DeviceAuthCache, InfluxBatchWriter, IngestResult; print('OK')"
```

## Files

| Action | File |
|--------|------|
| CREATE | `services/shared/__init__.py` |
| CREATE | `services/shared/ingest_core.py` |
| MODIFY | `services/ingest_iot/ingest.py` |
