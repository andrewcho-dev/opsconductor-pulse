-- Migration: 118_rls_gap_fixes.sql
-- Purpose: Close remaining tenant-data RLS gaps identified in the phase 201 audit.

-- Enable RLS on alert_digest_settings (missed in original schema)
ALTER TABLE alert_digest_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_digest_settings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON alert_digest_settings;
CREATE POLICY tenant_isolation ON alert_digest_settings
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on device_extended_attributes (missed in original schema)
ALTER TABLE device_extended_attributes ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_extended_attributes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON device_extended_attributes;
CREATE POLICY tenant_isolation ON device_extended_attributes
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on escalation_policies (missed in original schema)
ALTER TABLE escalation_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE escalation_policies FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON escalation_policies;
CREATE POLICY tenant_isolation ON escalation_policies
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on notification_channels (missed in original schema)
ALTER TABLE notification_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_channels FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON notification_channels;
CREATE POLICY tenant_isolation ON notification_channels
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on notification_jobs (missed in original schema)
ALTER TABLE notification_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_jobs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON notification_jobs;
CREATE POLICY tenant_isolation ON notification_jobs
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on notification_routing_rules (missed in original schema)
ALTER TABLE notification_routing_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_routing_rules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON notification_routing_rules;
CREATE POLICY tenant_isolation ON notification_routing_rules
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on oncall_schedules (missed in original schema)
ALTER TABLE oncall_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE oncall_schedules FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON oncall_schedules;
CREATE POLICY tenant_isolation ON oncall_schedules
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on quarantine_counters_minute (missed in original schema)
ALTER TABLE quarantine_counters_minute ENABLE ROW LEVEL SECURITY;
ALTER TABLE quarantine_counters_minute FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON quarantine_counters_minute;
CREATE POLICY tenant_isolation ON quarantine_counters_minute
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on report_runs (missed in original schema)
ALTER TABLE report_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON report_runs;
CREATE POLICY tenant_isolation ON report_runs
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on subscription_notifications (had RLS enabled but no tenant policy)
ALTER TABLE subscription_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_notifications FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON subscription_notifications;
CREATE POLICY tenant_isolation ON subscription_notifications
  USING (tenant_id = current_setting('app.tenant_id', true)::text);

-- Enable RLS on sites (tenant-scoped table created in seed migration)
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE sites FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON sites;
CREATE POLICY tenant_isolation ON sites
  USING (tenant_id = current_setting('app.tenant_id', true)::text);
