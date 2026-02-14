BEGIN;

CREATE TABLE IF NOT EXISTS device_api_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    client_id   TEXT NOT NULL UNIQUE,
    token_hash  TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT 'default',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

ALTER TABLE device_api_tokens
    DROP CONSTRAINT IF EXISTS fk_device_api_tokens_device;
ALTER TABLE device_api_tokens
    ADD CONSTRAINT fk_device_api_tokens_device
    FOREIGN KEY (tenant_id, device_id)
    REFERENCES device_registry(tenant_id, device_id)
    ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_device_api_tokens_device
    ON device_api_tokens(tenant_id, device_id);
CREATE INDEX IF NOT EXISTS idx_device_api_tokens_tenant
    ON device_api_tokens(tenant_id);

ALTER TABLE device_api_tokens ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_api_tokens_tenant_isolation ON device_api_tokens;
CREATE POLICY device_api_tokens_tenant_isolation
    ON device_api_tokens
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
