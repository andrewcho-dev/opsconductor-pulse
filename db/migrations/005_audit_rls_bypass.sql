-- Migration: 005_audit_rls_bypass.sql
-- Purpose: Track RLS bypass in operator audit log
-- Date: 2026-02-02

ALTER TABLE operator_audit_log
ADD COLUMN IF NOT EXISTS rls_bypassed BOOLEAN DEFAULT true;
