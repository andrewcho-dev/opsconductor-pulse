# Task 001: Delivery Worker SNMP Support

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

The delivery worker currently only handles webhook deliveries via HTTP POST. SNMP integrations created by customers will never receive automatic alert delivery because the worker doesn't know how to send SNMP traps.

The `services/ui_iot/services/snmp_sender.py` module already exists and works correctly (tested via the manual test delivery endpoints). We need to integrate it into the background delivery worker.

**Read first**:
- `services/delivery_worker/worker.py` (current webhook-only worker)
- `services/ui_iot/services/snmp_sender.py` (existing SNMP sender)
- `services/ui_iot/services/alert_dispatcher.py` (unified dispatcher pattern)
- `db/migrations/011_snmp_integrations.sql` (SNMP schema)

**Depends on**: Phase 4 completion

---

## Task

### 1.1 Copy SNMP sender to delivery_worker service

The delivery_worker is a separate service and cannot import from ui_iot. Copy the SNMP sender module.

Create `services/delivery_worker/snmp_sender.py`:

```python
"""SNMP trap sender for alert delivery.

Copied from services/ui_iot/services/snmp_sender.py for use in delivery_worker.
"""

import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Check for pysnmp availability
try:
    from pysnmp.hlapi.v3arch.asyncio import (
        CommunityData,
        ContextData,
        NotificationType,
        ObjectIdentity,
        ObjectType,
        OctetString,
        SnmpEngine,
        UdpTransportTarget,
        UsmUserData,
        sendNotification,
        usmHMACSHAAuthProtocol,
        usmAesCfb128Protocol,
        usmDESPrivProtocol,
    )
    PYSNMP_AVAILABLE = True
except ImportError:
    PYSNMP_AVAILABLE = False
    logger.warning("pysnmp not available - SNMP delivery disabled")


@dataclass
class SNMPTrapResult:
    """Result of SNMP trap send attempt."""
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None


async def send_alert_trap(
    host: str,
    port: int,
    config: dict,
    alert_id: str,
    device_id: str,
    tenant_id: str,
    severity: str,
    message: str,
    timestamp: datetime,
    oid_prefix: str = "1.3.6.1.4.1.99999",
) -> SNMPTrapResult:
    """Send an SNMP trap for an alert."""
    if not PYSNMP_AVAILABLE:
        return SNMPTrapResult(success=False, error="pysnmp not available")

    start_time = asyncio.get_event_loop().time()

    try:
        version = config.get("version", "2c")

        if version == "2c":
            community = config.get("community", "public")
            auth_data = CommunityData(community, mpModel=1)
        elif version == "3":
            username = config.get("username", "")
            auth_password = config.get("auth_password")
            priv_password = config.get("priv_password")
            auth_protocol = config.get("auth_protocol", "SHA")
            priv_protocol = config.get("priv_protocol")

            auth_proto = usmHMACSHAAuthProtocol
            priv_proto = None

            if priv_password:
                priv_proto = usmAesCfb128Protocol if priv_protocol == "AES" else usmDESPrivProtocol

            if priv_password:
                auth_data = UsmUserData(
                    username,
                    authKey=auth_password,
                    privKey=priv_password,
                    authProtocol=auth_proto,
                    privProtocol=priv_proto,
                )
            elif auth_password:
                auth_data = UsmUserData(
                    username,
                    authKey=auth_password,
                    authProtocol=auth_proto,
                )
            else:
                auth_data = UsmUserData(username)
        else:
            return SNMPTrapResult(success=False, error=f"Unsupported SNMP version: {version}")

        transport = UdpTransportTarget((host, port), timeout=10, retries=1)

        severity_map = {"critical": 1, "warning": 2, "info": 3}
        severity_int = severity_map.get(severity.lower(), 4)

        var_binds = [
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.1.0"), OctetString(alert_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.2.0"), OctetString(device_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.3.0"), OctetString(tenant_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.4.0"), severity_int),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.5.0"), OctetString(message)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.6.0"), OctetString(timestamp.isoformat())),
        ]

        snmp_engine = SnmpEngine()

        error_indication, error_status, error_index, var_binds_out = await sendNotification(
            snmp_engine,
            auth_data,
            transport,
            ContextData(),
            "trap",
            NotificationType(ObjectIdentity(f"{oid_prefix}.0.1")),
            *var_binds,
        )

        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        if error_indication:
            return SNMPTrapResult(success=False, error=str(error_indication), duration_ms=duration_ms)

        if error_status:
            return SNMPTrapResult(
                success=False,
                error=f"{error_status.prettyPrint()} at {error_index}",
                duration_ms=duration_ms,
            )

        return SNMPTrapResult(success=True, duration_ms=duration_ms)

    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        logger.exception("SNMP trap send failed")
        return SNMPTrapResult(success=False, error=str(e), duration_ms=duration_ms)
```

### 1.2 Update delivery worker to handle SNMP

Modify `services/delivery_worker/worker.py` to support both webhook and SNMP:

Add import at top:
```python
from snmp_sender import send_alert_trap, SNMPTrapResult, PYSNMP_AVAILABLE
```

Add helper to normalize snmp_config:
```python
def normalize_snmp_config(value) -> dict:
    """Normalize snmp_config from various storage formats."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}
```

Update `fetch_integration` to return SNMP fields:
```python
async def fetch_integration(conn: asyncpg.Connection, tenant_id: str, integration_id) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT type, enabled, config_json, snmp_host, snmp_port, snmp_config, snmp_oid_prefix
        FROM integrations
        WHERE tenant_id=$1 AND integration_id=$2
        """,
        tenant_id,
        integration_id,
    )
    if row is None:
        return None
    return dict(row)
```

Replace the delivery logic in `process_job` (around line 256-286):
```python
async def process_job(conn: asyncpg.Connection, job: asyncpg.Record) -> None:
    job_id = job["job_id"]
    tenant_id = job["tenant_id"]
    integration_id = job["integration_id"]
    attempt_no = int(job["attempts"]) + 1

    started_at = now_utc()
    http_status = None
    error = None
    ok = False

    integration = await fetch_integration(conn, tenant_id, integration_id)
    if integration is None:
        error = "integration_not_found"
    elif not integration["enabled"]:
        error = "integration_disabled"
    else:
        integration_type = integration.get("type", "webhook")

        if integration_type == "snmp":
            # SNMP delivery
            ok, error = await deliver_snmp(integration, job)
        else:
            # Webhook delivery (default)
            ok, http_status, error = await deliver_webhook(integration, job)

    finished_at = now_utc()
    latency_ms = int((finished_at - started_at).total_seconds() * 1000)

    await record_attempt(
        conn,
        tenant_id,
        job_id,
        attempt_no,
        ok,
        http_status,
        latency_ms,
        error,
        started_at,
        finished_at,
    )

    if ok:
        await update_job_success(conn, job_id, attempt_no)
        return

    if attempt_no >= WORKER_MAX_ATTEMPTS:
        await update_job_failed(conn, job_id, attempt_no, error or "failed")
        return

    await update_job_retry(conn, job_id, attempt_no, error or "failed")


async def deliver_webhook(integration: dict, job: asyncpg.Record) -> tuple[bool, int | None, str | None]:
    """Deliver via webhook. Returns (ok, http_status, error)."""
    config = normalize_config_json(integration.get("config_json"))
    url = config.get("url")
    headers = config.get("headers") or {}

    if not url:
        return False, None, "missing_url"

    allowed, reason = validate_url(url)
    if not allowed:
        return False, None, f"url_blocked:{reason}"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    try:
        timeout = httpx.Timeout(WORKER_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            http_status = resp.status_code
            ok = 200 <= resp.status_code < 300
            error = None if ok else f"http_{resp.status_code}"
            return ok, http_status, error
    except Exception as exc:
        return False, None, f"request_error:{type(exc).__name__}"


async def deliver_snmp(integration: dict, job: asyncpg.Record) -> tuple[bool, str | None]:
    """Deliver via SNMP trap. Returns (ok, error)."""
    if not PYSNMP_AVAILABLE:
        return False, "snmp_not_available"

    snmp_host = integration.get("snmp_host")
    snmp_port = integration.get("snmp_port") or 162
    snmp_config = normalize_snmp_config(integration.get("snmp_config"))
    oid_prefix = integration.get("snmp_oid_prefix") or "1.3.6.1.4.1.99999"

    if not snmp_host:
        return False, "missing_snmp_host"

    if not snmp_config:
        return False, "missing_snmp_config"

    payload = job["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    # Extract alert fields from payload
    alert_id = str(payload.get("alert_id", "unknown"))
    device_id = payload.get("device_id", "unknown")
    tenant_id = job["tenant_id"]
    severity = str(payload.get("severity", "info"))
    message = payload.get("summary") or payload.get("message") or "Alert"

    # Parse timestamp or use now
    ts_str = payload.get("created_at")
    if ts_str:
        try:
            timestamp = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = now_utc()
    else:
        timestamp = now_utc()

    result = await send_alert_trap(
        host=snmp_host,
        port=snmp_port,
        config=snmp_config,
        alert_id=alert_id,
        device_id=device_id,
        tenant_id=tenant_id,
        severity=severity,
        message=message,
        timestamp=timestamp,
        oid_prefix=oid_prefix,
    )

    return result.success, result.error
```

### 1.3 Update delivery_worker Dockerfile

Add pysnmp to `services/delivery_worker/requirements.txt`:
```
asyncpg>=0.29.0
httpx>=0.27.0
pysnmp-lextudio>=6.0.0
```

### 1.4 Update worker startup logging

Update the startup print in `run_worker`:
```python
async def run_worker() -> None:
    pool = await get_pool()
    ssrf_strict = MODE == "PROD"
    print(
        "[worker] startup mode={} ssrf_strict={} timeout_seconds={} max_attempts={} snmp_available={}".format(
            MODE,
            ssrf_strict,
            WORKER_TIMEOUT_SECONDS,
            WORKER_MAX_ATTEMPTS,
            PYSNMP_AVAILABLE,
        )
    )
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/delivery_worker/snmp_sender.py` |
| MODIFY | `services/delivery_worker/worker.py` |
| MODIFY | `services/delivery_worker/requirements.txt` |

---

## Acceptance Criteria

- [ ] delivery_worker imports snmp_sender module
- [ ] Worker checks integration type before delivery
- [ ] SNMP integrations receive traps via background worker
- [ ] Webhook integrations continue to work unchanged
- [ ] Worker logs SNMP availability on startup
- [ ] pysnmp added to requirements.txt

**Test**:
```bash
# Rebuild delivery worker
cd compose && docker compose build delivery_worker

# Restart and check logs
docker compose up -d delivery_worker
docker compose logs -f delivery_worker
# Should see: snmp_available=True

# Create SNMP integration and integration route, then generate an alert
# Verify SNMP trap is sent (check with tcpdump or SNMP manager)
```

---

## Commit

```
Add SNMP support to delivery worker

- Copy snmp_sender module to delivery_worker service
- Update worker to check integration type
- Route SNMP integrations to SNMP sender
- Webhook delivery unchanged
- Add pysnmp to requirements

Part of Phase 5: System Completion
```
