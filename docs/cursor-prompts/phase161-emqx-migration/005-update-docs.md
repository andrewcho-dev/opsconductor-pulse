# Task 5: Update Documentation

## Files to Update

### 1. `docs/architecture/service-map.md`
- Replace Mosquitto with EMQX in the service diagram
- Note EMQX dashboard on port 18083
- Document the HTTP auth backend flow (EMQX → ui_iot internal endpoints)

### 2. `docs/services/ingest.md`
- Update broker reference from Mosquitto to EMQX
- Note that EMQX handles per-client rate limiting and tenant-scoped ACLs at broker level
- Update connection details (TLS changes if internal listener is plain TCP)

### 3. `docs/architecture/tenant-isolation.md`
- **Critical update:** Document that tenant isolation is now enforced at the broker level (not just application level)
- The read-side ACL gap is closed — EMQX ACL endpoint validates `topic_tenant == cert_tenant` for subscribes
- Update the defense-in-depth table to include EMQX ACL as Layer 1

### 4. `docs/operations/security.md`
- Document EMQX dashboard access and default credentials
- Document the internal auth endpoints and shared secret
- Note that Caddy must block `/api/v1/internal/*` from external access

### 5. `docs/services/ui-iot.md`
- Document the new `/api/v1/internal/mqtt-auth` and `/api/v1/internal/mqtt-acl` endpoints
- Note these are internal-only, called by EMQX

Update YAML frontmatter on all files: `last-verified: 2026-02-19`, add `161` to `phases` array.
