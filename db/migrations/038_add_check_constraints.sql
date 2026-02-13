-- device_state status constraint
ALTER TABLE device_state
ADD CONSTRAINT chk_device_state_status
CHECK (status IN ('ONLINE', 'STALE', 'OFFLINE'));

-- fleet_alert status constraint
ALTER TABLE fleet_alert
ADD CONSTRAINT chk_fleet_alert_status
CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED'));

-- device_registry status constraint
ALTER TABLE device_registry
ADD CONSTRAINT chk_device_registry_status
CHECK (status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED'));

-- delivery_jobs status constraint
ALTER TABLE delivery_jobs
ADD CONSTRAINT chk_delivery_jobs_status
CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'dead'));
