# Prompt 001 — Migration 064: device_api_tokens

Create `db/migrations/064_device_api_tokens.sql`.

## Schema

```sql
CREATE TABLE IF NOT EXISTS device_api_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   TEXT NOT NULL,
    device_id   UUID NOT NULL REFERENCES device_registry(id) ON DELETE CASCADE,
    client_id   TEXT NOT NULL UNIQUE,
    token_hash  TEXT NOT NULL,        -- bcrypt hash of the raw password
    label       TEXT NOT NULL DEFAULT 'default',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at  TIMESTAMPTZ
);

CREATE INDEX idx_device_api_tokens_device ON device_api_tokens(device_id);
CREATE INDEX idx_device_api_tokens_tenant ON device_api_tokens(tenant_id);

ALTER TABLE device_api_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY device_api_tokens_tenant_isolation
    ON device_api_tokens
    USING (tenant_id = current_setting('app.tenant_id', true));
```

Note: when a device is provisioned (POST /provision/device), insert a row here too with the generated client_id and hash of the password.

## Acceptance Criteria
- [ ] Migration file exists
- [ ] Table has RLS policy
- [ ] Foreign key to device_registry
