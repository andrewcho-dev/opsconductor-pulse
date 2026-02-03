"""Unified alert dispatcher for webhooks and SNMP traps."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from enum import Enum

import httpx

try:
    from services.snmp_sender import send_alert_trap
except ImportError:  # Fallback for local namespace package usage
    from services.ui_iot.services.snmp_sender import send_alert_trap

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
                results.append(
                    DeliveryResult(
                        integration_id="unknown",
                        integration_name="unknown",
                        delivery_type=DeliveryType.WEBHOOK,
                        success=False,
                        error=str(result),
                    )
                )
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
    webhook_url = integration.get("webhook_url") or integration.get("url")
    if not webhook_url:
        return DeliveryResult(
            integration_id=integration.get("integration_id", "unknown"),
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
    if alert.metadata:
        payload["metadata"] = alert.metadata

    start_time = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            success = 200 <= response.status_code < 300
            error = None if success else f"HTTP {response.status_code}"
            return DeliveryResult(
                integration_id=integration.get("integration_id", "unknown"),
                integration_name=integration.get("name", "unknown"),
                delivery_type=DeliveryType.WEBHOOK,
                success=success,
                error=error,
                duration_ms=duration_ms,
            )
    except Exception as e:
        duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return DeliveryResult(
            integration_id=integration.get("integration_id", "unknown"),
            integration_name=integration.get("name", "unknown"),
            delivery_type=DeliveryType.WEBHOOK,
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


async def _deliver_snmp(alert: AlertPayload, integration: dict) -> DeliveryResult:
    """Deliver alert via SNMP trap."""
    snmp_host = integration.get("snmp_host")
    snmp_config = integration.get("snmp_config")

    if not snmp_host or not snmp_config:
        return DeliveryResult(
            integration_id=integration.get("integration_id", "unknown"),
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
        integration_id=integration.get("integration_id", "unknown"),
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
    if integration_type == "snmp":
        return await _deliver_snmp(alert, integration)
    return DeliveryResult(
        integration_id=integration.get("integration_id", "unknown"),
        integration_name=integration.get("name", "unknown"),
        delivery_type=DeliveryType.WEBHOOK,
        success=False,
        error=f"Unknown integration type: {integration_type}",
    )
