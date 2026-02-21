# Task 6: Update Documentation

## Files to Update

### 1. `docs/architecture/service-map.md`
- Add NATS JetStream to the service diagram
- Show message flow: EMQX → NATS → Ingest Workers → PostgreSQL
- Show route delivery: Ingest → NATS ROUTES → Route Delivery Workers → Webhooks/MQTT
- Document the new `route-delivery` service

### 2. `docs/services/ingest.md`
- **Major rewrite:** Document the NATS consumer architecture
- Remove MQTT subscription details
- Document NATS streams (TELEMETRY, SHADOW, COMMANDS)
- Document consumer groups and horizontal scaling
- Update env vars (remove MQTT_*, add NATS_URL)
- Document the unified pipeline (both MQTT and HTTP data flows through NATS)
- Document graceful shutdown sequence

### 3. `docs/api/ingest-endpoints.md`
- Update to reflect that HTTP ingest now publishes to NATS
- Note that `202 Accepted` means "published to queue" not "written to DB"
- Document that validation happens asynchronously
- Note quarantine reasons are still the same

### 4. `docs/features/integrations.md`
- Document that message route delivery is now via dedicated service
- Document retry semantics (3 attempts via NATS max_deliver)
- Note DLQ behavior on final failure

### 5. Create `docs/services/nats.md`
- New doc for NATS JetStream configuration
- Document streams, consumers, retention policies
- Document monitoring (port 8222)
- Document scaling (adding cluster nodes)

### 6. Create `docs/services/route-delivery.md`
- New doc for the route delivery service
- Document configuration, env vars
- Document delivery types (webhook, MQTT republish)
- Document retry and DLQ behavior

Update YAML frontmatter on all files: `last-verified: 2026-02-19`, add `162` to `phases` array.
