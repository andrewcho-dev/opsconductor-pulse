# Task 3: Update Tenant Isolation Doc

## File to Modify

- `docs/architecture/tenant-isolation.md`

## What to Do

The current tenant isolation doc describes Mosquitto ACLs (coarse wildcards) and application-layer validation in ingest_iot. After Phase 161 (EMQX migration), tenant isolation has significantly improved. Update the doc to reflect the new EMQX-based enforcement model and NATS subject-level scoping.

### Changes Required

#### 1. Read the current content first

Read `docs/architecture/tenant-isolation.md` to understand the existing structure.

#### 2. Update MQTT Broker Isolation section

Replace Mosquitto ACL description with EMQX HTTP auth backend:

**Before (Mosquitto):**
- Coarse wildcard ACLs allowing `pattern readwrite tenant/%u/device/#`
- No per-device topic enforcement at broker level
- Application-layer validation in ingest_iot as the real isolation boundary

**After (EMQX):**
- HTTP authentication backend calls `ui_iot /api/v1/internal/mqtt-auth`
- Per-device authentication: device must present valid credentials (client_id + username + password or mTLS cert)
- Per-topic ACL: auth backend returns allowed topics for each device — only `tenant/{tenant_id}/device/{device_id}/#`
- **Read-side isolation fixed**: devices can no longer subscribe to other tenants' shadow/command topics (was a gap with Mosquitto)
- Broker-level rate limiting per client prevents resource abuse
- Failed auth attempts logged and visible in Prometheus metrics (`emqx_client_auth_anonymous` should be 0)

#### 3. Add NATS Subject Scoping section

New section describing how NATS subjects enforce tenant boundaries:

- All NATS subjects include `tenant_id`: `telemetry.{tenant_id}.{device_id}`
- Consumer filters can scope to specific tenants if needed
- NATS authorization can restrict per-service access to specific subjects (future: NATS accounts per tenant at scale)
- The EMQX → NATS bridge preserves tenant_id in the subject mapping

#### 4. Update Application-Layer Validation section

The 6-layer validation in ingest_iot remains but now operates on NATS messages:
1. Topic parsing extracts tenant_id and device_id from NATS subject
2. Auth cache validates device belongs to claimed tenant
3. Site-scope enforcement
4. Rate limiting (per-device + per-tenant)
5. Payload validation
6. Quarantine for rejected messages

Note: With EMQX's HTTP auth backend, layers 1–3 are now also enforced at the broker level, providing defense-in-depth.

#### 5. Update Database Isolation section

No changes to RLS or database isolation model, but note:
- `operator_connection()` bypass pattern for operator endpoints (unchanged)
- All new services (route_delivery) use tenant-scoped NATS subjects, not RLS for isolation

#### 6. Update YAML frontmatter

```yaml
---
last-verified: 2026-02-19
sources:
  - services/ingest_iot/ingest.py
  - compose/emqx/emqx.conf
  - compose/nats/nats-server.conf
  - services/ui_iot/routes/internal.py
phases: [<existing phases>, 161, 162, 165]
---
```
