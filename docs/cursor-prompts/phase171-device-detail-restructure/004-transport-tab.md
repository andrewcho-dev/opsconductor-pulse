# Task 4: Transport Tab

## Create component in `frontend/src/features/devices/` (e.g., `DeviceTransportTab.tsx`)

Consolidates DeviceConnectionPanel + DeviceCarrierPanel + DeviceConnectivityPanel into a single Transport tab.

### Component Structure

```
TransportTab
├── "Add Transport" button
├── Transport cards (one per configured transport)
│   └── TransportCard
│       ├── Header: ingestion_protocol badge + is_primary indicator
│       ├── Status badge (active/inactive/failover)
│       ├── Protocol Details section
│       │   ├── Protocol: "MQTT Direct" / "HTTP API" / "LoRaWAN" / etc.
│       │   └── Protocol Config (expandable): MQTT client_id, topic_prefix, etc.
│       ├── Connectivity Details section
│       │   ├── Physical: "Cellular" / "Ethernet" / "WiFi" / etc.
│       │   └── Connectivity Config (expandable): carrier, APN, ICCID, IMEI, etc.
│       ├── Carrier Integration link (if linked)
│       │   └── "View Carrier Integration" link → /settings/carrier
│       ├── Last Connected: timestamp
│       └── Actions: Edit, Delete
└── Empty state: "No transports configured. Add a transport to define how this device connects."
```

### Protocol/Connectivity Display

Map protocol and connectivity values to human-readable labels:

```typescript
const protocolLabels: Record<string, string> = {
  mqtt_direct: "MQTT Direct",
  http_api: "HTTP API",
  lorawan: "LoRaWAN",
  gateway_proxy: "Gateway Proxy",
  modbus_rtu: "Modbus RTU",
};

const connectivityLabels: Record<string, string> = {
  cellular: "Cellular",
  ethernet: "Ethernet",
  wifi: "WiFi",
  satellite: "Satellite",
  lora: "LoRa",
  other: "Other",
};
```

### Protocol Config Display

Show relevant fields based on protocol type:
- **MQTT**: client_id, topic_prefix, broker URL
- **HTTP**: api_key (masked), endpoint URL
- **LoRaWAN**: dev_eui, app_key (masked), join_server
- **Gateway Proxy**: parent gateway device link

### Connectivity Config Display

Show relevant fields based on connectivity type:
- **Cellular**: carrier_name, APN, ICCID, IMEI, SIM status, data usage
- **WiFi**: SSID, IP address
- **Ethernet**: IP address, MAC

### Add/Edit Transport Dialog

```
TransportDialog (shared for create/edit)
├── Ingestion Protocol selector (dropdown) — required, not editable on update
├── Physical Connectivity selector (dropdown) — optional
├── Protocol Config section (dynamic fields based on selected protocol)
│   ├── MQTT: client_id, topic_prefix
│   ├── HTTP: api_key
│   ├── LoRaWAN: dev_eui, app_key
│   └── Other: JSON editor fallback
├── Connectivity Config section (dynamic fields based on selected connectivity)
│   ├── Cellular: carrier_name, apn, sim_iccid, data_limit_mb
│   ├── WiFi: ssid
│   └── Other: JSON editor fallback
├── Carrier Integration selector (dropdown of tenant's carrier integrations)
├── Primary transport checkbox
└── Submit
```

### Data Fetching

```typescript
const { data: transports } = useQuery({
  queryKey: ["device-transports", deviceId],
  queryFn: () => listDeviceTransports(deviceId),
});
```

## Verification

1. Transport tab shows cards for each configured transport
2. Add transport → card appears
3. Edit transport → fields update
4. Delete transport with confirmation → card disappears
5. Protocol/connectivity configs display correctly for each type
