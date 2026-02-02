# Task 002: SNMP Trap Sender

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need an SNMP trap sender that can send alert notifications to customer-configured SNMP destinations. Must support both SNMPv2c (community string) and SNMPv3 (authentication/privacy).

**Read first**:
- `services/ui_iot/schemas/snmp.py` (SNMP config schemas from Task 001)
- `services/ui_iot/services/webhook_sender.py` (similar pattern)
- pysnmp documentation: https://pysnmp.readthedocs.io/

**Depends on**: Task 001

## Task

### 2.1 Add pysnmp dependency

Add to `services/ui_iot/requirements.txt`:

```
pysnmp>=4.4.12
pysnmp-lextudio>=5.0.0  # Modern maintained fork
```

### 2.2 Create SNMP sender service

Create `services/ui_iot/services/snmp_sender.py`:

```python
"""SNMP trap sender for alert notifications."""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from pysnmp.hlapi.asyncio import (
    sendNotification,
    SnmpEngine,
    CommunityData,
    UsmUserData,
    UdpTransportTarget,
    ContextData,
    NotificationType,
    ObjectType,
    ObjectIdentity,
    OctetString,
    Integer32,
    TimeTicks,
)
from pysnmp.hlapi.asyncio import usmHMACSHAAuthProtocol, usmAesCfb128Protocol
from pysnmp.hlapi.asyncio import usmHMACMD5AuthProtocol, usmDESPrivProtocol

logger = logging.getLogger(__name__)

# Map config strings to pysnmp protocol objects
AUTH_PROTOCOLS = {
    "MD5": usmHMACMD5AuthProtocol,
    "SHA": usmHMACSHAAuthProtocol,
}

PRIV_PROTOCOLS = {
    "DES": usmDESPrivProtocol,
    "AES": usmAesCfb128Protocol,
}

# Default OIDs for alert trap varbinds
DEFAULT_OID_PREFIX = "1.3.6.1.4.1.99999"  # Enterprise OID (placeholder)


@dataclass
class SNMPTrapResult:
    """Result of SNMP trap send attempt."""
    success: bool
    error: Optional[str] = None
    destination: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class AlertTrapData:
    """Alert data to include in SNMP trap."""
    alert_id: str
    device_id: str
    tenant_id: str
    severity: str  # critical, warning, info
    message: str
    timestamp: datetime


class SNMPSender:
    """Send SNMP traps for alerts."""

    def __init__(self, timeout: float = 5.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.engine = SnmpEngine()

    async def send_trap(
        self,
        host: str,
        port: int,
        config: dict,
        alert: AlertTrapData,
        oid_prefix: str = DEFAULT_OID_PREFIX,
    ) -> SNMPTrapResult:
        """
        Send SNMP trap for an alert.

        Args:
            host: Destination hostname or IP
            port: Destination port (usually 162)
            config: SNMP config dict (v2c or v3)
            alert: Alert data to send
            oid_prefix: Base OID for varbinds

        Returns:
            SNMPTrapResult with success/failure info
        """
        start_time = asyncio.get_event_loop().time()
        destination = f"{host}:{port}"

        try:
            # Build auth data based on version
            if config.get("version") == "2c":
                auth_data = CommunityData(config["community"])
            elif config.get("version") == "3":
                auth_data = self._build_v3_auth(config)
            else:
                return SNMPTrapResult(
                    success=False,
                    error=f"Unsupported SNMP version: {config.get('version')}",
                    destination=destination,
                )

            # Build transport target
            transport = UdpTransportTarget(
                (host, port),
                timeout=self.timeout,
                retries=self.retries,
            )

            # Build trap varbinds
            varbinds = self._build_alert_varbinds(alert, oid_prefix)

            # Send notification
            error_indication, error_status, error_index, var_binds = await sendNotification(
                self.engine,
                auth_data,
                transport,
                ContextData(),
                "trap",
                NotificationType(
                    ObjectIdentity(f"{oid_prefix}.1.0.1")  # Alert trap OID
                ),
                *varbinds,
            )

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if error_indication:
                logger.warning(
                    f"SNMP trap failed to {destination}: {error_indication}"
                )
                return SNMPTrapResult(
                    success=False,
                    error=str(error_indication),
                    destination=destination,
                    duration_ms=duration_ms,
                )

            if error_status:
                error_msg = f"{error_status.prettyPrint()} at {error_index}"
                logger.warning(f"SNMP trap error to {destination}: {error_msg}")
                return SNMPTrapResult(
                    success=False,
                    error=error_msg,
                    destination=destination,
                    duration_ms=duration_ms,
                )

            logger.info(
                f"SNMP trap sent to {destination} for alert {alert.alert_id}"
            )
            return SNMPTrapResult(
                success=True,
                destination=destination,
                duration_ms=duration_ms,
            )

        except asyncio.TimeoutError:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return SNMPTrapResult(
                success=False,
                error="Timeout waiting for response",
                destination=destination,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.exception(f"SNMP trap failed to {destination}: {e}")
            return SNMPTrapResult(
                success=False,
                error=str(e),
                destination=destination,
                duration_ms=duration_ms,
            )

    def _build_v3_auth(self, config: dict) -> UsmUserData:
        """Build SNMPv3 authentication data."""
        auth_protocol = AUTH_PROTOCOLS.get(
            config.get("auth_protocol", "SHA"),
            usmHMACSHAAuthProtocol,
        )

        priv_protocol = None
        priv_key = None
        if config.get("priv_protocol") and config.get("priv_password"):
            priv_protocol = PRIV_PROTOCOLS.get(
                config["priv_protocol"],
                usmAesCfb128Protocol,
            )
            priv_key = config["priv_password"]

        return UsmUserData(
            config["username"],
            config["auth_password"],
            priv_key,
            authProtocol=auth_protocol,
            privProtocol=priv_protocol,
        )

    def _build_alert_varbinds(
        self, alert: AlertTrapData, oid_prefix: str
    ) -> list:
        """Build varbinds for alert trap."""
        # OID structure:
        # .1.1 = alertId (string)
        # .1.2 = deviceId (string)
        # .1.3 = tenantId (string)
        # .1.4 = severity (integer: 1=info, 2=warning, 3=critical)
        # .1.5 = message (string)
        # .1.6 = timestamp (timeticks)

        severity_map = {"info": 1, "warning": 2, "critical": 3}
        severity_int = severity_map.get(alert.severity.lower(), 1)

        # Calculate uptime in hundredths of seconds (timeticks)
        uptime = int((datetime.utcnow() - alert.timestamp).total_seconds() * 100)

        return [
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.1"),
                OctetString(alert.alert_id),
            ),
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.2"),
                OctetString(alert.device_id),
            ),
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.3"),
                OctetString(alert.tenant_id),
            ),
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.4"),
                Integer32(severity_int),
            ),
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.5"),
                OctetString(alert.message),
            ),
            ObjectType(
                ObjectIdentity(f"{oid_prefix}.1.6"),
                TimeTicks(uptime),
            ),
        ]


# Singleton instance
_snmp_sender: Optional[SNMPSender] = None


def get_snmp_sender() -> SNMPSender:
    """Get or create SNMP sender instance."""
    global _snmp_sender
    if _snmp_sender is None:
        _snmp_sender = SNMPSender()
    return _snmp_sender


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
    oid_prefix: str = DEFAULT_OID_PREFIX,
) -> SNMPTrapResult:
    """
    Convenience function to send alert trap.

    Args:
        host: SNMP destination host
        port: SNMP destination port
        config: SNMP config (v2c or v3)
        alert_id: Alert identifier
        device_id: Device that generated alert
        tenant_id: Tenant ID
        severity: Alert severity (critical, warning, info)
        message: Alert message
        timestamp: Alert timestamp
        oid_prefix: Base OID for varbinds

    Returns:
        SNMPTrapResult
    """
    sender = get_snmp_sender()
    alert = AlertTrapData(
        alert_id=alert_id,
        device_id=device_id,
        tenant_id=tenant_id,
        severity=severity,
        message=message,
        timestamp=timestamp,
    )
    return await sender.send_trap(host, port, config, alert, oid_prefix)
```

### 2.3 Create SNMP sender tests

Create `tests/unit/test_snmp_sender.py`:

```python
"""Unit tests for SNMP sender."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from services.ui_iot.services.snmp_sender import (
    SNMPSender,
    AlertTrapData,
    SNMPTrapResult,
    send_alert_trap,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestSNMPSender:
    """Test SNMP sender functionality."""

    def test_build_v2c_varbinds(self):
        """Test building varbinds for SNMPv2c trap."""
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )

        varbinds = sender._build_alert_varbinds(alert, "1.3.6.1.4.1.99999")

        assert len(varbinds) == 6  # 6 varbinds

    def test_severity_mapping(self):
        """Test severity string to integer mapping."""
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="warning",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )

        varbinds = sender._build_alert_varbinds(alert, "1.3.6.1.4.1.99999")

        # Severity varbind is at index 3
        severity_varbind = varbinds[3]
        # Check it maps to 2 (warning)
        assert "2" in str(severity_varbind)

    @patch("services.ui_iot.services.snmp_sender.sendNotification")
    async def test_send_trap_v2c_success(self, mock_send):
        """Test successful SNMPv2c trap send."""
        mock_send.return_value = (None, None, None, [])

        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )

        result = await sender.send_trap(
            host="192.168.1.100",
            port=162,
            config={"version": "2c", "community": "public"},
            alert=alert,
        )

        assert result.success is True
        assert result.destination == "192.168.1.100:162"
        assert result.error is None

    @patch("services.ui_iot.services.snmp_sender.sendNotification")
    async def test_send_trap_error_indication(self, mock_send):
        """Test trap with error indication."""
        mock_send.return_value = ("Connection timeout", None, None, [])

        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )

        result = await sender.send_trap(
            host="192.168.1.100",
            port=162,
            config={"version": "2c", "community": "public"},
            alert=alert,
        )

        assert result.success is False
        assert "Connection timeout" in result.error

    async def test_unsupported_version(self):
        """Test unsupported SNMP version."""
        sender = SNMPSender()
        alert = AlertTrapData(
            alert_id="alert-123",
            device_id="device-456",
            tenant_id="tenant-a",
            severity="critical",
            message="Test alert",
            timestamp=datetime.utcnow(),
        )

        result = await sender.send_trap(
            host="192.168.1.100",
            port=162,
            config={"version": "1"},  # v1 not supported
            alert=alert,
        )

        assert result.success is False
        assert "Unsupported SNMP version" in result.error
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/requirements.txt` |
| CREATE | `services/ui_iot/services/snmp_sender.py` |
| CREATE | `tests/unit/test_snmp_sender.py` |

## Acceptance Criteria

- [ ] pysnmp dependency added
- [ ] SNMPSender class supports v2c authentication
- [ ] SNMPSender class supports v3 authentication
- [ ] Alert data mapped to OID varbinds
- [ ] Timeout and retry handling implemented
- [ ] Unit tests pass

**Test**:
```bash
# Run unit tests
pytest tests/unit/test_snmp_sender.py -v

# Manual test (requires SNMP trap receiver)
# python -c "
# import asyncio
# from services.ui_iot.services.snmp_sender import send_alert_trap
# from datetime import datetime
# result = asyncio.run(send_alert_trap(
#     host='localhost', port=1162,
#     config={'version': '2c', 'community': 'public'},
#     alert_id='test-1', device_id='dev-1', tenant_id='tenant-a',
#     severity='warning', message='Test trap', timestamp=datetime.utcnow()
# ))
# print(result)
# "
```

## Commit

```
Add SNMP trap sender service

- pysnmp dependency for SNMP protocol support
- SNMPSender class with v2c and v3 support
- Alert data to OID varbind mapping
- Timeout and retry handling
- Unit tests for trap sending

Part of Phase 4: SNMP and Alternative Outputs
```
