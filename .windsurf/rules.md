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
- When providing file changes, ALWAYS output either:
  (A) a 'nano <path>' edit command plus full file content, OR
  (B) a 'cat > <path> <<EOF ... EOF' heredoc command.
  Never output pseudo edit commands like 'edit --file_path ...'.

## Product Intent
This is a multi-tenant SaaS control plane.
Customer isolation and auditability are critical.

## Tenant Context Contract (ENFORCE)
- Tenant identity MUST come only from authenticated session context (JWT/session), never from URL/query/body.
- All customer-plane queries MUST be tenant-scoped and MUST NOT query by device_id alone.
- Canonical key is (tenant_id, device_id); treat device_id as non-unique globally.
- Database RLS is the target enforcement mechanism; code changes must preserve ability to SET LOCAL app.tenant_id.
- Operator/admin cross-tenant access must be explicit, isolated (separate pool/role), and audited.
