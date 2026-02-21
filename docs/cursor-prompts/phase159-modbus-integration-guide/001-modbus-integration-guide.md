# Task 1: Create Modbus TCP Integration Guide

## File to Create

`docs/features/modbus-integration.md`

## What to Do

Create a comprehensive guide for customers who need to connect Modbus TCP devices to the platform. This is documentation only — no code changes.

### YAML Frontmatter

```yaml
---
last-verified: 2026-02-19
sources:
  - services/ui_iot/routes/ingest.py
  - services/ingest_iot/ingest.py
  - docs/api/ingest-endpoints.md
phases: [159]
---
```

### Content Structure

Write the guide with the following sections:

#### 1. Overview

Explain:
- Modbus TCP is a polling protocol common in industrial automation, building management, and energy monitoring
- Modbus devices (PLCs, meters, sensors, VFDs) don't push data to the cloud — they sit on a local network and respond to read requests
- An **edge gateway** bridges the gap: it sits on the customer's LAN, polls Modbus devices on a schedule, translates register values to named metrics, and publishes telemetry to the platform via MQTT or HTTP
- The platform receives standard telemetry messages — it doesn't need to know the data originated from Modbus

Include this architecture diagram (use a code block):

```
Customer Site                              Cloud Platform
─────────────────────────────              ──────────────────

 ┌──────────┐  Modbus TCP (port 502)
 │ PLC /    │◄──────────┐
 │ Sensor   │           │
 └──────────┘           │
                   ┌────▼──────┐   MQTT (port 8883)   ┌──────────┐
 ┌──────────┐      │   Edge    │──────────────────────▶│ Platform │
 │ Meter    │◄─────│  Gateway  │   or HTTP (port 443)  │ Broker   │
 └──────────┘      └───────────┘                       └──────────┘

 ┌──────────┐           ▲
 │ VFD      │◄──────────┘
 └──────────┘  Modbus TCP
```

#### 2. Prerequisites

- Devices registered in the platform with `device_id` and `provision_token`
- Network access from the gateway to Modbus devices (port 502, same LAN/VLAN)
- Network access from the gateway to the platform (MQTT port 8883 or HTTPS port 443)
- Gateway hardware or software (see Recommended Gateways section)

#### 3. How It Works

Step-by-step flow:

1. **Register devices** in the platform (via UI or provisioning API) — each Modbus device gets a `device_id` and `provision_token`
2. **Install an edge gateway** on the customer's local network (Raspberry Pi, industrial PC, Docker host, or hardware gateway)
3. **Configure the register map** — define which Modbus registers correspond to which metric names (e.g., holding register 40001 → `temperature_c`, input register 30005 → `power_kw`)
4. **Configure the MQTT/HTTP connection** — point the gateway at the platform broker with the device's credentials
5. **Data flows automatically** — gateway polls registers on schedule, translates to JSON, publishes to platform

#### 4. Register Mapping

Explain the four Modbus register types:
- **Coils** (0xxxx) — read/write boolean, function codes 1/5/15
- **Discrete Inputs** (1xxxx) — read-only boolean, function code 2
- **Input Registers** (3xxxx) — read-only 16-bit, function code 4
- **Holding Registers** (4xxxx) — read/write 16-bit, function code 3

Explain data types:
- Single register (16-bit): `uint16`, `int16`
- Double register (32-bit): `uint32`, `int32`, `float32` — byte order matters (big-endian vs little-endian, word swap)
- Quad register (64-bit): `uint64`, `float64`

Explain scaling:
- Raw register value × scale factor = engineering units
- Example: register 40001 returns `2350`, scale `0.01` → `23.50°C`

Provide a reference table format:

```
| Register | Type     | Data Type | Scale | Metric Name    | Unit |
|----------|----------|-----------|-------|----------------|------|
| 40001    | holding  | int16     | 0.01  | temperature_c  | °C   |
| 40003    | holding  | uint32    | 1.0   | energy_kwh     | kWh  |
| 30001    | input    | uint16    | 0.1   | voltage_v      | V    |
| 30002    | input    | uint16    | 0.01  | current_a      | A    |
```

Note: register maps are device-specific. Customers must consult their device's Modbus register documentation.

#### 5. MQTT Topic & Payload Format

The gateway must publish to the platform's standard topic:

```
tenant/{tenant_id}/device/{device_id}/telemetry
```

With standard payload:

```json
{
  "site_id": "site-1",
  "provision_token": "tok-xxxxxxxx",
  "ts": "2026-02-19T14:30:00Z",
  "seq": 42,
  "metrics": {
    "temperature_c": 23.5,
    "humidity_pct": 65.2,
    "power_kw": 12.8,
    "compressor_running": true
  }
}
```

For HTTP ingestion, POST to:

```
POST /ingest/v1/tenant/{tenant_id}/device/{device_id}/telemetry
X-Provision-Token: tok-xxxxxxxx
Content-Type: application/json

{
  "site_id": "site-1",
  "ts": "2026-02-19T14:30:00Z",
  "metrics": {
    "temperature_c": 23.5
  }
}
```

Reference: [Ingestion Endpoints](../api/ingest-endpoints.md)

#### 6. Recommended Gateways

Document three options:

**Neuron (Recommended for production)**
- Open source, by EMQ (same team as EMQX)
- Native EMQX integration
- Supports 80+ industrial protocols (Modbus TCP/RTU, OPC-UA, BACnet, Siemens S7, EtherNet/IP)
- REST API for configuration
- Runs on ARM (Raspberry Pi) and x86
- Docker image available
- Link: https://neugates.io/

**Telegraf (Quick start)**
- Open source, by InfluxData
- Modbus input plugin + MQTT output plugin
- Config file driven (TOML)
- Lightweight, single binary
- Good for simple register polling without visual configuration
- Link: https://www.influxdata.com/time-series-platform/telegraf/

**Node-RED (Visual / prototyping)**
- Open source, by OpenJS Foundation
- Visual flow editor in browser
- Modbus nodes available via npm (`node-red-contrib-modbus`)
- MQTT output node built-in
- Good for prototyping and non-standard transformations
- Heavier resource usage than Telegraf
- Link: https://nodered.org/

**Hardware gateways (no software to manage)**
- Teltonika TRB-series (~$150-300)
- Advantech ECU-series (~$200-500)
- Moxa ioThinx (~$300-600)
- Most support Modbus TCP + MQTT natively

See [Gateway Example Configurations](modbus-gateway-configs.md) for ready-to-use configs.

#### 7. Polling Best Practices

- **Poll interval:** Match to the physical process. Temperature → 30-60s. Power metering → 1-5s. Status bits → 5-10s.
- **Batch registers:** Read contiguous register ranges in one request (e.g., registers 40001-40010) rather than individual reads. Reduces network overhead and device load.
- **Stagger devices:** If polling 10+ devices, stagger start times to avoid thundering herd.
- **Timeout handling:** Set Modbus read timeout to 3-5s. If a device is unreachable, log locally and skip — don't block other devices.
- **Local buffering:** Configure the gateway to buffer data locally (SQLite, file) if the internet connection drops. Replay buffered data when connectivity returns.

#### 8. Troubleshooting

Common issues:
- **No data appearing:** Check that `tenant_id`, `device_id`, and `provision_token` match the platform device registry. Check MQTT connection to broker (TLS certificate, port 8883).
- **Wrong values:** Check byte order (big-endian vs little-endian). Modbus register byte order varies by manufacturer. Try swapping word order for 32-bit values.
- **Intermittent timeouts:** Reduce concurrent register reads. Some devices can only handle 1-2 concurrent Modbus TCP connections.
- **Register offset confusion:** Some tools use 0-based addressing (register 0 = 40001), others use 1-based. Verify with the device documentation.
- **Scaling wrong:** Confirm scale factor and data type (signed vs unsigned, 16-bit vs 32-bit).

#### 9. Security Considerations

- Modbus TCP has **no authentication or encryption**. It must only run on isolated, trusted networks (VLAN, firewall).
- **Never expose Modbus port 502 to the internet.**
- The edge gateway should be the only bridge between the Modbus network and the internet.
- Use MQTT with TLS (port 8883) or HTTPS for all gateway-to-platform communication.
- Device provision tokens should be stored securely on the gateway (environment variables or encrypted config, not plain text in shared configs).

#### 10. See Also

- [Ingestion Endpoints](../api/ingest-endpoints.md)
- [Device Management](device-management.md)
- [Gateway Example Configurations](modbus-gateway-configs.md)
- [Integrations](integrations.md)

## Important Notes

- This is a **documentation-only** task — no platform code changes
- The guide should be written for a customer audience (clear, practical, not overly technical about platform internals)
- Include enough Modbus background that a customer who hasn't used Modbus before can understand the register mapping concept
- The example configs are in a separate file (Task 2) — this guide links to them
