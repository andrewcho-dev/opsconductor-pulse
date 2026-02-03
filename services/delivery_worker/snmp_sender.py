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
