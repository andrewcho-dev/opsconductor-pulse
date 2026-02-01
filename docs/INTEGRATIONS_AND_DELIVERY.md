# Alert Integrations and Delivery Design

## Alert Transcoding

Alert transcoding converts fleet_alert records into tenant-configurable output formats. Each tenant defines their integration destinations, and the system transforms alerts into the appropriate protocol and payload format for delivery.

## Customer-Configurable Destinations

### Webhook
HTTP POST with JSON payload. Supports custom headers, retry logic, and timeout configuration.

### SNMP Trap
SNMPv2c trap delivery to configured managers. Maps alert fields to OID varbinds.

### Email (Optional)
SMTP delivery for critical alerts. Template-based subject and body formatting.

## Proposed Tables (Tenant-Scoped)

### integrations
- tenant_id, integration_id, name, type (webhook/snmp/email)
- config (JSONB: URLs, credentials, templates)
- enabled, created_at, updated_at

### integration_routes
- tenant_id, route_id, integration_id
- filter_conditions (JSONB: alert_type, severity, device patterns)
- enabled, priority

### delivery_jobs
- tenant_id, job_id, alert_id, route_id
- status (pending/processing/completed/failed)
- created_at, scheduled_at, completed_at

### delivery_attempts
- tenant_id, attempt_id, job_id, attempt_num
- status, response_code, response_body, error_message
- created_at

## Delivery Pipeline Design

```
fleet_alert → route_match → delivery_job → delivery_attempt
    ↓              ↓              ↓              ↓
filter check   priority sort   queue job    send/retry
    ↓              ↓              ↓              ↓
skip if no     select best   background   success/failure
match          route          worker        retry/backoff
```

### Retry Logic
- Exponential backoff: 30s, 2m, 8m, 30m, 2h
- Max attempts: 5 per job
- Dead-letter after max attempts

## Tenancy and Security Requirements

### Tenant Isolation Rules
- All tables scoped by tenant_id
- RLS policies enforce tenant boundaries
- Cross-tenant data access prohibited by database constraints

### Secrets Storage Model
- Integration credentials stored as encrypted blobs
- Per-tenant encryption keys (future: external vault)
- Plaintext secrets never persisted

### Rate Limits and Caps
- Per-tenant concurrency limits (default: 10 concurrent jobs)
- Per-integration rate limits (webhook: 100/minute)
- Global system rate limits to prevent abuse

## Example Payload Formats

### Webhook JSON
```json
{
  "alert_id": "12345",
  "tenant_id": "customer-abc",
  "device_id": "sensor-001",
  "alert_type": "NO_HEARTBEAT",
  "severity": 4,
  "summary": "lab-1: sensor-001 heartbeat missing/stale",
  "created_at": "2024-01-01T12:00:00Z",
  "details": {
    "last_heartbeat_at": "2024-01-01T11:25:00Z"
  }
}
```

### SNMP Varbind Mapping Concept
- .1.3.6.1.4.1.XXX.1.1.0 = tenant_id
- .1.3.6.1.4.1.XXX.1.2.0 = device_id  
- .1.3.6.1.4.1.XXX.1.3.0 = alert_type
- .1.3.6.1.4.1.XXX.1.4.0 = severity
- .1.3.6.1.4.1.XXX.1.5.0 = summary

## Rollout Phases

### Phase 1: Webhook Only
- Basic webhook delivery with retry logic
- Simple integration management UI
- Success criteria: Customers receive webhook alerts

### Phase 2: SNMP Support
- SNMP trap delivery implementation
- OID mapping configuration
- Success criteria: SNMP traps reach configured managers

### Phase 3: Email + Advanced Features
- SMTP delivery for critical alerts
- Advanced routing and filtering
- Success criteria: Email alerts work, routing is flexible

### Future Considerations
- External secret management (HashiCorp Vault)
- Advanced delivery analytics and monitoring
- Custom protocol adapters via plugin system
