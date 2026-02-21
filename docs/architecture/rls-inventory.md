# RLS Inventory

Last updated: 2026-02-20

## Summary

| Status | Count |
|--------|-------|
| PROTECTED | 61 |
| EXEMPT | 21 |
| REVIEW | 0 |
| GAP (unfixed) | 0 |

All tables with tenant data are now protected by RLS.
Tables listed as EXEMPT contain no tenant-specific rows and are intentionally excluded.

## Adding New Tables

When creating a new table that contains tenant data:
1. Always add `tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE`
2. Always add `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY;`
3. Always add the standard `tenant_isolation` policy (see existing tables for the pattern)
4. Add the table to this inventory file with status PROTECTED

| Table | Has tenant_id | RLS Enabled | Policies | Status | Notes |
|-------|---------------|-------------|----------|--------|-------|
| account_tiers | No | No | 0 | EXEMPT | Subscription tier catalog (global package metadata) |
| alert_digest_settings | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| alert_maintenance_windows | Yes | Yes | 1 | PROTECTED | - |
| alert_rules | Yes | Yes | 1 | PROTECTED | - |
| app_settings | No | No | 0 | EXEMPT | Global application settings |
| audit_log | Yes | Yes | 1 | PROTECTED | - |
| carrier_integrations | Yes | Yes | 2 | PROTECTED | - |
| dashboard_widgets | No | Yes | 1 | EXEMPT | Template/global widget definitions (no tenant_id) |
| dashboards | Yes | Yes | 1 | PROTECTED | - |
| dead_letter_messages | Yes | Yes | 1 | PROTECTED | - |
| delivery_attempts | Yes | Yes | 1 | PROTECTED | - |
| delivery_jobs | Yes | Yes | 2 | PROTECTED | - |
| delivery_log | Yes | Yes | 1 | PROTECTED | - |
| device_api_tokens | Yes | Yes | 1 | PROTECTED | - |
| device_certificates | Yes | Yes | 2 | PROTECTED | - |
| device_commands | Yes | Yes | 1 | PROTECTED | - |
| device_connection_events | Yes | Yes | 1 | PROTECTED | - |
| device_connections | Yes | Yes | 3 | PROTECTED | - |
| device_extended_attributes | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| device_group_members | Yes | Yes | 1 | PROTECTED | - |
| device_groups | Yes | Yes | 1 | PROTECTED | - |
| device_health_telemetry | Yes | Yes | 3 | PROTECTED | - |
| device_modules | Yes | Yes | 3 | PROTECTED | - |
| device_plans | No | No | 0 | EXEMPT | Global plan catalog linking device plans to subscription packages |
| device_registry | Yes | Yes | 3 | PROTECTED | - |
| device_sensors | Yes | Yes | 3 | PROTECTED | - |
| device_state | Yes | Yes | 1 | PROTECTED | - |
| device_subscriptions | Yes | Yes | 1 | PROTECTED | - |
| device_tags | Yes | Yes | 1 | PROTECTED | - |
| device_templates | Yes | Yes | 4 | PROTECTED | - |
| device_tiers | No | No | 0 | EXEMPT | Global tier definitions |
| device_transports | Yes | Yes | 3 | PROTECTED | - |
| dynamic_device_groups | Yes | Yes | 1 | PROTECTED | - |
| escalation_levels | No | No | 0 | EXEMPT | Global escalation level definitions |
| escalation_policies | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| export_jobs | Yes | Yes | 1 | PROTECTED | - |
| firmware_versions | Yes | Yes | 1 | PROTECTED | - |
| fleet_alert | Yes | Yes | 1 | PROTECTED | - |
| integration_routes | Yes | Yes | 1 | PROTECTED | - |
| integrations | Yes | Yes | 1 | PROTECTED | - |
| job_executions | Yes | Yes | 1 | PROTECTED | - |
| jobs | Yes | Yes | 1 | PROTECTED | - |
| maintenance_log | No | No | 0 | EXEMPT | Platform maintenance/audit log with no tenant_id |
| message_routes | Yes | Yes | 1 | PROTECTED | - |
| metric_catalog | Yes | Yes | 1 | PROTECTED | - |
| metric_mappings | Yes | Yes | 1 | PROTECTED | - |
| normalized_metrics | Yes | Yes | 1 | PROTECTED | - |
| notification_channels | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| notification_jobs | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| notification_log | No | No | 0 | EXEMPT | Global delivery operational log |
| notification_routing_rules | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| oncall_layers | No | No | 0 | EXEMPT | Shared schedule layer templates |
| oncall_overrides | No | No | 0 | EXEMPT | Shared override templates without tenant_id |
| oncall_schedules | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| operator_audit_log | No | No | 0 | EXEMPT | Operator-only audit stream (cross-tenant) |
| ota_campaigns | Yes | Yes | 1 | PROTECTED | - |
| ota_device_status | Yes | Yes | 1 | PROTECTED | - |
| permissions | No | No | 0 | EXEMPT | Global IAM action catalog |
| plan_tier_defaults | No | No | 0 | EXEMPT | Global defaults for plan-tier relationships |
| quarantine_counters_minute | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| quarantine_events | Yes | Yes | 2 | PROTECTED | - |
| rate_limits | Yes | Yes | 1 | PROTECTED | - |
| report_runs | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| role_permissions | No | No | 0 | EXEMPT | Global role-to-permission mapping table |
| roles | Yes | Yes | 2 | PROTECTED | - |
| sensors | Yes | Yes | 3 | PROTECTED | - |
| sites | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| subscription_audit | Yes | Yes | 1 | PROTECTED | - |
| subscription_notifications | Yes | Yes | 1 | PROTECTED | Fixed in 118_rls_gap_fixes.sql |
| subscription_plans | No | No | 0 | EXEMPT | Global subscription plan catalog |
| subscription_tier_allocations | No | No | 0 | EXEMPT | Global allocation lookup table |
| subscriptions | Yes | Yes | 3 | PROTECTED | - |
| system_metrics | No | No | 0 | EXEMPT | Platform-wide metrics |
| telemetry | Yes | Yes | 3 | PROTECTED | - |
| template_commands | No | Yes | 3 | EXEMPT | Global command templates (tenant applied at assignment) |
| template_metrics | No | Yes | 3 | EXEMPT | Global metric templates (tenant applied at assignment) |
| template_slots | No | Yes | 3 | EXEMPT | Global template slot definitions |
| tenant_subscription | Yes | Yes | 2 | PROTECTED | - |
| tenant_subscription_archive | No | No | 0 | EXEMPT | Legacy archive table without tenant-scoped access path |
| tenants | Yes | Yes | 5 | PROTECTED | - |
| user_preferences | Yes | Yes | 1 | PROTECTED | - |
| user_role_assignments | Yes | Yes | 1 | PROTECTED | - |
