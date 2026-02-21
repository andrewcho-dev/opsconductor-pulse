# Task 2: Gateway Example Configurations

## File to Create

`docs/features/modbus-gateway-configs.md`

## What to Do

Create ready-to-use example configurations for the three recommended gateways. Customers should be able to copy-paste and adapt these with minimal changes.

### YAML Frontmatter

```yaml
---
last-verified: 2026-02-19
sources:
  - docs/api/ingest-endpoints.md
phases: [159]
---
```

### Content Structure

#### 1. Overview

Brief intro: these are starter configurations for connecting Modbus TCP devices to the platform. Each example polls a hypothetical HVAC controller with:
- Holding register 40001: temperature (int16, scale 0.01, °C)
- Holding register 40003: humidity (uint16, scale 0.1, %)
- Holding register 40005: power consumption (uint32, scale 1.0, W)
- Coil 00001: compressor running (boolean)

Customers should replace:
- `{BROKER_HOST}` → platform MQTT broker hostname
- `{TENANT_ID}` → their tenant ID
- `{DEVICE_ID}` → the device ID registered in the platform
- `{PROVISION_TOKEN}` → the device's provision token
- `{MODBUS_HOST}` → the Modbus device's IP address
- Register addresses and metric names → their actual device registers

---

#### 2. Telegraf Configuration

Provide a complete `telegraf.conf`:

```toml
# Telegraf Configuration for Modbus TCP → Platform MQTT
# =====================================================

# Global settings
[agent]
  interval = "30s"           # Poll every 30 seconds
  flush_interval = "10s"
  hostname = "{DEVICE_ID}"

# ─── INPUT: Modbus TCP ───────────────────────────────

[[inputs.modbus]]
  name = "hvac_controller"
  slave_id = 1
  timeout = "3s"
  controller = "tcp://{MODBUS_HOST}:502"

  # Holding registers (function code 3)
  holding_registers = [
    { name = "temperature_c",  byte_order = "AB",   data_type = "INT16",  scale = 0.01, address = [0] },
    { name = "humidity_pct",   byte_order = "AB",   data_type = "UINT16", scale = 0.1,  address = [2] },
    { name = "power_w",        byte_order = "ABCD", data_type = "UINT32", scale = 1.0,  address = [4] },
  ]

  # Coils (function code 1)
  coils = [
    { name = "compressor_running", address = [0] },
  ]

  # Tag the output with device identity
  [inputs.modbus.tags]
    tenant_id = "{TENANT_ID}"
    device_id = "{DEVICE_ID}"
    site_id   = "site-1"

# ─── OUTPUT: MQTT to Platform ────────────────────────

[[outputs.mqtt]]
  servers = ["ssl://{BROKER_HOST}:8883"]
  topic = "tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry"

  # TLS
  tls_ca = "/etc/telegraf/ca.crt"
  # insecure_skip_verify = true  # Only for testing

  # Auth
  username = "{DEVICE_ID}"
  password = "{PROVISION_TOKEN}"

  # Data format — JSON matching platform payload spec
  data_format = "json"
  json_timestamp_units = "1ms"

  # Add required fields to payload
  [outputs.mqtt.tagpass]
    tenant_id = ["{TENANT_ID}"]

# ─── PROCESSOR: Reshape to platform format ───────────

[[processors.rename]]
  # Telegraf wraps metrics in a "fields" object by default.
  # The platform expects a flat "metrics" object.
  # Use the Execd processor or a custom script if deeper
  # reshaping is needed. For basic setups, Telegraf's
  # JSON output with the modbus field names works directly
  # if the ingest endpoint accepts the format.
```

**Note to the doc author:** Telegraf's default JSON output shape may not exactly match the platform's expected payload format (`{"site_id": "...", "metrics": {...}}`). If the shapes don't align, add a note that customers may need an `[[processors.execd]]` or `[[processors.starlark]]` processor to reshape the payload. Alternatively, recommend using the HTTP output plugin with the batch endpoint, which may be more flexible:

```toml
[[outputs.http]]
  url = "https://{BROKER_HOST}/ingest/v1/tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry"
  method = "POST"
  data_format = "json"
  [outputs.http.headers]
    Content-Type = "application/json"
    X-Provision-Token = "{PROVISION_TOKEN}"
```

---

#### 3. Node-RED Flow

Provide a JSON flow that can be imported into Node-RED:

```json
[
  {
    "id": "modbus-read",
    "type": "modbus-read",
    "name": "Read HVAC Registers",
    "topic": "",
    "showStatusActivities": true,
    "showErrors": true,
    "unitid": "1",
    "dataType": "HoldingRegister",
    "adr": "0",
    "quantity": "6",
    "rate": "30",
    "rateUnit": "s",
    "delayOnStart": false,
    "startDelayTime": "",
    "server": "modbus-server",
    "useIOFile": false,
    "ioFile": "",
    "useIOForPayload": false,
    "wires": [["transform"]]
  },
  {
    "id": "modbus-server",
    "type": "modbus-client",
    "name": "Modbus Device",
    "clienttype": "tcp",
    "bufferCommands": true,
    "stateLogEnabled": false,
    "tcpHost": "{MODBUS_HOST}",
    "tcpPort": "502",
    "tcpType": "DEFAULT",
    "serialPort": "",
    "serialType": "RTU-BUFFERED",
    "serialBaudrate": "9600",
    "serialDatabits": "8",
    "serialStopbits": "1",
    "serialParity": "none",
    "serialConnectionDelay": "100",
    "unit_id": "1",
    "commandDelay": "1",
    "clientTimeout": "3000",
    "reconnectOnTimeout": true,
    "reconnectTimeout": "5000"
  },
  {
    "id": "transform",
    "type": "function",
    "name": "Transform to Platform Format",
    "func": "// Raw registers from Modbus read\nvar regs = msg.payload;\n\n// Parse register values with scaling\nvar temperature = (regs[0] > 32767 ? regs[0] - 65536 : regs[0]) * 0.01;\nvar humidity = regs[2] * 0.1;\nvar power = (regs[4] * 65536 + regs[5]);\n\nmsg.topic = 'tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry';\nmsg.payload = {\n    site_id: 'site-1',\n    provision_token: '{PROVISION_TOKEN}',\n    ts: new Date().toISOString(),\n    metrics: {\n        temperature_c: Math.round(temperature * 100) / 100,\n        humidity_pct: Math.round(humidity * 10) / 10,\n        power_w: power,\n    }\n};\n\nreturn msg;",
    "outputs": 1,
    "wires": [["mqtt-out"]]
  },
  {
    "id": "mqtt-out",
    "type": "mqtt out",
    "name": "Publish to Platform",
    "topic": "",
    "qos": "1",
    "retain": "false",
    "broker": "mqtt-broker",
    "wires": []
  },
  {
    "id": "mqtt-broker",
    "type": "mqtt-broker",
    "name": "Platform Broker",
    "broker": "{BROKER_HOST}",
    "port": "8883",
    "tls": true,
    "clientid": "{DEVICE_ID}",
    "usetls": true,
    "protocolVersion": "4",
    "keepalive": "60",
    "cleansession": true,
    "credentials": {
      "user": "{DEVICE_ID}",
      "password": "{PROVISION_TOKEN}"
    }
  }
]
```

**Installation note:**
```bash
# Install the Modbus nodes first
cd ~/.node-red
npm install node-red-contrib-modbus
# Restart Node-RED, then import the flow above
```

---

#### 4. Neuron Configuration

Neuron is configured via its REST API or web dashboard (default port 7000). Provide the steps:

**Step 1: Run Neuron**
```bash
docker run -d --name neuron \
  -p 7000:7000 \
  -p 7001:7001 \
  --restart unless-stopped \
  emqx/neuron:latest
```

**Step 2: Create a Modbus TCP southbound node**

```bash
# Create a Modbus TCP driver node
curl -s -X POST http://localhost:7000/api/v2/node \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hvac-controller",
    "plugin": "Modbus TCP",
    "params": {
      "host": "{MODBUS_HOST}",
      "port": 502,
      "timeout": 3000,
      "connection_mode": 0
    }
  }'
```

**Step 3: Create a group with tags (register mappings)**

```bash
# Create a polling group (30s interval)
curl -s -X POST http://localhost:7000/api/v2/group \
  -H "Content-Type: application/json" \
  -d '{
    "node": "hvac-controller",
    "group": "telemetry",
    "interval": 30000
  }'

# Add tags (register-to-metric mappings)
curl -s -X POST http://localhost:7000/api/v2/tags \
  -H "Content-Type: application/json" \
  -d '{
    "node": "hvac-controller",
    "group": "telemetry",
    "tags": [
      {"name": "temperature_c", "address": "1!40001", "attribute": 1, "type": 5, "precision": 2, "description": "Temperature in Celsius"},
      {"name": "humidity_pct",  "address": "1!40003", "attribute": 1, "type": 4, "precision": 1, "description": "Relative humidity %"},
      {"name": "power_w",      "address": "1!40005", "attribute": 1, "type": 8, "description": "Power consumption watts"},
      {"name": "compressor_running", "address": "1!00001", "attribute": 1, "type": 0, "description": "Compressor status"}
    ]
  }'
```

**Step 4: Create an MQTT northbound node to the platform**

```bash
# Create MQTT output node
curl -s -X POST http://localhost:7000/api/v2/node \
  -H "Content-Type: application/json" \
  -d '{
    "name": "platform-mqtt",
    "plugin": "MQTT",
    "params": {
      "client-id": "{DEVICE_ID}",
      "host": "{BROKER_HOST}",
      "port": 8883,
      "ssl": true,
      "username": "{DEVICE_ID}",
      "password": "{PROVISION_TOKEN}",
      "topic": "tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry",
      "ca": "/etc/neuron/ca.crt"
    }
  }'

# Subscribe the MQTT node to the Modbus group
curl -s -X POST http://localhost:7000/api/v2/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "app": "platform-mqtt",
    "driver": "hvac-controller",
    "group": "telemetry"
  }'
```

**Note:** Neuron's MQTT plugin may format the payload differently than the platform expects. If so, document the required payload transformation. Neuron supports data processing pipelines for reshaping output. Alternatively, use EMQX rule engine to transform the Neuron payload into the platform's expected format — this is the native integration path.

**Note about Neuron API versions:** Verify the exact API paths and payload format against the version of Neuron being used. The REST API has evolved between versions. The Neuron web dashboard (port 7000) provides a visual alternative to all the curl commands above.

---

#### 5. Docker Compose Example

Provide a minimal docker-compose snippet customers can add to their edge gateway:

```yaml
# Edge gateway docker-compose.yml
# Add to your existing docker-compose or run standalone

version: "3.8"

services:
  neuron:
    image: emqx/neuron:latest
    container_name: modbus-gateway
    ports:
      - "7000:7000"   # Neuron dashboard
    volumes:
      - neuron-data:/opt/neuron/persistence
      - ./certs/ca.crt:/etc/neuron/ca.crt:ro
    restart: unless-stopped

volumes:
  neuron-data:
```

Or for Telegraf:

```yaml
services:
  telegraf:
    image: telegraf:latest
    container_name: modbus-gateway
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - ./certs/ca.crt:/etc/telegraf/ca.crt:ro
    restart: unless-stopped
```

---

#### 6. Verifying Data Flow

Step-by-step verification:

1. **Check gateway connectivity to Modbus device:**
   ```bash
   # Using mbpoll (apt install mbpoll)
   mbpoll -a 1 -r 40001 -c 2 -t 3 {MODBUS_HOST}
   ```

2. **Check gateway MQTT connectivity:**
   ```bash
   # Using mosquitto_pub (test publish)
   mosquitto_pub -h {BROKER_HOST} -p 8883 \
     --cafile ca.crt \
     -u "{DEVICE_ID}" -P "{PROVISION_TOKEN}" \
     -t "tenant/{TENANT_ID}/device/{DEVICE_ID}/telemetry" \
     -m '{"site_id":"site-1","metrics":{"test":1}}'
   ```

3. **Check data in platform:**
   - Navigate to the device detail page in the platform UI
   - Telemetry tab should show the metric names from the register map
   - If no data appears, check the quarantine log (operator view) for rejection reasons

---

#### 7. See Also

- [Modbus Integration Guide](modbus-integration.md) — overview and concepts
- [Ingestion Endpoints](../api/ingest-endpoints.md) — HTTP and MQTT payload specs
- [Device Management](device-management.md) — registering devices

## Important Notes

- All gateway configs are **examples** — customers must adapt register addresses, metric names, scaling, and credentials for their specific devices
- The Neuron API examples should be verified against the current Neuron release before publishing — API endpoints may have changed between versions
- Telegraf's JSON output format may need a processor to match the platform's exact payload spec — flag this clearly in the doc
- Include a warning that Modbus TCP has no security — gateway must be on a trusted network
