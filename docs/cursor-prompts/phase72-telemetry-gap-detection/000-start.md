# Phase 72: Telemetry Gap Detection

## What Exists

- `device_state` table: `last_heartbeat_at`, `last_telemetry_at`, `last_seen_at`, `status`
- `NO_HEARTBEAT` alert: fires when heartbeat age > `HEARTBEAT_STALE_SECONDS` (30s default)
- Fingerprint: `"NO_HEARTBEAT:{device_id}"`
- `alert_rules` table: has `metric_name`, `threshold`, `device_type` — single-metric rules
- Current heartbeat check only looks at `msg_type='heartbeat'` messages, NOT data telemetry

## The Gap

A device can send heartbeats (alive pings) but stop sending actual metric data. For example:
- Device still pinging every 30s → `NO_HEARTBEAT` never fires
- But `temperature` metric hasn't arrived in 10 minutes → no alert

This phase adds `NO_TELEMETRY` alerts for metric-specific data gaps.

## What This Phase Adds

1. **Migration**: Add `NO_TELEMETRY` to alert_type constraint; add `telemetry_gap_rules` table (or use `alert_rules` with `rule_type='telemetry_gap'`)
2. **Evaluator**: New evaluation loop — for each `rule_type='telemetry_gap'` rule, check if `metric_name` has had any reading in the last `gap_minutes` — fire `NO_TELEMETRY` alert if not
3. **Backend API**: Accept `rule_type='telemetry_gap'` with `gap_config` in `AlertRuleCreate`
4. **Frontend**: Telemetry gap rule form option

## Gap Rule Config (stored in `conditions` JSONB)

```json
{
  "metric_name": "temperature",
  "gap_minutes": 10,
  "min_expected_per_hour": 6
}
```

Alert fires when: no `temperature` reading in the last `gap_minutes` minutes.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Migration: NO_TELEMETRY alert type |
| 002 | Evaluator: gap detection loop |
| 003 | Backend API: telemetry_gap rule type |
| 004 | Frontend: gap rule form |
| 005 | Unit tests |
| 006 | Verify |
