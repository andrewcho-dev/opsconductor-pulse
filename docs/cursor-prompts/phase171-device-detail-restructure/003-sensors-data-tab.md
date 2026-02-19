# Task 3: Sensors & Data Tab

## Create component in `frontend/src/features/devices/` (e.g., `DeviceSensorsDataTab.tsx`)

This is the most complex tab — it combines module assignment, sensor management, and telemetry charts.

### Component Structure

```
SensorsDataTab
├── Module Assignment Section (if device has template with slots)
│   ├── Section header: "Expansion Modules"
│   ├── For each slot from template:
│   │   ├── Slot card showing: slot_key, display_name, interface_type badge
│   │   ├── Assigned modules list (from device_modules for this slot)
│   │   │   ├── Module card: label, template name, status badge, metric_key_map summary
│   │   │   └── Edit/Remove buttons
│   │   ├── Capacity indicator: "{count}/{max_devices} assigned"
│   │   └── "Assign Module" button (if capacity available)
│   └── Empty state if no template or no slots
│
├── Active Sensors Table
│   ├── Section header: "Sensors" + "Add Sensor" button
│   ├── DataTable columns:
│   │   ├── Metric Key
│   │   ├── Display Name
│   │   ├── Source badge (required/optional/unmodeled)
│   │   ├── Module (link to module label, or "Built-in")
│   │   ├── Unit
│   │   ├── Last Value
│   │   ├── Last Seen
│   │   ├── Status badge
│   │   └── Actions (Edit, Deactivate/Delete)
│   └── Filters: status, source
│
└── Telemetry Charts
    ├── Reuse TelemetryChartsSection component
    ├── Time range selector (1h, 6h, 24h, 7d, 30d)
    └── Charts for each active sensor with metric_key
```

### Module Assignment Dialog

When "Assign Module" is clicked:

```
AssignModuleDialog
├── Module Template selector
│   ├── If slot has compatible_templates: show only those templates
│   ├── Otherwise: show all expansion_module templates visible to tenant
│   └── Fetch from listTemplates({ category: "expansion_module" })
├── Label input (required)
├── Bus Address input (if slot interface_type supports it: rs485, i2c, 1-wire, fsk, ble, lora)
│   └── Show helper text based on interface: "1-Wire ROM address", "Modbus slave ID", etc.
├── Serial Number input (optional)
├── Metric Key Map editor
│   ├── Show as key-value pairs
│   ├── For each metric in the selected module template:
│   │   ├── Semantic key (from template): read-only
│   │   └── Raw firmware key: editable input
│   ├── Example: temperature → port_3_temp
│   └── If no module template selected, show free-form key-value editor
└── Submit → createDeviceModule()
```

### Data Fetching

```typescript
// Modules
const { data: modules } = useQuery({
  queryKey: ["device-modules", deviceId],
  queryFn: () => listDeviceModules(deviceId),
});

// Sensors
const { data: sensors } = useQuery({
  queryKey: ["device-sensors", deviceId],
  queryFn: () => listDeviceSensors(deviceId),
});

// Template slots (for module assignment UI)
const { data: template } = useQuery({
  queryKey: ["templates", templateId],
  queryFn: () => getTemplate(templateId!),
  enabled: !!templateId,
});
```

### Sensor "Add" Dialog

```
AddSensorDialog
├── Source selector: "From Template" or "Custom"
├── If "From Template":
│   ├── Show template_metrics not yet created as device_sensors
│   ├── Select metric → auto-fill fields from template_metric
│   └── Optionally link to a module
├── If "Custom":
│   ├── metric_key input
│   ├── display_name input
│   ├── unit, min_range, max_range, precision_digits
└── Submit → createDeviceSensor()
```

### Telemetry Charts

Reuse the existing `TelemetryChartsSection` component but feed it the `device_sensors` metric keys instead of raw telemetry keys. The charts section queries `fetchTelemetryHistory(deviceId, metricKey, range)` for each active sensor.

## Verification

1. If device has a template with slots, module assignment section appears
2. Assign a module to a slot → module appears in list, required sensors auto-created
3. Sensors table shows all sensors with correct source badges
4. Add a custom sensor → appears in table
5. Telemetry charts render for active sensors
6. Cannot delete a required sensor
