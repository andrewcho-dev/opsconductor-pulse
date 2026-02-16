"""
High-performance audit logger with buffered batch writes.
Handles 10,000+ events/second via in-memory buffering and COPY bulk inserts.
"""

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Deque

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    timestamp: datetime
    tenant_id: Optional[str]
    event_type: str
    category: str
    severity: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    entity_name: Optional[str]
    action: str
    message: str
    details: Optional[dict]
    source_service: str
    actor_type: str
    actor_id: Optional[str]
    actor_name: Optional[str]
    ip_address: Optional[str]
    request_id: Optional[str]
    duration_ms: Optional[int]

    def to_tuple(self):
        return (
            self.timestamp,
            self.tenant_id,
            self.event_type,
            self.category,
            self.severity,
            self.entity_type,
            self.entity_id,
            self.entity_name,
            self.action,
            self.message,
            json.dumps(self.details) if self.details else None,
            self.source_service,
            self.actor_type,
            self.actor_id,
            self.actor_name,
            self.ip_address,
            self.request_id,
            self.duration_ms,
        )


class AuditLogger:
    """
    Buffered audit logger with async batch writes.

    - Events are buffered in memory
    - Flushed every flush_interval_ms OR when buffer hits batch_size
    - Uses COPY for fast bulk inserts
    - Fire-and-forget: never blocks the caller
    """

    COLUMNS = [
        "timestamp",
        "tenant_id",
        "event_type",
        "category",
        "severity",
        "entity_type",
        "entity_id",
        "entity_name",
        "action",
        "message",
        "details",
        "source_service",
        "actor_type",
        "actor_id",
        "actor_name",
        "ip_address",
        "request_id",
        "duration_ms",
    ]

    def __init__(
        self,
        pool: asyncpg.Pool,
        service_name: str,
        batch_size: int = 1000,
        flush_interval_ms: int = 100,
        max_buffer_size: int = 50000,
    ):
        self.pool = pool
        self.service_name = service_name
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self.max_buffer_size = max_buffer_size

        self.buffer: Deque[AuditEvent] = deque(maxlen=max_buffer_size)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

        # Stats
        self.events_logged = 0
        self.events_flushed = 0
        self.flush_errors = 0

    async def start(self):
        """Start the background flush loop."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("AuditLogger started for %s", self.service_name)

    async def stop(self):
        """Stop the flush loop and flush remaining events."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()
        logger.info(
            "AuditLogger stopped. Total: %s logged, %s flushed",
            self.events_logged,
            self.events_flushed,
        )

    async def _flush_loop(self):
        """Background loop that flushes buffer periodically."""
        while self._running:
            await asyncio.sleep(self.flush_interval_ms / 1000)
            if len(self.buffer) > 0:
                await self._flush()

    async def _flush(self):
        """Flush buffered events to database using COPY."""
        if len(self.buffer) == 0:
            return

        async with self._lock:
            events = []
            while self.buffer:
                events.append(self.buffer.popleft())

            if not events:
                return

            try:
                async with self.pool.acquire() as conn:
                    await conn.copy_records_to_table(
                        "audit_log",
                        records=[e.to_tuple() for e in events],
                        columns=self.COLUMNS,
                    )
                self.events_flushed += len(events)
            except Exception as exc:
                self.flush_errors += 1
                logger.error("Audit flush failed (%s events): %s", len(events), exc)
                for event in reversed(events):
                    if len(self.buffer) < self.max_buffer_size:
                        self.buffer.appendleft(event)

    def log(
        self,
        event_type: str,
        category: str,
        action: str,
        message: str,
        *,
        tenant_id: str | None = None,
        severity: str = "info",
        entity_type: str | None = None,
        entity_id: str | None = None,
        entity_name: str | None = None,
        details: dict | None = None,
        actor_type: str = "system",
        actor_id: str | None = None,
        actor_name: str | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
        duration_ms: int | None = None,
    ):
        """
        Log an audit event. Non-blocking, adds to buffer.
        Call this synchronously - no await needed.
        """
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            event_type=event_type,
            category=category,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            message=message,
            details=details,
            source_service=self.service_name,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_name=actor_name,
            ip_address=ip_address,
            request_id=request_id,
            duration_ms=duration_ms,
        )

        self.buffer.append(event)
        self.events_logged += 1

        if len(self.buffer) >= self.batch_size:
            asyncio.create_task(self._flush())

    # Convenience methods for common event types
    def device_telemetry(self, tenant_id: str, device_id: str, msg_type: str, metrics: list):
        self.log(
            "device.telemetry",
            "device",
            "receive",
            f"Received {msg_type} from {device_id}",
            tenant_id=tenant_id,
            entity_type="device",
            entity_id=device_id,
            details={"msg_type": msg_type, "metrics": metrics},
        )

    def device_state_change(self, tenant_id: str, device_id: str, old_state: str, new_state: str):
        severity = "warning" if new_state in ("stale", "offline") else "info"
        self.log(
            "device.state_change",
            "device",
            "state_change",
            f"Device {device_id}: {old_state} -> {new_state}",
            tenant_id=tenant_id,
            entity_type="device",
            entity_id=device_id,
            severity=severity,
            details={"old_state": old_state, "new_state": new_state},
        )

    def device_rejected(self, tenant_id: str, device_id: str, reason: str, details: dict | None = None):
        self.log(
            "device.rejected",
            "device",
            "reject",
            f"Rejected message from {device_id}: {reason}",
            tenant_id=tenant_id,
            entity_type="device",
            entity_id=device_id,
            severity="warning",
            details={"reason": reason, **(details or {})},
        )

    def alert_created(self, tenant_id: str, alert_id: str, alert_type: str, device_id: str, message: str):
        self.log(
            "alert.created",
            "alert",
            "create",
            message,
            tenant_id=tenant_id,
            entity_type="alert",
            entity_id=alert_id,
            severity="warning",
            details={"alert_type": alert_type, "device_id": device_id},
        )

    def alert_closed(self, tenant_id: str, alert_id: str, reason: str):
        self.log(
            "alert.closed",
            "alert",
            "close",
            f"Alert {alert_id} closed: {reason}",
            tenant_id=tenant_id,
            entity_type="alert",
            entity_id=alert_id,
        )

    def rule_triggered(
        self,
        tenant_id: str,
        rule_id: str,
        rule_name: str,
        device_id: str,
        metric: str,
        value: float,
        threshold: float,
        operator: str,
    ):
        self.log(
            "rule.triggered",
            "rule",
            "trigger",
            f"Rule '{rule_name}' triggered: {metric}={value} {operator} {threshold}",
            tenant_id=tenant_id,
            entity_type="rule",
            entity_id=str(rule_id),
            details={
                "device_id": device_id,
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "operator": operator,
            },
        )

    def delivery_queued(self, tenant_id: str, job_id: str, alert_id: str, integration_type: str):
        self.log(
            "delivery.queued",
            "delivery",
            "queue",
            f"Delivery queued for alert {alert_id} via {integration_type}",
            tenant_id=tenant_id,
            entity_type="delivery",
            entity_id=str(job_id),
            details={"alert_id": alert_id, "integration_type": integration_type},
        )

    def delivery_succeeded(
        self,
        tenant_id: str,
        job_id: str,
        integration_type: str,
        destination: str,
        duration_ms: int,
    ):
        self.log(
            "delivery.succeeded",
            "delivery",
            "deliver",
            f"Delivered via {integration_type} to {destination}",
            tenant_id=tenant_id,
            entity_type="delivery",
            entity_id=str(job_id),
            duration_ms=duration_ms,
            details={"integration_type": integration_type},
        )

    def delivery_failed(
        self,
        tenant_id: str,
        job_id: str,
        integration_type: str,
        error: str,
        attempt: int,
    ):
        self.log(
            "delivery.failed",
            "delivery",
            "fail",
            f"Delivery failed via {integration_type}: {error}",
            tenant_id=tenant_id,
            entity_type="delivery",
            entity_id=str(job_id),
            severity="error",
            details={"error": error, "attempt": attempt},
        )

    def notification_delivered(
        self,
        tenant_id: str,
        channel_type: str,
        channel_id: str | None = None,
        status: str = "delivered",
        details: dict | None = None,
    ):
        """Log a successful notification delivery."""
        self.log(
            "NOTIFICATION_DELIVERED",
            "notification",
            "deliver",
            f"Notification delivered via {channel_type}",
            tenant_id=tenant_id,
            entity_type="notification_channel",
            entity_id=channel_id,
            severity="info",
            details={"status": status, **(details or {})},
        )

    def notification_failed(
        self,
        tenant_id: str,
        channel_type: str,
        channel_id: str | None = None,
        error: str = "",
        details: dict | None = None,
    ):
        """Log a failed notification delivery."""
        self.log(
            "NOTIFICATION_FAILED",
            "notification",
            "deliver",
            f"Notification delivery failed via {channel_type}: {error}",
            tenant_id=tenant_id,
            entity_type="notification_channel",
            entity_id=channel_id,
            severity="warning",
            details={"error": error, **(details or {})},
        )

    def config_changed(
        self,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        entity_name: str,
        user_id: str,
        username: str,
        ip_address: str | None = None,
        details: dict | None = None,
    ):
        self.log(
            f"{entity_type}.{action}",
            "config",
            action,
            f"User {username} {action}d {entity_type} '{entity_name}'",
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_name=entity_name,
            actor_type="user",
            actor_id=user_id,
            actor_name=username,
            ip_address=ip_address,
            details=details,
        )

    def error(self, tenant_id: str, message: str, details: dict | None = None):
        self.log(
            "system.error",
            "error",
            "error",
            message,
            tenant_id=tenant_id,
            severity="error",
            details=details,
        )

    def auth_success(
        self,
        tenant_id: str,
        user_id: str,
        email: str,
        ip_address: str,
        details: dict | None = None,
    ):
        self.log(
            "auth.login_success",
            "auth",
            "login",
            f"Successful authentication for {email}",
            tenant_id=tenant_id,
            actor_type="user",
            actor_id=user_id,
            actor_name=email,
            ip_address=ip_address,
            details=details,
        )

    def auth_failure(
        self,
        reason: str,
        ip_address: str,
        details: dict | None = None,
    ):
        self.log(
            "auth.login_failure",
            "auth",
            "login_failure",
            f"Authentication failed: {reason}",
            severity="warning",
            ip_address=ip_address,
            details={"reason": reason, **(details or {})},
        )

    def auth_token_refresh(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        details: dict | None = None,
    ):
        self.log(
            "auth.token_refresh",
            "auth",
            "refresh",
            f"Token refreshed for {email or 'unknown'}",
            tenant_id=tenant_id,
            actor_type="user",
            actor_id=user_id,
            actor_name=email,
            ip_address=ip_address,
            details=details,
        )


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> Optional[AuditLogger]:
    return _audit_logger


def init_audit_logger(pool: asyncpg.Pool, service_name: str, **kwargs) -> AuditLogger:
    global _audit_logger
    _audit_logger = AuditLogger(pool, service_name, **kwargs)
    return _audit_logger
