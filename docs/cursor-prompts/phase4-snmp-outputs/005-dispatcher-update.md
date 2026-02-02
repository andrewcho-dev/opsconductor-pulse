# Task 005: Dispatcher Update for SNMP

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

The alert dispatcher currently only sends webhooks. It needs to be updated to also send SNMP traps based on integration type. Routing rules already determine which integration receives an alert; now the dispatcher must handle both output types.

**Read first**:
- `services/ui_iot/services/webhook_dispatcher.py` (or equivalent alert dispatcher)
- `services/ui_iot/services/snmp_sender.py` (from Task 002)
- `services/ui_iot/models/integration.py` (integration types)

**Depends on**: Tasks 002, 003

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

from services.ui_iot.services.webhook_sender import send_webhook, WebhookResult
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


async def dispatch_alert(
    alert: AlertPayload,
    integrations: list[dict],
) -> DispatchResult:
    """
    Dispatch alert to all matched integrations.

    Args:
        alert: Alert data to send
        integrations: List of integration configs from database

    Returns:
        DispatchResult with delivery outcomes
    """
    results = []

    # Create delivery tasks for all integrations
    tasks = []
    for integration in integrations:
        if not integration.get("enabled", True):
            continue

        integration_type = integration.get("type", "webhook")

        if integration_type == "webhook":
            task = _deliver_webhook(alert, integration)
        elif integration_type == "snmp":
            task = _deliver_snmp(alert, integration)
        else:
            logger.warning(f"Unknown integration type: {integration_type}")
            continue

        tasks.append(task)

    # Execute all deliveries concurrently
    if tasks:
        delivery_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in delivery_results:
            if isinstance(result, Exception):
                logger.exception(f"Delivery task failed: {result}")
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
    failed = len(results) - successful

    return DispatchResult(
        alert_id=alert.alert_id,
        total_integrations=len(integrations),
        successful=successful,
        failed=failed,
        results=results,
    )


async def _deliver_webhook(
    alert: AlertPayload,
    integration: dict,
) -> DeliveryResult:
    """Deliver alert via webhook."""
    webhook_url = integration.get("webhook_url")
    webhook_secret = integration.get("webhook_secret")

    if not webhook_url:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.WEBHOOK,
            success=False,
            error="Missing webhook_url",
        )

    # Build webhook payload
    payload = {
        "alert_id": alert.alert_id,
        "device_id": alert.device_id,
        "tenant_id": alert.tenant_id,
        "severity": alert.severity,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat(),
        "metadata": alert.metadata or {},
    }

    result = await send_webhook(
        url=webhook_url,
        payload=payload,
        secret=webhook_secret,
    )

    return DeliveryResult(
        integration_id=integration.get("id", "unknown"),
        integration_name=integration.get("name", "unknown"),
        delivery_type=DeliveryType.WEBHOOK,
        success=result.success,
        error=result.error,
        duration_ms=result.duration_ms,
    )


async def _deliver_snmp(
    alert: AlertPayload,
    integration: dict,
) -> DeliveryResult:
    """Deliver alert via SNMP trap."""
    snmp_host = integration.get("snmp_host")
    snmp_port = integration.get("snmp_port", 162)
    snmp_config = integration.get("snmp_config", {})
    oid_prefix = integration.get("snmp_oid_prefix", "1.3.6.1.4.1.99999")

    if not snmp_host:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.SNMP,
            success=False,
            error="Missing snmp_host",
        )

    if not snmp_config:
        return DeliveryResult(
            integration_id=integration.get("id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.SNMP,
            success=False,
            error="Missing snmp_config",
        )

    result = await send_alert_trap(
        host=snmp_host,
        port=snmp_port,
        config=snmp_config,
        alert_id=alert.alert_id,
        device_id=alert.device_id,
        tenant_id=alert.tenant_id,
        severity=alert.severity,
        message=alert.message,
        timestamp=alert.timestamp,
        oid_prefix=oid_prefix,
    )

    return DeliveryResult(
        integration_id=integration.get("id", "unknown"),
        integration_name=integration.get("name", "unknown"),
        delivery_type=DeliveryType.SNMP,
        success=result.success,
        error=result.error,
        duration_ms=result.duration_ms,
    )


async def dispatch_to_integration(
    alert: AlertPayload,
    integration: dict,
) -> DeliveryResult:
    """
    Dispatch alert to a single integration.

    Useful for test delivery or retry scenarios.
    """
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

### 5.2 Update existing webhook worker to use dispatcher

If there's an existing webhook worker or background task, update it to use the new dispatcher:

```python
# In services/ui_iot/workers/alert_worker.py (or similar)

from services.ui_iot.services.alert_dispatcher import (
    dispatch_alert,
    AlertPayload,
)


async def process_alert(alert_data: dict, db):
    """Process an alert and dispatch to integrations."""

    # Get matched integrations from routing rules
    integrations = await get_matched_integrations(
        db,
        tenant_id=alert_data["tenant_id"],
        device_id=alert_data["device_id"],
        severity=alert_data["severity"],
    )

    if not integrations:
        logger.info(f"No integrations matched for alert {alert_data['id']}")
        return

    # Build alert payload
    alert = AlertPayload(
        alert_id=alert_data["id"],
        device_id=alert_data["device_id"],
        tenant_id=alert_data["tenant_id"],
        severity=alert_data["severity"],
        message=alert_data["message"],
        timestamp=alert_data["timestamp"],
        metadata=alert_data.get("metadata"),
    )

    # Dispatch to all matched integrations
    result = await dispatch_alert(alert, integrations)

    # Log results
    logger.info(
        f"Alert {alert.alert_id} dispatched: "
        f"{result.successful}/{result.total_integrations} successful"
    )

    # Store delivery results for audit
    for delivery in result.results:
        await store_delivery_log(db, alert.alert_id, delivery)
```

### 5.3 Create delivery log table migration

Create `db/migrations/012_delivery_log.sql`:

```sql
-- Delivery log for tracking alert dispatches
CREATE TABLE IF NOT EXISTS delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(64) NOT NULL,
    integration_id UUID NOT NULL,
    integration_name VARCHAR(128),
    delivery_type VARCHAR(16) NOT NULL,  -- 'webhook' or 'snmp'
    success BOOLEAN NOT NULL,
    error TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key to integrations (optional, for cleanup)
    CONSTRAINT fk_integration FOREIGN KEY (integration_id)
        REFERENCES integrations(id) ON DELETE SET NULL
);

-- Indexes for querying
CREATE INDEX IF NOT EXISTS idx_delivery_log_alert_id ON delivery_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_integration_id ON delivery_log(integration_id);
CREATE INDEX IF NOT EXISTS idx_delivery_log_created_at ON delivery_log(created_at);
CREATE INDEX IF NOT EXISTS idx_delivery_log_success ON delivery_log(success);

-- Add tenant_id for RLS
ALTER TABLE delivery_log ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_delivery_log_tenant_id ON delivery_log(tenant_id);

-- Enable RLS
ALTER TABLE delivery_log ENABLE ROW LEVEL SECURITY;

-- RLS policy for customers
CREATE POLICY delivery_log_tenant_policy ON delivery_log
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Grant to app roles
GRANT SELECT, INSERT ON delivery_log TO pulse_app;
GRANT SELECT ON delivery_log TO pulse_operator;

COMMENT ON TABLE delivery_log IS 'Log of alert delivery attempts (webhook and SNMP)';
```

### 5.4 Create dispatcher tests

Create `tests/unit/test_alert_dispatcher.py`:

```python
"""Unit tests for alert dispatcher."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

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
def webhook_integration():
    return {
        "id": "int-1",
        "name": "Test Webhook",
        "type": "webhook",
        "webhook_url": "https://example.com/hook",
        "webhook_secret": "secret123",
        "enabled": True,
    }


@pytest.fixture
def snmp_integration():
    return {
        "id": "int-2",
        "name": "Test SNMP",
        "type": "snmp",
        "snmp_host": "192.0.2.100",
        "snmp_port": 162,
        "snmp_config": {"version": "2c", "community": "public"},
        "snmp_oid_prefix": "1.3.6.1.4.1.99999",
        "enabled": True,
    }


class TestDispatchAlert:
    """Test dispatch_alert function."""

    @patch("services.ui_iot.services.alert_dispatcher.send_webhook")
    async def test_dispatch_webhook_success(
        self, mock_send, sample_alert, webhook_integration
    ):
        """Dispatch to webhook integration succeeds."""
        mock_send.return_value = AsyncMock(
            success=True, error=None, duration_ms=50.0
        )()

        result = await dispatch_alert(sample_alert, [webhook_integration])

        assert result.total_integrations == 1
        assert result.successful == 1
        assert result.failed == 0
        assert result.results[0].delivery_type == DeliveryType.WEBHOOK

    @patch("services.ui_iot.services.alert_dispatcher.send_alert_trap")
    async def test_dispatch_snmp_success(
        self, mock_send, sample_alert, snmp_integration
    ):
        """Dispatch to SNMP integration succeeds."""
        mock_send.return_value = AsyncMock(
            success=True, error=None, duration_ms=30.0
        )()

        result = await dispatch_alert(sample_alert, [snmp_integration])

        assert result.total_integrations == 1
        assert result.successful == 1
        assert result.results[0].delivery_type == DeliveryType.SNMP

    @patch("services.ui_iot.services.alert_dispatcher.send_webhook")
    @patch("services.ui_iot.services.alert_dispatcher.send_alert_trap")
    async def test_dispatch_mixed_integrations(
        self, mock_snmp, mock_webhook, sample_alert,
        webhook_integration, snmp_integration
    ):
        """Dispatch to both webhook and SNMP."""
        mock_webhook.return_value = AsyncMock(
            success=True, error=None, duration_ms=50.0
        )()
        mock_snmp.return_value = AsyncMock(
            success=True, error=None, duration_ms=30.0
        )()

        result = await dispatch_alert(
            sample_alert,
            [webhook_integration, snmp_integration]
        )

        assert result.total_integrations == 2
        assert result.successful == 2
        assert result.failed == 0

    async def test_skip_disabled_integration(
        self, sample_alert, webhook_integration
    ):
        """Disabled integrations are skipped."""
        webhook_integration["enabled"] = False

        result = await dispatch_alert(sample_alert, [webhook_integration])

        assert result.total_integrations == 1
        assert result.successful == 0
        assert result.failed == 0
        assert len(result.results) == 0


class TestDispatchToIntegration:
    """Test single integration dispatch."""

    @patch("services.ui_iot.services.alert_dispatcher.send_webhook")
    async def test_single_webhook(
        self, mock_send, sample_alert, webhook_integration
    ):
        """Dispatch to single webhook."""
        mock_send.return_value = AsyncMock(
            success=True, error=None, duration_ms=50.0
        )()

        result = await dispatch_to_integration(sample_alert, webhook_integration)

        assert result.success is True
        assert result.delivery_type == DeliveryType.WEBHOOK

    async def test_unknown_type(self, sample_alert):
        """Unknown integration type returns error."""
        integration = {"id": "int-1", "name": "Unknown", "type": "email"}

        result = await dispatch_to_integration(sample_alert, integration)

        assert result.success is False
        assert "Unknown integration type" in result.error
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/services/alert_dispatcher.py` |
| CREATE | `db/migrations/012_delivery_log.sql` |
| CREATE | `tests/unit/test_alert_dispatcher.py` |
| MODIFY | Existing alert worker if present |

## Acceptance Criteria

- [ ] Dispatcher handles both webhook and SNMP
- [ ] Disabled integrations skipped
- [ ] Parallel delivery to multiple integrations
- [ ] Delivery results returned
- [ ] Delivery log table created with RLS
- [ ] Unit tests pass

**Test**:
```bash
# Run unit tests
pytest tests/unit/test_alert_dispatcher.py -v

# Run migration
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/012_delivery_log.sql
```

## Commit

```
Add unified alert dispatcher for webhooks and SNMP

- AlertDispatcher handles both delivery types
- Parallel dispatch to multiple integrations
- DeliveryResult tracking
- delivery_log table with RLS
- Unit tests for dispatch logic

Part of Phase 4: SNMP and Alternative Outputs
```
