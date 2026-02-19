---
last-verified: 2026-02-19
sources:
  - services/ui_iot/routes/devices.py
  - services/ui_iot/routes/customer.py
  - services/ui_iot/routes/jobs.py
  - services/ui_iot/routes/ota.py
  - services/ui_iot/routes/certificates.py
  - frontend/src/features/devices/DeviceCarrierPanel.tsx
  - services/ui_iot/routes/operator.py
  - services/provision_api/app.py
  - services/ingest_iot/ingest.py
phases: [37, 48, 52, 66, 74, 76, 107, 108, 109, 125, 131, 142, 157, 158]
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

