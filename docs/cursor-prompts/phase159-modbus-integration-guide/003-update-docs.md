# Task 3: Update Documentation

## Files to Update

### 1. `docs/api/ingest-endpoints.md`

**What changed:** Modbus devices are now a documented use case for both MQTT and HTTP ingestion.

Add a brief section after the "MQTT Ingestion" section titled "## Industrial Protocol Ingestion (Modbus TCP)" with:
- One paragraph explaining that Modbus TCP and other industrial protocols are supported via edge gateways that translate to MQTT/HTTP
- The payload format is identical to standard device telemetry
- Link to the Modbus integration guide: `[Modbus Integration Guide](../features/modbus-integration.md)`

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `159` to the `phases` array

### 2. `docs/features/integrations.md`

**What changed:** Modbus TCP is now a documented inbound integration pathway.

In the "Overview" section, add a third capability:
- Current: "1. Alert notifications" and "2. Message routing"
- Add: "3. Industrial protocol ingestion: connect Modbus TCP and other field-bus devices via edge gateways"
- Link to: `[Modbus Integration Guide](modbus-integration.md)`

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `159` to the `phases` array

### 3. `docs/features/device-management.md`

**What changed:** Modbus devices are now a documented device type.

In the "Overview" section or "How It Works → Registry & Provisioning" section, add a note:
- Industrial devices (Modbus TCP, BACnet, OPC-UA) can be registered like any other device
- Data is ingested via edge gateways that poll the devices and publish telemetry to the platform using MQTT or HTTP
- Link to: `[Modbus Integration Guide](modbus-integration.md)`

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `159` to the `phases` array

### 4. `docs/index.md`

**What changed:** New documentation page added.

Add a link to `features/modbus-integration.md` in the Features section of the docs index.
Add a link to `features/modbus-gateway-configs.md` in the same section (or as a sub-link under the Modbus guide).

Update YAML frontmatter:
- Set `last-verified: 2026-02-19`
- Add `159` to the `phases` array (if the index has frontmatter)

## Process for Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 159 changes
3. Update the YAML frontmatter:
   - Set `last-verified: 2026-02-19`
   - Add `159` to the `phases` array
4. Verify no stale information remains
