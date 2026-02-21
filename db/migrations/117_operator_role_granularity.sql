-- Migration: 117_operator_role_granularity.sql
-- Purpose: Introduce granular operator read/write roles.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pulse_operator_read') THEN
        CREATE ROLE pulse_operator_read NOLOGIN BYPASSRLS;
    END IF;
END
$$;

GRANT SELECT ON ALL TABLES IN SCHEMA public TO pulse_operator_read;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pulse_operator_read;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_operator_read;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pulse_operator_write') THEN
        CREATE ROLE pulse_operator_write NOLOGIN;
    END IF;
END
$$;

GRANT INSERT, UPDATE ON device_registry TO pulse_operator_write;
GRANT INSERT, UPDATE ON fleet_alert TO pulse_operator_write;
GRANT INSERT, UPDATE ON subscriptions TO pulse_operator_write;
GRANT INSERT, UPDATE ON system_metrics TO pulse_operator_write;
GRANT INSERT, UPDATE ON integrations TO pulse_operator_write;
GRANT INSERT, UPDATE ON integration_routes TO pulse_operator_write;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO pulse_operator_write;

-- Transition: keep legacy pulse_operator role untouched in this migration.
