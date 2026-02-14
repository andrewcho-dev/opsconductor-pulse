-- Migration 072: Remove dead operator_read RLS policy on telemetry
--
-- Background:
--   021_telemetry_hypertable.sql created a policy:
--     CREATE POLICY operator_read ON telemetry FOR SELECT
--       USING (current_setting('app.role', true) IN ('operator', 'operator_admin'));
--
--   This policy is dead code. The setting 'app.role' is never set anywhere in the codebase.
--   Operator read access to telemetry is correctly handled via the pulse_operator DB role
--   which has BYPASSRLS - all RLS policies are skipped for that role entirely.
--
--   Leaving the policy in place is misleading and creates false confidence that
--   operator access is controlled by app.role when it is not.

DROP POLICY IF EXISTS operator_read ON telemetry;

-- Verify remaining policies on telemetry
SELECT policyname, cmd, qual
FROM pg_policies
WHERE tablename = 'telemetry'
ORDER BY policyname;

-- Expected: only tenant isolation policy remains
-- operator_read should NOT appear
