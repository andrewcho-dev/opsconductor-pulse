import keycloak from "@/services/auth/keycloak";
import { messageBus } from "./message-bus";
import type { WsServerMessage, WsSubscribeMessage } from "./types";

const MAX_RETRY_DELAY = 30_000; // 30 seconds
const BASE_RETRY_DELAY = 1_000; // 1 second
const MAX_RETRIES = 20;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private retryCount = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;
  private subscriptions: WsSubscribeMessage[] = [];

  /**
   * Connect to the WebSocket endpoint using the current Keycloak token.
   */
  connect(): void {
    // Don't connect if already connected or connecting
    if (
      this.ws?.readyState === WebSocket.OPEN ||
      this.ws?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    const token = keycloak.token;
    if (!token) {
      console.warn("WebSocketManager: No token available, skipping connect");
      messageBus.emit("connection", { status: "error", message: "No auth token" });
      return;
    }

    this.intentionalClose = false;
    messageBus.emit("connection", { status: "connecting" });

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/api/v2/ws?token=${encodeURIComponent(
      token
    )}`;

    try {
      this.ws = new WebSocket(url);
    } catch (err) {
      console.error("WebSocketManager: Failed to create WebSocket", err);
      messageBus.emit("connection", { status: "error", message: "Connection failed" });
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.retryCount = 0;
      messageBus.emit("connection", { status: "connected" });

      // Re-subscribe to previously active subscriptions
      for (const sub of this.subscriptions) {
        this.send(sub);
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as WsServerMessage;
        this.handleMessage(msg);
      } catch (err) {
        console.error("WebSocketManager: Failed to parse message", err);
      }
    };

    this.ws.onclose = (event) => {
      this.ws = null;
      messageBus.emit("connection", {
        status: "disconnected",
        code: event.code,
        reason: event.reason,
      });

      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // The onclose handler will fire after onerror, so we just log here
      messageBus.emit("connection", { status: "error", message: "WebSocket error" });
    };
  }

  /**
   * Intentionally disconnect. Does NOT auto-reconnect.
   */
  disconnect(): void {
    this.intentionalClose = true;
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
    this.retryCount = 0;
    messageBus.emit("connection", { status: "disconnected" });
  }

  /**
   * Subscribe to a channel. Persists across reconnects.
   */
  subscribe(type: "alerts" | "fleet"): void;
  subscribe(type: "device", deviceId: string): void;
  subscribe(type: "alerts" | "device" | "fleet", deviceId?: string): void {
    const msg: WsSubscribeMessage = { action: "subscribe", type };
    if (type === "device" && deviceId) {
      msg.device_id = deviceId;
    }

    // Track subscription for re-subscribe on reconnect
    const exists = this.subscriptions.some(
      (s) => s.type === type && s.device_id === deviceId
    );
    if (!exists) {
      this.subscriptions.push(msg);
    }

    this.send(msg);
  }

  /**
   * Unsubscribe from a channel.
   */
  unsubscribe(type: "alerts" | "fleet"): void;
  unsubscribe(type: "device", deviceId: string): void;
  unsubscribe(type: "alerts" | "device" | "fleet", deviceId?: string): void {
    const msg: WsSubscribeMessage = { action: "unsubscribe", type };
    if (type === "device" && deviceId) {
      msg.device_id = deviceId;
    }

    // Remove from tracked subscriptions
    this.subscriptions = this.subscriptions.filter(
      (s) => !(s.type === type && s.device_id === deviceId)
    );

    this.send(msg);
  }

  /**
   * Check if currently connected.
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // --- Private methods ---

  private send(msg: WsSubscribeMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private handleMessage(msg: WsServerMessage): void {
    switch (msg.type) {
      case "alerts":
        messageBus.emit("alerts", msg.alerts);
        break;

      case "telemetry":
        messageBus.emit(`telemetry:${msg.device_id}`, msg.data);
        break;

      case "fleet_summary":
        messageBus.emit("fleet", msg.data);
        break;

      case "subscribed":
      case "unsubscribed":
        // Acknowledgement — no action needed
        break;

      case "error":
        console.warn("WebSocket server error:", msg.message);
        messageBus.emit("error", msg.message);
        break;

      default:
        console.warn("Unknown WebSocket message type:", msg);
    }
  }

  private scheduleReconnect(): void {
    if (this.retryCount >= MAX_RETRIES) {
      console.warn("WebSocketManager: Max retries reached, giving up");
      messageBus.emit("connection", {
        status: "error",
        message: "Max reconnection attempts reached",
      });
      return;
    }

    const delay = Math.min(
      BASE_RETRY_DELAY * Math.pow(2, this.retryCount),
      MAX_RETRY_DELAY
    );
    this.retryCount++;

    messageBus.emit("connection", {
      status: "disconnected",
      retryIn: delay,
      retryCount: this.retryCount,
    });

    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      this.connect();
    }, delay);
  }
}

/** Singleton instance */
export const wsManager = new WebSocketManager();
