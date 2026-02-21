# Prompt 002 — Backend: Fleet Uptime Summary

Read `services/ui_iot/routes/customer.py`.

## Add: GET /customer/fleet/uptime-summary

No parameters needed.

Logic: for the last 24h, per device:
- Count devices currently ONLINE (no open NO_TELEMETRY alert)
- Count devices currently OFFLINE (open NO_TELEMETRY alert exists)
- Compute average uptime % across all devices (use same formula as per-device endpoint but aggregate)

Response:
```json
{
  "total_devices": 42,
  "online": 39,
  "offline": 3,
  "avg_uptime_pct": 97.2,
  "as_of": "2026-01-01T12:00:00Z"
}
```

## Acceptance Criteria
- [ ] GET /customer/fleet/uptime-summary exists
- [ ] Returns online/offline counts and avg_uptime_pct
