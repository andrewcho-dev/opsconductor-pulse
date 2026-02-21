# Prompt 001 — Backend: Per-Device Uptime Endpoint

Read `services/ui_iot/routes/customer.py` fully.

## Add: GET /customer/devices/{device_id}/uptime

Query parameters:
- `range`: `24h` | `7d` | `30d` (default: `24h`)

Logic:
1. Determine interval start: `now() - interval '{range}'`
2. Count how many NO_TELEMETRY alerts were OPEN for this device in that range:
   - Use `fleet_alert` where `tenant_id = $1 AND device_id = $2 AND alert_type = 'NO_TELEMETRY'`
   - Compute total offline seconds: sum of `EXTRACT(EPOCH FROM (COALESCE(closed_at, now()) - GREATEST(opened_at, $interval_start)))` for alerts in range
3. Compute uptime %: `(range_seconds - offline_seconds) / range_seconds * 100`
4. Also return: `status` = "online" if no currently OPEN NO_TELEMETRY alert, else "offline"

Response:
```json
{
  "device_id": "uuid",
  "range": "24h",
  "uptime_pct": 98.5,
  "offline_seconds": 1260,
  "range_seconds": 86400,
  "status": "online"
}
```

## Acceptance Criteria
- [ ] GET /customer/devices/{id}/uptime endpoint exists
- [ ] Returns uptime_pct, offline_seconds, status
- [ ] range parameter respected
