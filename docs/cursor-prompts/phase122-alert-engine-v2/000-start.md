# Phase 122 -- Alert Engine v2

## Overview

This phase adds four major enhancements to the OpsConductor-Pulse alert engine:

1. **Time-Window Aggregation Rules** -- WINDOW rule type with sliding-window aggregation (avg, min, max, count, sum)
2. **Alert Deduplication** -- trigger_count increment instead of duplicate alert rows
3. **Device-Group-Scoped Rules** -- restrict rule evaluation to members of a specific device group
4. **Fleet Health Score** -- single numeric score endpoint + dashboard gauge widget

## Execution Order

Each task = 1 commit. Execute in order:

| # | File | Commit summary |
|---|------|----------------|
| 1 | `001-time-window-rules.md` | feat(alerts): add WINDOW rule type with sliding-window aggregation |
| 2 | `002-alert-deduplication.md` | feat(alerts): deduplicate alerts with trigger_count + last_triggered_at |
| 3 | `003-device-group-scoped-rules.md` | feat(alerts): scope alert rules to a single device group |
| 4 | `004-fleet-health-score.md` | feat(dashboard): add fleet health score endpoint and gauge widget |

## Key Files

### Database migrations
- `db/migrations/` -- currently through 080. Phase 120 may claim 081, so check before assigning.
- Use `082_alert_window_rules.sql`, `083_alert_dedup.sql`, `084_rule_device_group.sql` if 081 is taken.
- Use `081_alert_window_rules.sql`, `082_alert_dedup.sql`, `083_rule_device_group.sql` if 081 is free.
- **Check `ls db/migrations/081*` before starting.**

### Backend
- `services/evaluator_iot/evaluator.py` -- main evaluation loop, threshold/anomaly/gap handlers
- `services/ui_iot/routes/alerts.py` -- alert CRUD routes (list_alerts, create_alert_rule, etc.)
- `services/ui_iot/routes/customer.py` -- Pydantic models (AlertRuleCreate, AlertRuleUpdate), shared deps
- `services/ui_iot/db/queries.py` -- SQL query helpers (create_alert_rule, update_alert_rule, fetch_alert_rules)
- `services/ui_iot/routes/devices.py` -- device CRUD, groups, maintenance windows

### Frontend
- `frontend/src/features/alerts/AlertRulesPage.tsx` -- rule list with table, formatCondition, formatDuration
- `frontend/src/features/alerts/AlertRuleDialog.tsx` -- create/edit dialog with ruleMode tabs
- `frontend/src/features/alerts/AlertListPage.tsx` -- alert inbox with tabbed severity
- `frontend/src/features/dashboard/DashboardPage.tsx` -- dashboard with widget grid
- `frontend/src/features/dashboard/FleetKpiStrip.tsx` -- KPI cards
- `frontend/src/services/api/types.ts` -- TypeScript interfaces (AlertRule, Alert, AlertRuleCreate, etc.)
- `frontend/src/services/api/devices.ts` -- fetchDeviceGroups, fetchFleetSummary
- `frontend/src/services/api/alerts.ts` -- alert API functions
- `frontend/src/hooks/use-alert-rules.ts` -- useAlertRules, useCreateAlertRule, useUpdateAlertRule

### Schema reference
- `alert_rules`: rule_id (UUID PK), tenant_id, name, rule_type, metric_name, operator, threshold, severity, duration_seconds, duration_minutes, description, site_ids, group_ids, conditions (JSONB), match_mode, enabled, created_at, updated_at
- `fleet_alert`: id (BIGSERIAL PK), tenant_id, device_id, site_id, alert_type, fingerprint, status, severity, confidence, summary, details (JSONB), silenced_until, acknowledged_by, acknowledged_at, escalation_level, escalated_at, created_at, closed_at
- `device_groups`: group_id (TEXT), tenant_id, name, description, created_at, updated_at -- PK is (tenant_id, group_id)
- `device_group_members`: tenant_id, group_id, device_id, added_at -- PK is (tenant_id, group_id, device_id)

## Verification (after all 4 tasks)

```bash
# 1. Run migrations
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_alert_window_rules.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_alert_dedup.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/08X_rule_device_group.sql

# 2. Verify schema changes
docker exec iot-postgres psql -U iot -d iotcloud -c "\d alert_rules"
docker exec iot-postgres psql -U iot -d iotcloud -c "\d fleet_alert"

# 3. Restart services
docker compose restart evaluator ui

# 4. Run tests
cd services/ui_iot && python -m pytest tests/ -v
cd services/evaluator_iot && python -m pytest tests/ -v

# 5. Frontend
cd frontend && npm run build && npm run dev

# 6. E2E: create WINDOW rule, verify dedup, verify group scope, verify health endpoint
curl -s http://localhost:3000/customer/fleet/health | jq .
```
