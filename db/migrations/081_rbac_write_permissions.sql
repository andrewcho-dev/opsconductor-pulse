-- Migration 081: Fine-grained write permissions for all mutating endpoints
-- Date: 2026-02-16

-- New permission rows (idempotent)
INSERT INTO permissions (action, category, description) VALUES
    -- Devices (some already exist in 080, those will be skipped)
    ('devices.create',        'devices',      'Create/provision new devices'),
    ('devices.update',        'devices',      'Update device properties'),
    ('devices.delete',        'devices',      'Delete devices'),
    ('devices.decommission',  'devices',      'Decommission devices'),
    ('devices.import',        'devices',      'Bulk import devices via CSV'),
    ('devices.tokens.rotate', 'devices',      'Rotate device API tokens'),
    ('devices.tokens.revoke', 'devices',      'Revoke device API tokens'),
    ('devices.tags.write',    'devices',      'Add/remove/set device tags'),
    ('devices.groups.write',  'devices',      'Manage device groups'),
    ('devices.twin.write',    'devices',      'Update device twin desired state'),
    ('devices.commands.send', 'devices',      'Send commands to devices'),

    -- Alerts
    ('alerts.acknowledge',    'alerts',       'Acknowledge alerts'),
    ('alerts.close',          'alerts',       'Close/resolve alerts'),
    ('alerts.silence',        'alerts',       'Silence alerts'),
    ('alerts.digest.write',   'alerts',       'Manage alert digest settings'),

    -- Alert rules
    ('alert-rules.create',    'alert-rules',  'Create alert rules'),
    ('alert-rules.update',    'alert-rules',  'Update alert rules'),
    ('alert-rules.delete',    'alert-rules',  'Delete alert rules'),
    ('alert-rules.templates', 'alert-rules',  'Apply alert rule templates'),

    -- Notifications
    ('notifications.create',  'notifications','Create notification channels'),
    ('notifications.update',  'notifications','Update notification channels'),
    ('notifications.delete',  'notifications','Delete notification channels'),
    ('notifications.test',    'notifications','Test notification channels'),
    ('notifications.routing.create', 'notifications', 'Create routing rules'),
    ('notifications.routing.update', 'notifications', 'Update routing rules'),
    ('notifications.routing.delete', 'notifications', 'Delete routing rules'),

    -- Escalation
    ('escalation.create',     'escalation',   'Create escalation policies'),
    ('escalation.update',     'escalation',   'Update escalation policies'),
    ('escalation.delete',     'escalation',   'Delete escalation policies'),

    -- On-call
    ('oncall.create',         'oncall',       'Create on-call schedules'),
    ('oncall.update',         'oncall',       'Update on-call schedules'),
    ('oncall.delete',         'oncall',       'Delete on-call schedules'),
    ('oncall.layers.write',   'oncall',       'Manage on-call layers'),
    ('oncall.overrides.write','oncall',       'Manage on-call overrides'),

    -- Maintenance
    ('maintenance.create',    'maintenance',  'Create maintenance windows'),
    ('maintenance.update',    'maintenance',  'Update maintenance windows'),
    ('maintenance.delete',    'maintenance',  'Delete maintenance windows')
ON CONFLICT (action) DO NOTHING;

-- Grant ALL new permissions to "Full Admin" system role.
-- Full Admin already gets all permissions via the blanket INSERT in 080,
-- but if these were added after the role was created, we need to backfill.
DO $$
DECLARE
    v_role_id UUID;
BEGIN
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Full Admin' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.id NOT IN (SELECT permission_id FROM role_permissions WHERE role_id = v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;

    -- Device Manager: add device-specific write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Device Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'devices.create', 'devices.update', 'devices.delete', 'devices.decommission',
            'devices.import', 'devices.tokens.rotate', 'devices.tokens.revoke',
            'devices.tags.write', 'devices.groups.write', 'devices.twin.write',
            'devices.commands.send',
            'maintenance.create', 'maintenance.update', 'maintenance.delete'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Alert Manager: add alert and alert-rule write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Alert Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'alerts.acknowledge', 'alerts.close', 'alerts.silence', 'alerts.digest.write',
            'alert-rules.create', 'alert-rules.update', 'alert-rules.delete', 'alert-rules.templates',
            'maintenance.create', 'maintenance.update', 'maintenance.delete'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Integration Manager: add notification write permissions
    SELECT id INTO v_role_id FROM roles WHERE tenant_id IS NULL AND name = 'Integration Manager' AND is_system = true;
    IF v_role_id IS NOT NULL THEN
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT v_role_id, p.id FROM permissions p
        WHERE p.action IN (
            'notifications.create', 'notifications.update', 'notifications.delete', 'notifications.test',
            'notifications.routing.create', 'notifications.routing.update', 'notifications.routing.delete',
            'escalation.create', 'escalation.update', 'escalation.delete',
            'oncall.create', 'oncall.update', 'oncall.delete',
            'oncall.layers.write', 'oncall.overrides.write'
        )
        ON CONFLICT DO NOTHING;
    END IF;

    -- Viewer: gets NO write permissions (already correct from 080, but confirm)
    -- No action needed.
END $$;

