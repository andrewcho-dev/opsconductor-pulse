# Task 4: Update Documentation

## Files to Update

### 1. `docs/services/ingest.md`

Major update to document:
- metric_key_map normalization step in the telemetry processing pipeline
- MetricKeyMapCache: configuration (TTL, max size), invalidation
- Normalization happens before batch write — stored telemetry uses semantic keys
- Unmapped keys pass through unchanged
- New Prometheus metrics: `ingest_metric_keys_normalized_total`, cache hit/miss counters
- Both NATS ingest and HTTP ingest apply the same normalization

### 2. `docs/architecture/overview.md`

Update the data flow diagram to show the normalization step:
```
EMQX → NATS JetStream → Ingest Worker → [Normalize Keys] → Batch Write → TimescaleDB
HTTP API → NATS JetStream → Ingest Worker → [Normalize Keys] → Batch Write → TimescaleDB
```

### 3. `docs/features/device-management.md`

Add section on telemetry normalization:
- How metric_key_map works (raw firmware keys → semantic names)
- Configuration via module assignment UI
- Impact on telemetry charts and exports
- Legacy data limitation (pre-normalization data retains raw keys)

### 4. `docs/api/customer-endpoints.md`

Document:
- New `GET /devices/{device_id}/telemetry/metrics` endpoint
- Updated telemetry query response format (includes unit, range metadata)

### For Each File

1. Read the current content
2. Update the relevant sections to reflect Phase 172 changes
3. Update the YAML frontmatter:
   - Set `last-verified` to `2026-02-19`
   - Add `172` to the `phases` array
   - Add `services/ingest_iot/ingest.py` to `sources`
4. Verify no stale information remains
