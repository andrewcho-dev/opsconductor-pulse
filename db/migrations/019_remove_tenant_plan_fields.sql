-- Remove unused business model fields (not yet defined)
ALTER TABLE tenants DROP COLUMN IF EXISTS plan;
ALTER TABLE tenants DROP COLUMN IF EXISTS max_devices;
ALTER TABLE tenants DROP COLUMN IF EXISTS max_rules;
