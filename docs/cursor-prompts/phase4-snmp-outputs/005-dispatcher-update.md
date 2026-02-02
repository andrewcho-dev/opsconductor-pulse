# Task 005: Dispatcher Update for SNMP

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

The alert dispatcher currently only sends webhooks. It needs to handle both webhook and SNMP outputs based on integration type.

**Read first**:
- `services/ui_iot/services/` (existing service patterns)
- `services/ui_iot/services/snmp_sender.py` (from Task 002)

**Depends on**: Tasks 002, 003

---

## Task

### 5.1 Create unified alert dispatcher

Create `services/ui_iot/services/alert_dispatcher.py`:

```python
"""Unified alert dispatcher for webhooks and SNMP traps."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from services.ui_iot.services.snmp_sender import send_alert_trap, SNMPTrapResult

logger = logging.getLogger(__name__)


class DeliveryType(str, Enum):
    WEBHOOK = "webhook"
    SNMP = "snmp"


@dataclass
class AlertPayload:
    """Alert data for dispatch."""
    alert_id: str
    device_id: str
    tenant_id: str
    severity: str
    message: str
    timestamp: datetime
    metadata: Optional[dict] = None


@dataclass
class DeliveryResult:
    """Result of alert delivery attempt."""
    integration_id: str
    integration_name: str
    delivery_type: DeliveryType
    success: bool
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class DispatchResult:
    """Result of dispatching alert to all matched integrations."""
    alert_id: str
    total_integrations: int
    successful: int
    failed: int
    results: list[DeliveryResult]


async def dispatch_alert(alert: AlertPayload, integrations: list[dict]) -> DispatchResult:
    """Dispatch alert to all matched integrations."""
    results = []
    tasks = []

    for integration in integrations:
        if not integration.get("enabled", True):
            continue

        integration_type = integration.get("type", "webhook")
        if integration_type == "webhook":
            tasks.append(_deliver_webhook(alert, integration))
        elif integration_type == "snmp":
            tasks.append(_deliver_snmp(alert, integration))

    if tasks:
        delivery_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in delivery_results:
            if isinstance(result, Exception):
                results.append(DeliveryResult(
                    integration_id="unknown",
                    integration_name="unknown",
                    delivery_type=DeliveryType.WEBHOOK,
                    success=False,
                    error=str(result),
                ))
            else:
                results.append(result)

    successful = sum(1 for r in results if r.success)
    return DispatchResult(
        alert_id=alert.alert_id,
        total_integrations=len(integrations),
        successful=successful,
        failed=len(results) - successful,
        results=results,
    )


async def _deliver_webhook(alert: AlertPayload, integration: dict) -> DeliveryResult:
    """Deliver alert via webhook."""
    # Import here to avoid circular imports
    from services.ui_iot.services.webhook_sender import send_webhook

    webhook_url = integration.get("webhook_url")
    if not webhook_url:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.WEBHOOK,
            success=False,
            error="Missing webhook_url",
        )

    payload = {
        "alert_id": alert.alert_id,
        "device_id": alert.device_id,
        "tenant_id": alert.tenant_id,
        "severity": alert.severity,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat(),
    }

    result = await send_webhook(
        url=webhook_url,
        payload=payload,
        secret=integration.get("webhook_secret"),
    )

    return DeliveryResult(
        integration_id=integration.get("id", "unknown"),
        integration_name=integration.get("name", "unknown"),
        delivery_type=DeliveryType.WEBHOOK,
        success=result.success,
        error=result.error,
        duration_ms=result.duration_ms,
    )


async def _deliver_snmp(alert: AlertPayload, integration: dict) -> DeliveryResult:
    """Deliver alert via SNMP trap."""
    snmp_host = integration.get("snmp_host")
    snmp_config = integration.get("snmp_config")

    if not snmp_host or not snmp_config:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.SNMP,
            success=False,
            error="Missing snmp_host or snmp_config",
        )

    result = await send_alert_trap(
        host=snmp_host,
        port=integration.get("snmp_port", 162),
        config=snmp_config,
        alert_id=alert.alert_id,
        device_id=alert.device_id,
        tenant_id=alert.tenant_id,
        severity=alert.severity,
        message=alert.message,
        timestamp=alert.timestamp,
        oid_prefix=integration.get("snmp_oid_prefix", "1.3.6.1.4.1.99999"),
    )

    return DeliveryResult(
        integration_id=integration.get("id", "unknown"),
        integration_name=integration.get("name", "unknown"),
        delivery_type=DeliveryType.SNMP,
        success=result.success,
        error=result.error,
        duration_ms=result.duration_ms,
    )


async def dispatch_to_integration(alert: AlertPayload, integration: dict) -> DeliveryResult:
    """Dispatch alert to a single integration."""
    integration_type = integration.get("type", "webhook")
    if integration_type == "webhook":
        return await _deliver_webhook(alert, integration)
    elif integration_type == "snmp":
        return await _deliver_snmp(alert, integration)
    else:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.WEBHOOK,
            success=False,
            error=f"Unknown integration type: {integration_type}",
        )
```

### 5.2 Create delivery log migration

Create `db/migrations/012_delivery_log.sql`:

```sql
CREATE TABLE IF NOT EXISTS delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(64) NOT NULL,
    integration_id UUID NOT NULL,
    integration_name VARCHAR(128),
    delivery_type VARCHAR(16) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL,
    error TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_delivery_log_alert_id ON delivery_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_tenant_id ON delivery_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_created_at ON delivery_log(created_at);

ALTER TABLE delivery_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY delivery_log_tenant_policy ON delivery_log
    FOR ALL USING (tenant_id = current_setting('app.tenant_id', true));

GRANT SELECT, INSERT ON delivery_log TO pulse_app;
GRANT SELECT ON delivery_log TO pulse_operator;
```

### 5.3 Create unit tests

Create `tests/unit/test_alert_dispatcher.py`:

```python
"""Unit tests for alert dispatcher."""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from services.ui_iot.services.alert_dispatcher import (
    dispatch_alert,
    dispatch_to_integration,
    AlertPayload,
    DeliveryType,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def sample_alert():
    return AlertPayload(
        alert_id="alert-123",
        device_id="device-456",
        tenant_id="tenant-a",
        severity="critical",
        message="Test alert",
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def snmp_integration():
    return {
        "id": "int-1",
        "name": "Test SNMP",
        "type": "snmp",
        "snmp_host": "192.0.2.100",
        "snmp_port": 162,
        "snmp_config": {"version": "2c", "community": "public"},
        "enabled": True,
    }


class TestDispatcher:
    """Test dispatcher functionality."""

    @patch("services.ui_iot.services.alert_dispatcher.send_alert_trap")
    async def test_dispatch_snmp(self, mock_send, sample_alert, snmp_integration):
        """Test SNMP dispatch."""
        mock_send.return_value = AsyncMock(success=True, error=None, duration_ms=30.0)()
        result = await dispatch_alert(sample_alert, [snmp_integration])
        assert result.successful == 1

    async def test_skip_disabled(self, sample_alert, snmp_integration):
        """Test disabled integrations skipped."""
        snmp_integration["enabled"] = False
        result = await dispatch_alert(sample_alert, [snmp_integration])
        assert len(result.results) == 0

    async def test_unknown_type(self, sample_alert):
        """Test unknown type returns error."""
        integration = {"id": "1", "name": "Bad", "type": "email"}
        result = await dispatch_to_integration(sample_alert, integration)
        assert not result.success
        assert "Unknown" in result.error
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/services/alert_dispatcher.py` |
| CREATE | `db/migrations/012_delivery_log.sql` |
| CREATE | `tests/unit/test_alert_dispatcher.py` |

---

## Acceptance Criteria

- [ ] Dispatcher handles both webhook and SNMP
- [ ] Disabled integrations skipped
- [ ] Parallel delivery to multiple integrations
- [ ] Delivery log table created with RLS
- [ ] Unit tests pass

**Test**:
```bash
pytest tests/unit/test_alert_dispatcher.py -v
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/012_delivery_log.sql
```

---

## Commit

```
Add unified alert dispatcher

- Dispatcher handles webhook and SNMP
- Parallel delivery to multiple integrations
- delivery_log table with RLS
- Unit tests

Part of Phase 4: SNMP and Alternative Outputs
```
