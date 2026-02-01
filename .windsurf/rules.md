# OpsConductor-Pulse – Project Rules

This repository implements OpsConductor-Pulse, an edge telemetry, health,
and signaling platform for managed devices.

## Architecture
- services/ingest_iot: device ingress, auth, validation, quarantine
- services/evaluator_iot: heartbeat tracking, state, alert generation
- services/ui_iot: read-only dashboards (no device writes)
- services/provision_api: admin + device provisioning APIs
- simulator/device_sim_iot: simulation only (never referenced as prod logic)

## Invariants (DO NOT BREAK)
- tenant_id is required on all device data paths
- no cross-tenant data access
- UI is read-only
- admin APIs require X-Admin-Key
- rejected events must NEVER affect device state
- rate limiting must fail closed

## Code Discipline
- Prefer small, explicit changes
- Do not refactor without instruction
- Never invent new tables or fields without checking existing schema
- Ask before changing auth, tenancy, or alert semantics

## Product Intent
This is a multi-tenant SaaS control plane.
Customer isolation and auditability are critical.
