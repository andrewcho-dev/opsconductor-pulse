-- Migration 098: Fix customer users incorrectly bootstrapped as Viewer
--
-- The bootstrap logic previously mapped 'customer' Keycloak realm role to
-- 'Viewer' system role, which has read-only permissions. Customers need
-- 'Full Admin' within their tenant to manage devices, alerts, channels, etc.
--
-- This upgrades all system-bootstrap Viewer assignments to Full Admin.

UPDATE user_role_assignments
SET role_id = (
    SELECT id FROM roles WHERE name = 'Full Admin' AND is_system = true AND tenant_id IS NULL
)
WHERE assigned_by = 'system-bootstrap'
  AND role_id = (
    SELECT id FROM roles WHERE name = 'Viewer' AND is_system = true AND tenant_id IS NULL
  );

