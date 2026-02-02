# Task 001: SNMP Schema Extension

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Create/Modify".
> Verify your work against the acceptance criteria.
> Commit with the exact message in the "Commit" section when done.

---

## Context

We need to extend the integrations system to support SNMP trap destinations alongside webhooks. Customers will configure SNMP integrations with the same tenant isolation as webhooks.

**Read first**:
- `db/migrations/` (existing schema)
- `services/ui_iot/models/` (existing models)

**Depends on**: Phase 3.5 complete

---

## Task

### 1.1 Create migration for SNMP support

Create `db/migrations/011_snmp_integrations.sql`:

```sql
-- Add integration type enum if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type') THEN
        CREATE TYPE integration_type AS ENUM ('webhook', 'snmp');
    END IF;
END$$;

-- Add type column to integrations (default webhook for existing rows)
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS type integration_type NOT NULL DEFAULT 'webhook';

-- Add SNMP configuration column (JSON)
-- Structure for SNMPv2c: {"version": "2c", "community": "public"}
-- Structure for SNMPv3: {"version": "3", "username": "...", "auth_protocol": "SHA", "auth_password": "...", "priv_protocol": "AES", "priv_password": "..."}
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_config JSONB;

-- Add SNMP destination columns
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_host VARCHAR(255);

ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_port INTEGER DEFAULT 162;

-- Add constraint: webhook requires webhook_url, snmp requires snmp_host
ALTER TABLE integrations
ADD CONSTRAINT integration_type_config_check CHECK (
    (type = 'webhook' AND webhook_url IS NOT NULL) OR
    (type = 'snmp' AND snmp_host IS NOT NULL AND snmp_config IS NOT NULL)
);

-- Index for type queries
CREATE INDEX IF NOT EXISTS idx_integrations_type ON integrations(type);

-- Add SNMP-specific OID configuration
ALTER TABLE integrations
ADD COLUMN IF NOT EXISTS snmp_oid_prefix VARCHAR(128) DEFAULT '1.3.6.1.4.1.99999';

COMMENT ON COLUMN integrations.type IS 'Integration output type: webhook or snmp';
COMMENT ON COLUMN integrations.snmp_config IS 'SNMP authentication config (v2c community or v3 credentials)';
COMMENT ON COLUMN integrations.snmp_host IS 'SNMP trap destination hostname or IP';
COMMENT ON COLUMN integrations.snmp_port IS 'SNMP trap destination port (default 162)';
COMMENT ON COLUMN integrations.snmp_oid_prefix IS 'Base OID for trap varbinds';
```

### 1.2 Create SNMP config validation schema

Create `services/ui_iot/schemas/snmp.py`:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from enum import Enum


class SNMPVersion(str, Enum):
    V2C = "2c"
    V3 = "3"


class SNMPAuthProtocol(str, Enum):
    MD5 = "MD5"
    SHA = "SHA"


class SNMPPrivProtocol(str, Enum):
    DES = "DES"
    AES = "AES"


class SNMPv2cConfig(BaseModel):
    """SNMPv2c configuration with community string."""
    version: Literal["2c"] = "2c"
    community: str = Field(..., min_length=1, max_length=64)


class SNMPv3Config(BaseModel):
    """SNMPv3 configuration with authentication and privacy."""
    version: Literal["3"] = "3"
    username: str = Field(..., min_length=1, max_length=64)
    auth_protocol: SNMPAuthProtocol = SNMPAuthProtocol.SHA
    auth_password: str = Field(..., min_length=8, max_length=64)
    priv_protocol: Optional[SNMPPrivProtocol] = SNMPPrivProtocol.AES
    priv_password: Optional[str] = Field(None, min_length=8, max_length=64)

    @field_validator('priv_password')
    @classmethod
    def priv_password_required_if_priv_protocol(cls, v, info):
        if info.data.get('priv_protocol') and not v:
            raise ValueError('priv_password required when priv_protocol is set')
        return v


class SNMPIntegrationCreate(BaseModel):
    """Create SNMP integration request."""
    name: str = Field(..., min_length=1, max_length=128)
    snmp_host: str = Field(..., min_length=1, max_length=255)
    snmp_port: int = Field(default=162, ge=1, le=65535)
    snmp_config: SNMPv2cConfig | SNMPv3Config
    snmp_oid_prefix: str = Field(default="1.3.6.1.4.1.99999", pattern=r'^[0-9.]+$')
    enabled: bool = True


class SNMPIntegrationUpdate(BaseModel):
    """Update SNMP integration request."""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    snmp_host: Optional[str] = Field(None, min_length=1, max_length=255)
    snmp_port: Optional[int] = Field(None, ge=1, le=65535)
    snmp_config: Optional[SNMPv2cConfig | SNMPv3Config] = None
    snmp_oid_prefix: Optional[str] = Field(None, pattern=r'^[0-9.]+$')
    enabled: Optional[bool] = None


class SNMPIntegrationResponse(BaseModel):
    """SNMP integration response (credentials masked)."""
    id: str
    tenant_id: str
    name: str
    type: Literal["snmp"] = "snmp"
    snmp_host: str
    snmp_port: int
    snmp_version: str
    snmp_oid_prefix: str
    enabled: bool
    created_at: str
    updated_at: str
```

### 1.3 Update integration model

Update `services/ui_iot/models/integration.py` to include type field:

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class IntegrationType(str, Enum):
    WEBHOOK = "webhook"
    SNMP = "snmp"


class Integration(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: IntegrationType = IntegrationType.WEBHOOK
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    snmp_host: Optional[str] = None
    snmp_port: Optional[int] = 162
    snmp_config: Optional[dict] = None
    snmp_oid_prefix: Optional[str] = None
    enabled: bool = True
    created_at: str
    updated_at: str
```

---

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/011_snmp_integrations.sql` |
| CREATE | `services/ui_iot/schemas/snmp.py` |
| MODIFY | `services/ui_iot/models/integration.py` |

---

## Acceptance Criteria

- [ ] Migration creates type column with enum
- [ ] Migration adds SNMP-specific columns (snmp_host, snmp_port, snmp_config, snmp_oid_prefix)
- [ ] Constraint ensures correct config per type
- [ ] Pydantic schemas validate SNMPv2c config
- [ ] Pydantic schemas validate SNMPv3 config
- [ ] Existing webhook integrations unaffected (default type)

**Test**:
```bash
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -f db/migrations/011_snmp_integrations.sql
PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud -c "\d integrations"
```

---

## Commit

```
Add SNMP integration schema support

- Migration adds type enum (webhook, snmp)
- SNMP columns: host, port, config, oid_prefix
- Pydantic schemas for SNMPv2c and SNMPv3 config
- Updated integration model with type field

Part of Phase 4: SNMP and Alternative Outputs
```
