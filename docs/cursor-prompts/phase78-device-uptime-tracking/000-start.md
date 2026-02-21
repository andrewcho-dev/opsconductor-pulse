# Phase 78 — Device Uptime / Availability Tracking

## Overview
Track each device's online/offline status over time and expose uptime percentage metrics. Uptime is derived from the existing telemetry gap detection: a device is "online" when telemetry is received within its expected gap threshold, "offline" when a NO_TELEMETRY alert is open. Expose a per-device uptime endpoint and add an uptime widget to the fleet dashboard.

## Execution Order
1. 001-backend.md — GET /customer/devices/{id}/uptime endpoint
2. 002-backend-fleet.md — GET /customer/fleet/uptime-summary
3. 003-frontend.md — UptimeBar component + DeviceUptimePanel
4. 004-frontend-fleet.md — UptimeSummaryWidget in fleet dashboard
5. 005-unit-tests.md — 6 unit tests
6. 006-verify.md — checklist
