-- Verify all expected tables exist
SELECT 'integrations' AS table_name, EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'integrations') AS exists
UNION ALL
SELECT 'integration_routes', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'integration_routes')
UNION ALL
SELECT 'delivery_jobs', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_jobs')
UNION ALL
SELECT 'delivery_attempts', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_attempts')
UNION ALL
SELECT 'delivery_log', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'delivery_log')
UNION ALL
SELECT 'operator_audit_log', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'operator_audit_log')
UNION ALL
SELECT 'rate_limits', EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rate_limits');

-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('integrations', 'integration_routes', 'delivery_jobs', 'delivery_attempts', 'delivery_log', 'device_state', 'fleet_alert');

-- Verify SNMP columns exist on integrations
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'integrations'
  AND column_name IN ('type', 'snmp_host', 'snmp_port', 'snmp_config', 'snmp_oid_prefix');
