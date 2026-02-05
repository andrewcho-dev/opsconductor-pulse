import logging
from dataclasses import dataclass, field

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class WSConnection:
    """Represents a single WebSocket client connection with its subscriptions."""
    websocket: WebSocket
    tenant_id: str
    user: dict
    device_subscriptions: set = field(default_factory=set)
    alert_subscription: bool = False


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.connections: list[WSConnection] = []

    async def connect(self, websocket: WebSocket, tenant_id: str, user: dict) -> WSConnection:
        """Accept a WebSocket connection and track it."""
        await websocket.accept()
        conn = WSConnection(websocket=websocket, tenant_id=tenant_id, user=user)
        self.connections.append(conn)
        logger.info("[ws] connected: tenant=%s email=%s", tenant_id, user.get("email"))
        return conn

    async def disconnect(self, conn: WSConnection):
        """Remove a connection from tracking."""
        if conn in self.connections:
            self.connections.remove(conn)
        logger.info("[ws] disconnected: tenant=%s", conn.tenant_id)

    def subscribe_device(self, conn: WSConnection, device_id: str):
        """Add a device to the connection's telemetry subscriptions."""
        conn.device_subscriptions.add(device_id)

    def unsubscribe_device(self, conn: WSConnection, device_id: str):
        """Remove a device from the connection's telemetry subscriptions."""
        conn.device_subscriptions.discard(device_id)

    def subscribe_alerts(self, conn: WSConnection):
        """Enable alert push for this connection."""
        conn.alert_subscription = True

    def unsubscribe_alerts(self, conn: WSConnection):
        """Disable alert push for this connection."""
        conn.alert_subscription = False

    @property
    def connection_count(self) -> int:
        return len(self.connections)


manager = ConnectionManager()
