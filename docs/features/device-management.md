---
last-verified: 2026-02-19
sources:
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/sensors.py
  - services/ui_iot/routes/templates.py
  - services/ui_iot/routes/customer.py
  - services/ui_iot/routes/jobs.py
  - services/ui_iot/routes/ota.py
  - services/ui_iot/routes/certificates.py
  - frontend/src/features/devices/DeviceDetailPage.tsx
  - frontend/src/features/devices/DeviceSensorsDataTab.tsx
  - frontend/src/features/devices/DeviceTransportTab.tsx
  - frontend/src/features/devices/DeviceHealthTab.tsx
  - frontend/src/features/devices/DeviceTwinCommandsTab.tsx
  - frontend/src/features/devices/DeviceSecurityTab.tsx
  - services/ui_iot/routes/operator.py
  - services/provision_api/app.py
  - services/ingest_iot/ingest.py
  - services/ui_iot/routes/ingest.py
  - frontend/src/features/templates/TemplateListPage.tsx
  - frontend/src/features/templates/TemplateDetailPage.tsx
  - frontend/src/services/api/templates.ts
phases: [166, 167, 168, 169, 170, 171, 172, 173]
---

# Device Management

> Provisioning, device registry, twin/shadow, commands, OTA, and certificates.

## Overview

Device management supports onboarding and operating a multi-tenant IoT fleet:

- Device registry and metadata management (tenant + site scoped).
- Device credentials (provision tokens and optional MQTT credentials).
- Telemetry ingestion and device last-seen/state.
- Device twin/shadow behaviors for desired/reported state.
- Commands and job orchestration across device groups.
- OTA firmware campaigns.
- X.509 certificate lifecycle management.

## How It Works

### Registry + provisioning

Devices are registered in the device registry tables. Provisioning flows:

- Admin provisioning API registers devices and issues tokens.
- Devices authenticate ingestion using provision tokens (and optionally certificates, depending on deployment).

### Templates and device instances (Phases 166-169)

The platform models device capability vs device reality:

- Templates (`device_templates`, `template_metrics`, `template_commands`, `template_slots`) describe what a device type can do.
- Instances (`device_registry`, `device_modules`, `device_sensors`, `device_transports`) describe what a specific device actually has configured.

Key behaviors:

- When a device is created with `template_id`, the system auto-creates `device_sensors` rows for all required template metrics (`template_metrics.is_required = true`).
- Template changes do not delete sensors automatically; they only add missing required sensors from the new template.
- Module assignment validates slot compatibility (slot exists in the device template; optional `compatible_templates` checks; `max_devices` slot enforcement).
- Transport configuration uses `device_transports` (replacing the legacy `device_connections` model). Legacy connection endpoints remain temporarily but are deprecated in favor of transports.

## Template Management UI (Phase 170)

The customer UI includes a dedicated template management experience:

- Template list page (`/app/templates`): filter by category/source and search by name/slug; actions include add, clone (system templates), and delete (tenant templates).
- Template detail page (`/app/templates/:templateId`): tabbed view:
  - Overview (identity + config)
  - Metrics
  - Commands
  - Slots
- System templates are read-only and show a clone banner to create a customizable tenant-owned copy.

## Device Detail UI (Phase 171)

The customer UI restructures the device detail page into a 6-tab layout to keep all instance management in one place:

- Overview: identity, map/location, plan/tier info, template badge link, notes/tags editing.
- Sensors & Data: module assignment (template slots), sensor management, telemetry charts.
- Transport: per-device transport configuration (protocol + physical connectivity) and carrier integration linking.
- Health: device health telemetry and uptime.
- Twin & Commands: desired/reported state management and command dispatch/history.
- Security: API tokens and mTLS certificates.

## Telemetry Key Normalization (Phase 172)

Telemetry is stored using *semantic* metric keys to keep charting and alerting stable across firmware versions and port assignments.

- Devices may publish raw firmware keys (e.g. `port_3_temp`).
- Assigned expansion modules can provide a `metric_key_map` (`device_modules.metric_key_map`) that translates raw keys to semantic keys (e.g. `port_3_temp` → `temperature`).
- Ingest applies this translation before writing to TimescaleDB; unmapped keys pass through unchanged.
- `device_sensors.last_value` / `last_seen_at` are updated from ingested telemetry for fast UI display.

Known limitation: historical telemetry ingested before normalization retains raw keys in storage; charting uses the requested semantic key and may show gaps for older raw-key-only data.

### Telemetry and state

Devices publish telemetry; ingestion updates device last-seen and stores telemetry. Evaluator uses telemetry/heartbeats to compute device status.

### Twin / shadow

Device twin endpoints expose:

- Current twin snapshot
- Desired state updates (optimistic concurrency via ETag/If-Match patterns)
- Delta views

### Commands and jobs

- Commands can be sent to a single device.
- Jobs can schedule/batch operations across devices/groups.

### OTA

Firmware versions and campaigns allow orchestrated updates, tracking rollout status per device.

### Certificates

Certificate endpoints manage:

- CA bundle retrieval
- Certificate upload/revocation
- Device certificate generation and rotation
- CRL retrieval

### Carrier SIM provisioning

From the device detail page, devices that are not yet linked to a carrier integration can provision a SIM directly:

- Users select a carrier integration, enter an ICCID, and optionally select a carrier plan.
- After provisioning, the device is automatically linked to the carrier integration and carrier diagnostics/usage become available.
- Operators can manage carrier integrations for any tenant from the Operator panel (`/operator/carriers`) with optional filtering by tenant/carrier.

## Database Schema

Key tables (high-level):

- `device_registry`, `device_state`
- `telemetry` hypertable
- `device_api_tokens`
- Grouping: `sites`, `device_groups` and membership tables
- Commands/jobs tables
- OTA firmware/campaign tables
- Certificates tables + CRL storage (implementation-dependent)

## API Endpoints

See: [Customer Endpoints](../api/customer-endpoints.md).

Key prefixes:

- Devices: `/api/v1/customer/devices*`
- Telemetry: `/api/v1/customer/devices/{device_id}/telemetry*`
- Twin: `/api/v1/customer/devices/{device_id}/twin*`
- Commands: `/api/v1/customer/devices/{device_id}/commands*`
- Jobs: `/api/v1/customer/jobs*`
- OTA: `/api/v1/customer/firmware*` and `/api/v1/customer/ota/*`
- Certificates: `/api/v1/customer/certificates*` and `/api/v1/customer/devices/*/certificates/*`

Provisioning API: [Provisioning Endpoints](../api/provisioning-endpoints.md).

## Frontend

Primary feature modules:

- `devices/` — device list/detail, tags, groups, wizard/import
- `ota/` — firmware versions and campaigns
- Certificates UI (feature module depends on tenant role and build)

## Configuration

Common knobs:

- Ingest behavior: `REQUIRE_TOKEN`, batch writer sizing, MQTT broker config
- Certificate paths/CA configuration in compose/ops workers

## See Also

- [Service: ingest](../services/ingest.md)
- [Service: provision-api](../services/provision-api.md)
- [Ingestion Endpoints](../api/ingest-endpoints.md)
- [Security](../operations/security.md)

