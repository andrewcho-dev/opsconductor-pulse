# Task 002: WebSocket Service + Message Bus

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

The backend provides a WebSocket endpoint at `/api/v2/ws?token=JWT` that pushes live alerts and device telemetry. This task creates the client-side WebSocket manager (a non-React singleton) and a message bus for distributing incoming messages to subscribers.

**Key design decisions**:
1. **Non-React**: The WebSocket manager and message bus are plain TypeScript — no React hooks or components. This ensures the connection survives React re-renders.
2. **Pub/sub message bus**: Components subscribe to specific topics. The manager parses messages and publishes to the bus.
3. **Exponential backoff reconnect**: 1s → 2s → 4s → 8s → 16s → 30s (max). Resets on successful connection.
4. **Token refresh**: On reconnect, always use the latest token from Keycloak.

**Read first**:
- `frontend/src/services/auth/keycloak.ts` — keycloak singleton for getting current token
- `frontend/src/stores/ui-store.ts` — UIStore for connection status
- `frontend/src/stores/alert-store.ts` — AlertStore for live alerts
- `docs/cursor-prompts/phase19-realtime-dashboard/INSTRUCTIONS.md` — WebSocket protocol reference

---

## Task

### 2.1 Create WebSocket message types

**File**: `frontend/src/services/websocket/types.ts` (NEW)

```typescript
/** Messages sent FROM client TO server */
export interface WsSubscribeMessage {
  action: "subscribe" | "unsubscribe";
  type: "alerts" | "device";
  device_id?: string;
}

/** Messages sent FROM server TO client */
export interface WsAlertMessage {
  type: "alerts";
  alerts: Array<{
    alert_id: number;
    tenant_id: string;
    device_id: string;
    alert_type: string;
    severity: number;
    summary: string;
    status: string;
    created_at: string;
    fingerprint: string;
    details: Record<string, unknown> | null;
    closed_at: string | null;
  }>;
}

export interface WsTelemetryMessage {
  type: "telemetry";
  device_id: string;
  data: {
    timestamp: string;
    metrics: Record<string, number | boolean>;
  };
}

export interface WsSubscribedMessage {
  type: "subscribed" | "unsubscribed";
  channel: string;
  device_id?: string;
}

export interface WsErrorMessage {
  type: "error";
  message: string;
}

export type WsServerMessage =
  | WsAlertMessage
  | WsTelemetryMessage
  | WsSubscribedMessage
  | WsErrorMessage;

/** Message bus topics */
export type MessageTopic =
  | "alerts"
  | `telemetry:${string}`
  | "connection"
  | "error";
```

### 2.2 Create Message Bus

**File**: `frontend/src/services/websocket/message-bus.ts` (NEW)

A simple pub/sub system. Components subscribe to topics, the WebSocket manager publishes to topics. Subscriptions return an unsubscribe function for cleanup.

```typescript
type Handler = (data: unknown) => void;

export class MessageBus {
  private listeners = new Map<string, Set<Handler>>();

  /**
   * Subscribe to a topic. Returns an unsubscribe function.
   */
  on(topic: string, handler: Handler): () => void {
    if (!this.listeners.has(topic)) {
      this.listeners.set(topic, new Set());
    }
    this.listeners.get(topic)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.listeners.get(topic);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.listeners.delete(topic);
        }
      }
    };
  }

  /**
   * Publish data to all subscribers of a topic.
   */
  emit(topic: string, data: unknown): void {
    const handlers = this.listeners.get(topic);
    if (!handlers) return;
    handlers.forEach((handler) => {
      try {
        handler(data);
      } catch (err) {
        console.error(`MessageBus handler error on topic "${topic}":`, err);
      }
    });
  }

  /**
   * Remove all listeners (for cleanup).
   */
  clear(): void {
    this.listeners.clear();
  }

  /**
   * Get the number of subscribers for a topic.
   */
  listenerCount(topic: string): number {
    return this.listeners.get(topic)?.size || 0;
  }
}

/** Singleton instance */
export const messageBus = new MessageBus();
```

### 2.3 Create WebSocket Manager

**File**: `frontend/src/services/websocket/manager.ts` (NEW)

The core WebSocket connection manager. Handles connect, disconnect, subscribe, unsubscribe, reconnect with backoff, and message routing to the message bus.

```typescript
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
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
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
    const url = `${protocol}//${window.location.host}/api/v2/ws?token=${encodeURIComponent(token)}`;

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
  subscribe(type: "alerts"): void;
  subscribe(type: "device", deviceId: string): void;
  subscribe(type: "alerts" | "device", deviceId?: string): void {
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
  unsubscribe(type: "alerts"): void;
  unsubscribe(type: "device", deviceId: string): void;
  unsubscribe(type: "alerts" | "device", deviceId?: string): void {
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
```

### 2.4 Create module index

**File**: `frontend/src/services/websocket/index.ts` (NEW)

```typescript
export { wsManager, WebSocketManager } from "./manager";
export { messageBus, MessageBus } from "./message-bus";
export type {
  WsServerMessage,
  WsAlertMessage,
  WsTelemetryMessage,
  WsSubscribeMessage,
  WsSubscribedMessage,
  WsErrorMessage,
  MessageTopic,
} from "./types";
```

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/src/services/websocket/types.ts` | WebSocket message type definitions |
| CREATE | `frontend/src/services/websocket/message-bus.ts` | Pub/sub EventEmitter with singleton |
| CREATE | `frontend/src/services/websocket/manager.ts` | WebSocket connection manager with reconnect |
| CREATE | `frontend/src/services/websocket/index.ts` | Module exports |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

### Step 2: Verify TypeScript

```bash
cd /home/opsconductor/simcloud/frontend && npx tsc --noEmit
```

### Step 3: Verify files exist

```bash
ls /home/opsconductor/simcloud/frontend/src/services/websocket/
```

Should show: types.ts, message-bus.ts, manager.ts, index.ts

### Step 4: Verify implementation

Read the files and confirm:
- [ ] `MessageBus` has `on()`, `emit()`, `clear()` methods
- [ ] `on()` returns an unsubscribe function
- [ ] `WebSocketManager` connects with token from `keycloak.token`
- [ ] URL uses `wss:` for HTTPS pages, `ws:` for HTTP
- [ ] Token is URL-encoded in query parameter
- [ ] `onopen` resets retryCount and re-subscribes to active subscriptions
- [ ] `onmessage` routes to message bus topics: "alerts", "telemetry:{deviceId}"
- [ ] `onclose` triggers reconnect (unless intentional close)
- [ ] Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
- [ ] Max 20 retries before giving up
- [ ] `subscribe()` persists subscriptions for reconnect
- [ ] `unsubscribe()` removes from persisted subscriptions
- [ ] `disconnect()` sets `intentionalClose = true` (no auto-reconnect)
- [ ] Connection status events emitted: connecting, connected, disconnected, error

### Step 5: Verify backend tests

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] MessageBus pub/sub with topic-based routing
- [ ] WebSocketManager singleton connects to `/api/v2/ws`
- [ ] Token from keycloak.token injected as query parameter
- [ ] Auto-reconnect with exponential backoff (1s base, 30s max, 20 max retries)
- [ ] Subscription persistence across reconnects
- [ ] Connection status emitted to message bus
- [ ] Alert messages routed to "alerts" topic
- [ ] Telemetry messages routed to "telemetry:{deviceId}" topic
- [ ] Intentional disconnect prevents auto-reconnect
- [ ] All Python tests pass

---

## Commit

```
Add WebSocket service with message bus and auto-reconnect

WebSocket manager connects to /api/v2/ws with JWT auth.
Message bus distributes alerts and telemetry to subscribers.
Exponential backoff reconnect (1s-30s). Subscription
persistence across reconnects.

Phase 19 Task 2: WebSocket Service
```
