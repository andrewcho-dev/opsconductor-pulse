import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy, Check } from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className="absolute top-2 right-2"
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-green-500" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </Button>
  );
}

function CodeBlock({ code }: { code: string; language: string }) {
  return (
    <div className="relative">
      <CopyButton text={code} />
      <pre className="overflow-x-auto rounded-md bg-muted p-4 text-sm font-mono leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// NOTE: These are template snippets. The actual broker URL, topic format, and
// HTTP ingestion endpoint should match the platform's configuration.
// Check:
//   - compose/emqx/emqx.conf for MQTT ports (1883 TCP, 8883 TLS, 9001 WS)
//   - services/ui_iot/routes/devices.py for the provisioning API response fields
//   - services/ui_iot/routes/ingest.py for the HTTP telemetry endpoint
//   - Topic format: tenant/{tenant_id}/device/{device_id}/telemetry
//   - Verify ACL behavior in services/ui_iot/routes/internal.py (MQTT ACL)
const SNIPPETS = {
  python: `import paho.mqtt.client as mqtt
import json

# Replace with your device credentials from the Devices page
BROKER = "your-broker-host"
PORT = 1883
CLIENT_ID = "your-client-id"
PASSWORD = "your-device-password"
TENANT_ID = "your-tenant-id"
DEVICE_ID = "your-device-id"

client = mqtt.Client(client_id=CLIENT_ID)
client.username_pw_set(CLIENT_ID, PASSWORD)

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # Subscribe to commands
    client.subscribe(f"tenant/{TENANT_ID}/device/{DEVICE_ID}/command/#")

def on_message(client, userdata, msg):
    print(f"Received: {msg.topic} -> {msg.payload.decode()}")

client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)

# Publish telemetry
payload = json.dumps({"temperature": 22.5, "humidity": 45.2})
client.publish(
    f"tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry",
    payload
)

client.loop_forever()`,

  nodejs: `const mqtt = require("mqtt");

// Replace with your device credentials from the Devices page
const BROKER = "mqtts://your-broker-host:8883";
const CLIENT_ID = "your-client-id";
const PASSWORD = "your-device-password";
const TENANT_ID = "your-tenant-id";
const DEVICE_ID = "your-device-id";

const client = mqtt.connect(BROKER, {
  clientId: CLIENT_ID,
  username: CLIENT_ID,
  password: PASSWORD,
});

client.on("connect", () => {
  process.stdout.write("Connected\\n");

  // Subscribe to commands
  client.subscribe(\`tenant/\${TENANT_ID}/device/\${DEVICE_ID}/command/#\`);

  // Publish telemetry
  const payload = JSON.stringify({ temperature: 22.5, humidity: 45.2 });
  client.publish(
    \`tenant/\${TENANT_ID}/device/\${DEVICE_ID}/telemetry\`,
    payload
  );
});

client.on("message", (topic, message) => {
  process.stdout.write(\`Received: \${topic} -> \${message.toString()}\\n\`);
});`,

  curl: `# HTTP Telemetry Ingestion (no MQTT required)
# Check /api/v1/ingest/telemetry for the actual endpoint and auth headers

curl -X POST https://your-host/api/v1/ingest/telemetry \\
  -H "Content-Type: application/json" \\
  -H "X-Device-ID: your-device-id" \\
  -H "X-Device-Token: your-device-password" \\
  -d '{
    "temperature": 22.5,
    "humidity": 45.2,
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
  }'`,

  arduino: `#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* wifiPassword = "YOUR_WIFI_PASSWORD";

// MQTT credentials (from the Devices page)
const char* mqttServer = "your-broker-host";
const int mqttPort = 1883;
const char* clientId = "your-client-id";
const char* mqttPassword = "your-device-password";
const char* tenantId = "your-tenant-id";
const char* deviceId = "your-device-id";

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, wifiPassword);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  client.setServer(mqttServer, mqttPort);
}

void loop() {
  if (!client.connected()) {
    client.connect(clientId, clientId, mqttPassword);
  }
  client.loop();

  // Publish telemetry every 10 seconds
  StaticJsonDocument<128> doc;
  doc["temperature"] = analogRead(A0) * 0.1;
  doc["humidity"] = analogRead(A1) * 0.1;

  char payload[128];
  serializeJson(doc, payload);

  char topic[128];
  snprintf(topic, sizeof(topic),
    "tenant/%s/device/%s/telemetry", tenantId, deviceId);
  client.publish(topic, payload);

  delay(10000);
}`,
};

export default function ConnectionGuidePage({ embedded }: { embedded?: boolean }) {
  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Connection Guide" description="Connect your devices to OpsConductor Pulse" />
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">How it works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <div className="flex items-start gap-3">
            <Badge variant="outline" className="shrink-0 mt-0.5">
              1
            </Badge>
            <span>
              <strong className="text-foreground">Add a device</strong> on the{" "}
              <Link to="/devices/wizard" className="text-primary hover:underline">
                Devices page
              </Link>{" "}
              to get connection credentials (client ID + password).
            </span>
          </div>
          <div className="flex items-start gap-3">
            <Badge variant="outline" className="shrink-0 mt-0.5">
              2
            </Badge>
            <span>
              <strong className="text-foreground">Connect via MQTT</strong> using the credentials and
              code snippets below.
            </span>
          </div>
          <div className="flex items-start gap-3">
            <Badge variant="outline" className="shrink-0 mt-0.5">
              3
            </Badge>
            <span>
              <strong className="text-foreground">Publish telemetry</strong> to{" "}
              <code className="text-xs bg-muted px-1 py-0.5 rounded">
                tenant/TENANT_ID/device/DEVICE_ID/telemetry
              </code>{" "}
              as JSON.
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Connection Parameters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <span className="text-muted-foreground">MQTT Broker:</span>{" "}
              <code className="bg-muted px-1 py-0.5 rounded text-xs">mqtts://your-host:8883</code>
            </div>
            <div>
              <span className="text-muted-foreground">MQTT TLS:</span>{" "}
              <code className="bg-muted px-1 py-0.5 rounded text-xs">mqtts://your-host:8883</code>
            </div>
            <div>
              <span className="text-muted-foreground">WebSocket:</span>{" "}
              <code className="bg-muted px-1 py-0.5 rounded text-xs">wss://your-host:9001/mqtt</code>
            </div>
            <div>
              <span className="text-muted-foreground">HTTP Ingest:</span>{" "}
              <code className="bg-muted px-1 py-0.5 rounded text-xs">POST /api/v1/ingest/telemetry</code>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Replace <code>your-host</code> with your platform&apos;s hostname. Get device credentials from the
            Devices page.
          </p>
        </CardContent>
      </Card>

      <Tabs defaultValue="python">
        <TabsList>
          <TabsTrigger value="python">Python</TabsTrigger>
          <TabsTrigger value="nodejs">Node.js</TabsTrigger>
          <TabsTrigger value="curl">curl / HTTP</TabsTrigger>
          <TabsTrigger value="arduino">Arduino / ESP32</TabsTrigger>
        </TabsList>
        <TabsContent value="python" className="mt-3">
          <CodeBlock code={SNIPPETS.python} language="python" />
          <p className="mt-2 text-xs text-muted-foreground">
            Install: <code className="bg-muted px-1 py-0.5 rounded">pip install paho-mqtt</code>
          </p>
        </TabsContent>
        <TabsContent value="nodejs" className="mt-3">
          <CodeBlock code={SNIPPETS.nodejs} language="javascript" />
          <p className="mt-2 text-xs text-muted-foreground">
            Install: <code className="bg-muted px-1 py-0.5 rounded">npm install mqtt</code>
          </p>
        </TabsContent>
        <TabsContent value="curl" className="mt-3">
          <CodeBlock code={SNIPPETS.curl} language="bash" />
          <p className="mt-2 text-xs text-muted-foreground">
            No MQTT library needed — uses the HTTP telemetry ingestion endpoint.
          </p>
        </TabsContent>
        <TabsContent value="arduino" className="mt-3">
          <CodeBlock code={SNIPPETS.arduino} language="cpp" />
          <p className="mt-2 text-xs text-muted-foreground">
            Requires: <code className="bg-muted px-1 py-0.5 rounded">PubSubClient</code> and{" "}
            <code className="bg-muted px-1 py-0.5 rounded">ArduinoJson</code> libraries.
          </p>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = ConnectionGuidePage;

