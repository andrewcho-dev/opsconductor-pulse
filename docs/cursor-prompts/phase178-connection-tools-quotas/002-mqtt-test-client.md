# Task 2: MQTT Test Client Page

## Objective

Create a browser-based MQTT test client for publishing messages and subscribing to topics. Uses the `mqtt` npm package (mqtt.js) which connects via WebSocket to the EMQX broker.

## Prerequisites

Install the mqtt.js package:

```bash
cd frontend && npm install mqtt
```

If TypeScript types are missing, also install:

```bash
cd frontend && npm install -D @types/mqtt
```

(mqtt.js v5+ may include types natively — check before installing `@types/mqtt`)

## File to Create

`frontend/src/features/fleet/MqttTestClientPage.tsx`

## Design

The page has 3 sections in a 2-column layout:

**Left column (connection + publish):**
1. **Connection panel** — Broker URL, Client ID, Password, Connect/Disconnect button, connection status indicator
2. **Publish panel** — Topic input, payload textarea, QoS selector, Retain toggle, Publish button

**Right column (subscribe + messages):**
3. **Subscribe panel** — Topic filter input, Subscribe button, active subscriptions list
4. **Message log** — Scrollable list of received messages (topic, payload, timestamp)

## Implementation

```tsx
import { useCallback, useEffect, useRef, useState } from "react";
import mqtt from "mqtt";
import {
  Plug,
  Unplug,
  Send,
  Trash2,
  Plus,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ReceivedMessage {
  id: number;
  topic: string;
  payload: string;
  timestamp: Date;
  qos: number;
}

let msgCounter = 0;

export default function MqttTestClientPage({ embedded }: { embedded?: boolean }) {
  // Connection state
  const [brokerUrl, setBrokerUrl] = useState("ws://localhost:9001/mqtt");
  const [clientId, setClientId] = useState("");
  const [password, setPassword] = useState("");
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const clientRef = useRef<mqtt.MqttClient | null>(null);

  // Publish state
  const [pubTopic, setPubTopic] = useState("");
  const [pubPayload, setPubPayload] = useState('{"temperature": 22.5}');
  const [pubQos, setPubQos] = useState<0 | 1 | 2>(0);
  const [pubRetain, setPubRetain] = useState(false);

  // Subscribe state
  const [subTopic, setSubTopic] = useState("#");
  const [subscriptions, setSubscriptions] = useState<string[]>([]);

  // Messages
  const [messages, setMessages] = useState<ReceivedMessage[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clientRef.current?.end(true);
    };
  }, []);

  const handleConnect = useCallback(() => {
    if (connected || connecting) return;
    setConnecting(true);
    setConnectionError(null);

    try {
      const client = mqtt.connect(brokerUrl, {
        clientId: clientId || undefined,
        username: clientId || undefined,
        password: password || undefined,
        reconnectPeriod: 0, // Don't auto-reconnect in test mode
      });

      client.on("connect", () => {
        setConnected(true);
        setConnecting(false);
        setConnectionError(null);
      });

      client.on("error", (err) => {
        setConnectionError(err.message);
        setConnecting(false);
      });

      client.on("close", () => {
        setConnected(false);
        setConnecting(false);
      });

      client.on("message", (topic, payload, packet) => {
        const msg: ReceivedMessage = {
          id: ++msgCounter,
          topic,
          payload: payload.toString(),
          timestamp: new Date(),
          qos: packet.qos,
        };
        setMessages((prev) => [msg, ...prev].slice(0, 200));
      });

      clientRef.current = client;
    } catch (err) {
      setConnectionError(err instanceof Error ? err.message : "Connection failed");
      setConnecting(false);
    }
  }, [brokerUrl, clientId, password, connected, connecting]);

  const handleDisconnect = useCallback(() => {
    clientRef.current?.end(true);
    clientRef.current = null;
    setConnected(false);
    setSubscriptions([]);
  }, []);

  const handlePublish = useCallback(() => {
    if (!clientRef.current || !connected || !pubTopic) return;
    clientRef.current.publish(pubTopic, pubPayload, {
      qos: pubQos,
      retain: pubRetain,
    });
  }, [connected, pubTopic, pubPayload, pubQos, pubRetain]);

  const handleSubscribe = useCallback(() => {
    if (!clientRef.current || !connected || !subTopic) return;
    clientRef.current.subscribe(subTopic, { qos: 0 });
    setSubscriptions((prev) =>
      prev.includes(subTopic) ? prev : [...prev, subTopic]
    );
    setSubTopic("");
  }, [connected, subTopic]);

  const handleUnsubscribe = useCallback((topic: string) => {
    clientRef.current?.unsubscribe(topic);
    setSubscriptions((prev) => prev.filter((t) => t !== topic));
  }, []);

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader
          title="MQTT Test Client"
          description="Publish and subscribe to MQTT topics for testing"
        />
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Left column: Connection + Publish */}
        <div className="space-y-4">
          {/* Connection panel */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Connection</CardTitle>
                <Badge variant={connected ? "default" : "secondary"}>
                  {connecting ? "Connecting..." : connected ? "Connected" : "Disconnected"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="broker-url" className="text-xs">Broker URL (WebSocket)</Label>
                <Input
                  id="broker-url"
                  value={brokerUrl}
                  onChange={(e) => setBrokerUrl(e.target.value)}
                  placeholder="ws://localhost:9001/mqtt"
                  disabled={connected}
                  className="mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="client-id" className="text-xs">Client ID</Label>
                  <Input
                    id="client-id"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    placeholder="test-client"
                    disabled={connected}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="password" className="text-xs">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={connected}
                    className="mt-1"
                  />
                </div>
              </div>
              {connectionError && (
                <p className="text-xs text-destructive">{connectionError}</p>
              )}
              <div className="flex gap-2">
                {!connected ? (
                  <Button size="sm" onClick={handleConnect} disabled={connecting || !brokerUrl}>
                    <Plug className="mr-1 h-3.5 w-3.5" />
                    {connecting ? "Connecting..." : "Connect"}
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={handleDisconnect}>
                    <Unplug className="mr-1 h-3.5 w-3.5" />
                    Disconnect
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Publish panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Publish</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="pub-topic" className="text-xs">Topic</Label>
                <Input
                  id="pub-topic"
                  value={pubTopic}
                  onChange={(e) => setPubTopic(e.target.value)}
                  placeholder="tenant/TENANT_ID/device/DEVICE_ID/telemetry"
                  disabled={!connected}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="pub-payload" className="text-xs">Payload (JSON)</Label>
                <textarea
                  id="pub-payload"
                  value={pubPayload}
                  onChange={(e) => setPubPayload(e.target.value)}
                  disabled={!connected}
                  rows={3}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                />
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <Label className="text-xs">QoS</Label>
                  <Select
                    value={String(pubQos)}
                    onValueChange={(v) => setPubQos(Number(v) as 0 | 1 | 2)}
                    disabled={!connected}
                  >
                    <SelectTrigger className="w-16 h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">0</SelectItem>
                      <SelectItem value="1">1</SelectItem>
                      <SelectItem value="2">2</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <label className="flex items-center gap-1.5 text-xs">
                  <input
                    type="checkbox"
                    checked={pubRetain}
                    onChange={(e) => setPubRetain(e.target.checked)}
                    disabled={!connected}
                  />
                  Retain
                </label>
                <div className="flex-1" />
                <Button size="sm" onClick={handlePublish} disabled={!connected || !pubTopic}>
                  <Send className="mr-1 h-3.5 w-3.5" />
                  Publish
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column: Subscribe + Messages */}
        <div className="space-y-4">
          {/* Subscribe panel */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Subscribe</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={subTopic}
                  onChange={(e) => setSubTopic(e.target.value)}
                  placeholder="# (all topics)"
                  disabled={!connected}
                  onKeyDown={(e) => e.key === "Enter" && handleSubscribe()}
                />
                <Button size="sm" onClick={handleSubscribe} disabled={!connected || !subTopic}>
                  <Plus className="mr-1 h-3.5 w-3.5" />
                  Subscribe
                </Button>
              </div>
              {subscriptions.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {subscriptions.map((t) => (
                    <Badge key={t} variant="secondary" className="gap-1 pr-1">
                      <span className="font-mono text-xs">{t}</span>
                      <button
                        onClick={() => handleUnsubscribe(t)}
                        className="ml-0.5 rounded-full hover:bg-muted"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Message log */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-medium">
                Messages
                {messages.length > 0 && (
                  <span className="ml-2 text-xs text-muted-foreground font-normal">
                    ({messages.length})
                  </span>
                )}
              </CardTitle>
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setMessages([])}
                  title="Clear messages"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {messages.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-6">
                  {connected
                    ? "Subscribe to a topic to see messages"
                    : "Connect and subscribe to see messages"}
                </p>
              ) : (
                <div className="max-h-96 overflow-y-auto space-y-2">
                  {messages.map((msg) => (
                    <div key={msg.id} className="rounded-md border p-2 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-muted-foreground truncate max-w-[70%]">
                          {msg.topic}
                        </span>
                        <span className="text-muted-foreground/60 shrink-0">
                          {msg.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <pre className="overflow-x-auto bg-muted rounded p-1.5 font-mono text-xs">
                        {msg.payload}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export const Component = MqttTestClientPage;
```

## Important Notes

- **mqtt.js import:** The package is `mqtt` (not `paho-mqtt`). If import resolution fails, check that `mqtt` is in `frontend/package.json` dependencies. The import `mqtt from "mqtt"` should work with the default bundler config (Vite handles CJS → ESM). If it doesn't, try `import * as mqtt from "mqtt"`.
- **WebSocket URL:** The default `ws://localhost:9001/mqtt` works in local development where the EMQX broker's WS port is exposed. In production, this would need to go through a reverse proxy or use `wss://`.
- **Message buffer:** Capped at 200 messages to prevent memory issues.
- **No auto-reconnect:** `reconnectPeriod: 0` prevents the test client from auto-reconnecting — this is intentional for a debugging tool.
- **`embedded` prop:** Included for rendering inside the Tools hub page.

## Verification

- `npx tsc --noEmit` passes
- `npm install mqtt` completes without errors
- File created at correct path
- Connection form renders with broker URL, client ID, password fields
- Publish form has topic, payload, QoS, retain controls
- Subscribe panel shows active subscriptions as badges
- Message log displays received messages with timestamp
