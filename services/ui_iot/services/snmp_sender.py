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

AUTH_PROTOCOLS = {
    "MD5": usmHMACMD5AuthProtocol,
    "SHA": usmHMACSHAAuthProtocol,
}

PRIV_PROTOCOLS = {
    "DES": usmDESPrivProtocol,
    "AES": usmAesCfb128Protocol,
}

DEFAULT_OID_PREFIX = "1.3.6.1.4.1.99999"


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
    severity: str
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
        """Send SNMP trap for an alert."""
        start_time = asyncio.get_event_loop().time()
        destination = f"{host}:{port}"

        try:
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

            transport = UdpTransportTarget(
                (host, port),
                timeout=self.timeout,
                retries=self.retries,
            )

            varbinds = self._build_alert_varbinds(alert, oid_prefix)

            error_indication, error_status, error_index, var_binds = await sendNotification(
                self.engine,
                auth_data,
                transport,
                ContextData(),
                "trap",
                NotificationType(ObjectIdentity(f"{oid_prefix}.1.0.1")),
                *varbinds,
            )

            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            if error_indication:
                return SNMPTrapResult(
                    success=False,
                    error=str(error_indication),
                    destination=destination,
                    duration_ms=duration_ms,
                )

            if error_status:
                return SNMPTrapResult(
                    success=False,
                    error=f"{error_status.prettyPrint()} at {error_index}",
                    destination=destination,
                    duration_ms=duration_ms,
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
                error="Timeout",
                destination=destination,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
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

    def _build_alert_varbinds(self, alert: AlertTrapData, oid_prefix: str) -> list:
        """Build varbinds for alert trap."""
        severity_map = {"info": 1, "warning": 2, "critical": 3}
        severity_int = severity_map.get(alert.severity.lower(), 1)
        uptime = int((datetime.utcnow() - alert.timestamp).total_seconds() * 100)

        return [
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.1"), OctetString(alert.alert_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.2"), OctetString(alert.device_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.3"), OctetString(alert.tenant_id)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.4"), Integer32(severity_int)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.5"), OctetString(alert.message)),
            ObjectType(ObjectIdentity(f"{oid_prefix}.1.6"), TimeTicks(uptime)),
        ]


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
    """Convenience function to send alert trap."""
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
