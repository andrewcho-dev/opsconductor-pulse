"""Manages streaming telemetry connections via MQTT subscription.

Each connected client (WebSocket or SSE) gets an asyncio.Queue.
The manager subscribes to MQTT topics for active tenants and distributes
incoming messages to matching queues.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import paho.mqtt.client as mqtt
from shared.config import require_env, optional_env

logger = logging.getLogger(__name__)

MQTT_HOST = optional_env("MQTT_HOST", "iot-mqtt")
MQTT_PORT = int(optional_env("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = require_env("MQTT_PASSWORD")
MAX_CONNECTIONS_PER_TENANT = int(optional_env("MAX_STREAM_CONNECTIONS_PER_TENANT", "10"))
STREAM_QUEUE_SIZE = int(optional_env("STREAM_QUEUE_SIZE", "100"))


@dataclass
class StreamSubscription:
    """Represents a single streaming client's subscription filters."""

    tenant_id: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=STREAM_QUEUE_SIZE))
    device_ids: set = field(default_factory=set)  # empty = all devices
    group_ids: set = field(default_factory=set)  # empty = no group filter (reserved)
    metric_names: set = field(default_factory=set)  # empty = all metrics
    connected_at: float = field(default_factory=time.time)
    event_counter: int = 0


class TelemetryStreamManager:
    """Manages MQTT subscriptions and distributes messages to streaming clients."""

    def __init__(self):
        self._subscriptions: list[StreamSubscription] = []
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._mqtt_client: Optional[mqtt.Client] = None
        self._subscribed_tenants: set[str] = set()
        self._started = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Start the MQTT client for telemetry streaming."""
        if self._started:
            return

        self._loop = loop
        self._mqtt_client = mqtt.Client(client_id="pulse-stream-manager")
        if MQTT_USERNAME and MQTT_PASSWORD:
            self._mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message

        try:
            self._mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            self._mqtt_client.loop_start()
            self._started = True
            logger.info(
                "TelemetryStreamManager MQTT connected to %s:%s",
                MQTT_HOST,
                MQTT_PORT,
            )
        except Exception as exc:
            logger.warning("TelemetryStreamManager MQTT connect failed: %s", exc)

    def stop(self) -> None:
        """Stop the MQTT client."""
        if self._mqtt_client:
            try:
                self._mqtt_client.loop_stop()
            finally:
                try:
                    self._mqtt_client.disconnect()
                finally:
                    self._started = False

    def _on_connect(self, client, userdata, flags, rc):
        """Re-subscribe to topics for all active tenants on reconnect."""
        logger.info("TelemetryStreamManager MQTT connected, rc=%s", rc)
        with self._lock:
            tenants = list(self._subscribed_tenants)
        for tenant_id in tenants:
            topic = f"tenant/{tenant_id}/device/+/telemetry"
            client.subscribe(topic)
            logger.debug("Re-subscribed to %s", topic)

    def _on_message(self, client, userdata, msg):
        """Distribute incoming MQTT message to matching subscriber queues."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        parts = msg.topic.split("/")
        if len(parts) < 5 or parts[0] != "tenant" or parts[2] != "device":
            return

        tenant_id = parts[1]
        device_id = parts[3]
        msg_type = parts[4]
        if msg_type != "telemetry":
            return

        metrics = payload.get("metrics", {}) or {}
        ts = payload.get("ts")

        event = {
            "type": "telemetry",
            "device_id": device_id,
            "tenant_id": tenant_id,
            "metrics": metrics,
            "timestamp": ts,
            "topic": msg.topic,
        }

        loop = self._loop
        if loop is None:
            return

        with self._lock:
            subs = list(self._subscriptions)

        for sub in subs:
            if sub.tenant_id != tenant_id:
                continue

            if sub.device_ids and device_id not in sub.device_ids:
                continue

            # Metric filter: include only if at least one requested metric is present
            if sub.metric_names:
                filtered_metrics = {k: v for k, v in metrics.items() if k in sub.metric_names}
                if not filtered_metrics:
                    continue
                event_copy = {**event, "metrics": filtered_metrics}
            else:
                event_copy = event

            def _enqueue(s: StreamSubscription = sub, e: dict = event_copy) -> None:
                try:
                    s.queue.put_nowait(e)
                    s.event_counter += 1
                except asyncio.QueueFull:
                    logger.debug("Stream queue full for tenant=%s, dropping event", tenant_id)

            # paho-mqtt callbacks run on a separate thread; enqueue on the asyncio loop thread.
            loop.call_soon_threadsafe(_enqueue)

    def register(
        self,
        tenant_id: str,
        device_ids: list[str] | None = None,
        metric_names: list[str] | None = None,
    ) -> StreamSubscription:
        """Register a new streaming subscription. Returns the subscription object."""
        with self._lock:
            tenant_count = sum(1 for s in self._subscriptions if s.tenant_id == tenant_id)
            if tenant_count >= MAX_CONNECTIONS_PER_TENANT:
                raise ConnectionError(
                    f"Max streaming connections ({MAX_CONNECTIONS_PER_TENANT}) reached for tenant"
                )

            sub = StreamSubscription(
                tenant_id=tenant_id,
                device_ids=set(device_ids) if device_ids else set(),
                metric_names=set(metric_names) if metric_names else set(),
            )
            self._subscriptions.append(sub)

        if tenant_id not in self._subscribed_tenants and self._mqtt_client:
            topic = f"tenant/{tenant_id}/device/+/telemetry"
            self._mqtt_client.subscribe(topic)
            self._subscribed_tenants.add(tenant_id)
            logger.info("Subscribed to MQTT topic: %s", topic)

        return sub

    def unregister(self, sub: StreamSubscription) -> None:
        """Remove a streaming subscription."""
        with self._lock:
            if sub in self._subscriptions:
                self._subscriptions.remove(sub)

            remaining = sum(1 for s in self._subscriptions if s.tenant_id == sub.tenant_id)
            if remaining == 0 and sub.tenant_id in self._subscribed_tenants:
                if self._mqtt_client:
                    topic = f"tenant/{sub.tenant_id}/device/+/telemetry"
                    self._mqtt_client.unsubscribe(topic)
                self._subscribed_tenants.discard(sub.tenant_id)
                logger.info("Unsubscribed from MQTT topic for tenant=%s", sub.tenant_id)

    def update_filters(
        self,
        sub: StreamSubscription,
        device_ids: list[str] | None = None,
        metric_names: list[str] | None = None,
    ) -> None:
        """Update subscription filters."""
        with self._lock:
            if device_ids is not None:
                sub.device_ids = set(device_ids)
            if metric_names is not None:
                sub.metric_names = set(metric_names)

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)

    def tenant_connection_count(self, tenant_id: str) -> int:
        with self._lock:
            return sum(1 for s in self._subscriptions if s.tenant_id == tenant_id)


# Singleton instance
stream_manager = TelemetryStreamManager()

