# Task 001 -- OTA Data Model and API Routes

## Commit message
`feat: add OTA firmware versions and campaigns data model and API`

## Overview

Create three database migration files for the OTA firmware update feature, then add a
new `routes/ota.py` with full CRUD + lifecycle endpoints for firmware versions and OTA
campaigns. Register the router in `app.py`.

---

## Step 1: Migration 081 -- firmware_versions table

Create file: `db/migrations/081_firmware_versions.sql`

```sql
-- Migration 081: Firmware Versions Registry
-- Stores metadata about firmware binaries available for OTA deployment.

BEGIN;

CREATE TABLE IF NOT EXISTS firmware_versions (
    id              SERIAL       PRIMARY KEY,
    tenant_id       TEXT         NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    version         VARCHAR(50)  NOT NULL,
    description     TEXT,
    file_url        TEXT         NOT NULL,
    file_size_bytes BIGINT,
    checksum_sha256 VARCHAR(64),
    device_type     VARCHAR(50),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by      TEXT,

    CONSTRAINT uq_firmware_tenant_version UNIQUE (tenant_id, version, device_type)
);

CREATE INDEX IF NOT EXISTS idx_firmware_versions_tenant
    ON firmware_versions (tenant_id);

CREATE INDEX IF NOT EXISTS idx_firmware_versions_device_type
    ON firmware_versions (tenant_id, device_type);

ALTER TABLE firmware_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS firmware_versions_tenant_isolation ON firmware_versions;
CREATE POLICY firmware_versions_tenant_isolation ON firmware_versions
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
```

## Step 2: Migration 082 -- ota_campaigns table

Create file: `db/migrations/082_ota_campaigns.sql`

```sql
-- Migration 082: OTA Campaigns
-- An OTA campaign targets a device group with a specific firmware version.
-- Supports linear and canary rollout strategies with automatic abort on failure threshold.

BEGIN;

CREATE TABLE IF NOT EXISTS ota_campaigns (
    id                  SERIAL        PRIMARY KEY,
    tenant_id           TEXT          NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    name                VARCHAR(100)  NOT NULL,
    firmware_version_id INT           NOT NULL REFERENCES firmware_versions(id) ON DELETE RESTRICT,
    target_group_id     TEXT          NOT NULL,
    rollout_strategy    VARCHAR(20)   NOT NULL DEFAULT 'linear'
                        CHECK (rollout_strategy IN ('linear', 'canary')),
    rollout_rate        INT           NOT NULL DEFAULT 10,
    abort_threshold     FLOAT         NOT NULL DEFAULT 0.1,
    status              VARCHAR(20)   NOT NULL DEFAULT 'CREATED'
                        CHECK (status IN ('CREATED', 'RUNNING', 'PAUSED', 'COMPLETED', 'ABORTED')),
    total_devices       INT           NOT NULL DEFAULT 0,
    succeeded           INT           NOT NULL DEFAULT 0,
    failed              INT           NOT NULL DEFAULT 0,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_by          TEXT
);

CREATE INDEX IF NOT EXISTS idx_ota_campaigns_tenant
    ON ota_campaigns (tenant_id);

CREATE INDEX IF NOT EXISTS idx_ota_campaigns_status
    ON ota_campaigns (tenant_id, status);

ALTER TABLE ota_campaigns ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ota_campaigns_tenant_isolation ON ota_campaigns;
CREATE POLICY ota_campaigns_tenant_isolation ON ota_campaigns
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
```

## Step 3: Migration 083 -- ota_device_status table

Create file: `db/migrations/083_ota_device_status.sql`

```sql
-- Migration 083: OTA Per-Device Status
-- Tracks individual device progress within an OTA campaign.

BEGIN;

CREATE TABLE IF NOT EXISTS ota_device_status (
    id              BIGSERIAL     PRIMARY KEY,
    tenant_id       TEXT          NOT NULL,
    campaign_id     INT           NOT NULL REFERENCES ota_campaigns(id) ON DELETE CASCADE,
    device_id       VARCHAR       NOT NULL,
    status          VARCHAR(20)   NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'DOWNLOADING', 'INSTALLING', 'SUCCESS', 'FAILED', 'SKIPPED')),
    progress_pct    INT           NOT NULL DEFAULT 0
                    CHECK (progress_pct >= 0 AND progress_pct <= 100),
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ota_device_campaign UNIQUE (tenant_id, campaign_id, device_id)
);

CREATE INDEX IF NOT EXISTS idx_ota_device_status_campaign
    ON ota_device_status (tenant_id, campaign_id);

CREATE INDEX IF NOT EXISTS idx_ota_device_status_pending
    ON ota_device_status (tenant_id, campaign_id, status)
    WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_ota_device_status_device
    ON ota_device_status (tenant_id, device_id);

ALTER TABLE ota_device_status ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ota_device_status_tenant_isolation ON ota_device_status;
CREATE POLICY ota_device_status_tenant_isolation ON ota_device_status
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMIT;
```

---

## Step 4: Create routes/ota.py

Create file: `services/ui_iot/routes/ota.py`

Follow the exact same patterns used in `routes/jobs.py` and `routes/devices.py`:
- Import everything from `routes.customer` via wildcard (provides `APIRouter`, `Depends`,
  `JWTBearer`, `inject_tenant_context`, `require_customer`, `get_tenant_id`, `get_user`,
  `tenant_connection`, `get_db_pool`, `HTTPException`, `Query`, `BaseModel`, `Field`, etc.)
- Create router with `prefix="/customer"`, `tags=["ota"]`, standard auth dependencies.
- All DB operations use `async with tenant_connection(pool, tenant_id) as conn:`.

```python
"""OTA firmware update routes -- firmware versions + campaigns."""

from routes.customer import *  # noqa: F401,F403
from typing import Any

router = APIRouter(
    prefix="/customer",
    tags=["ota"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


# ── Pydantic Models ──────────────────────────────────────────────

class FirmwareCreate(BaseModel):
    version: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    file_url: str = Field(..., min_length=1)
    file_size_bytes: int | None = None
    checksum_sha256: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=50)


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    firmware_version_id: int
    target_group_id: str = Field(..., min_length=1)
    rollout_strategy: str = Field(default="linear", pattern="^(linear|canary)$")
    rollout_rate: int = Field(default=10, ge=1, le=1000)
    abort_threshold: float = Field(default=0.1, ge=0.0, le=1.0)


# ── Firmware Version Endpoints ───────────────────────────────────

@router.get("/firmware")
async def list_firmware_versions(
    device_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        conditions = ["tenant_id = $1"]
        params: list[Any] = [tenant_id]
        if device_type:
            params.append(device_type)
            conditions.append(f"device_type = ${len(params)}")
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = await conn.fetch(
            f"""
            SELECT id, version, description, file_url, file_size_bytes,
                   checksum_sha256, device_type, created_at, created_by
            FROM firmware_versions
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
    return {"firmware_versions": [dict(r) for r in rows], "total": len(rows)}


@router.post("/firmware", status_code=201)
async def create_firmware_version(body: FirmwareCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()
    async with tenant_connection(pool, tenant_id) as conn:
        # Check for duplicate version+device_type
        existing = await conn.fetchval(
            """
            SELECT 1 FROM firmware_versions
            WHERE tenant_id = $1 AND version = $2 AND device_type IS NOT DISTINCT FROM $3
            """,
            tenant_id,
            body.version,
            body.device_type,
        )
        if existing:
            raise HTTPException(status_code=409, detail="Firmware version already exists for this device type")

        row = await conn.fetchrow(
            """
            INSERT INTO firmware_versions
                (tenant_id, version, description, file_url, file_size_bytes,
                 checksum_sha256, device_type, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, version, description, file_url, file_size_bytes,
                      checksum_sha256, device_type, created_at, created_by
            """,
            tenant_id,
            body.version,
            body.description,
            body.file_url,
            body.file_size_bytes,
            body.checksum_sha256,
            body.device_type,
            user.get("sub") or user.get("user_id"),
        )
    return dict(row)


# ── Campaign Endpoints ───────────────────────────────────────────

@router.get("/ota/campaigns")
async def list_campaigns(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        conditions = ["c.tenant_id = $1"]
        params: list[Any] = [tenant_id]
        if status:
            params.append(status.upper())
            conditions.append(f"c.status = ${len(params)}")
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        rows = await conn.fetch(
            f"""
            SELECT c.id, c.name, c.status, c.rollout_strategy,
                   c.rollout_rate, c.abort_threshold,
                   c.total_devices, c.succeeded, c.failed,
                   c.target_group_id,
                   fv.version AS firmware_version,
                   fv.device_type AS firmware_device_type,
                   c.started_at, c.completed_at, c.created_at, c.created_by
            FROM ota_campaigns c
            JOIN firmware_versions fv ON fv.id = c.firmware_version_id
            WHERE {where}
            ORDER BY c.created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
    return {"campaigns": [dict(r) for r in rows], "total": len(rows)}


@router.post("/ota/campaigns", status_code=201)
async def create_campaign(body: CampaignCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    async with tenant_connection(pool, tenant_id) as conn:
        # Validate firmware version exists and belongs to tenant
        fw = await conn.fetchrow(
            "SELECT id, version, file_url, checksum_sha256 FROM firmware_versions WHERE id = $1 AND tenant_id = $2",
            body.firmware_version_id,
            tenant_id,
        )
        if not fw:
            raise HTTPException(status_code=404, detail="Firmware version not found")

        # Validate device group exists and has members
        group = await conn.fetchval(
            "SELECT 1 FROM device_groups WHERE tenant_id = $1 AND group_id = $2",
            tenant_id,
            body.target_group_id,
        )
        if not group:
            raise HTTPException(status_code=404, detail="Device group not found")

        members = await conn.fetch(
            "SELECT device_id FROM device_group_members WHERE tenant_id = $1 AND group_id = $2",
            tenant_id,
            body.target_group_id,
        )
        if not members:
            raise HTTPException(status_code=400, detail="Device group has no members")

        device_ids = [m["device_id"] for m in members]

        # Create campaign
        row = await conn.fetchrow(
            """
            INSERT INTO ota_campaigns
                (tenant_id, name, firmware_version_id, target_group_id,
                 rollout_strategy, rollout_rate, abort_threshold,
                 total_devices, created_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, name, status, rollout_strategy, rollout_rate,
                      abort_threshold, total_devices, created_at, created_by
            """,
            tenant_id,
            body.name,
            body.firmware_version_id,
            body.target_group_id,
            body.rollout_strategy,
            body.rollout_rate,
            body.abort_threshold,
            len(device_ids),
            user.get("sub") or user.get("user_id"),
        )

        campaign_id = row["id"]

        # Pre-populate ota_device_status for each group member
        await conn.executemany(
            """
            INSERT INTO ota_device_status (tenant_id, campaign_id, device_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (tenant_id, campaign_id, device_id) DO NOTHING
            """,
            [(tenant_id, campaign_id, did) for did in device_ids],
        )

    return {**dict(row), "target_group_id": body.target_group_id}


@router.get("/ota/campaigns/{campaign_id}")
async def get_campaign(campaign_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        campaign = await conn.fetchrow(
            """
            SELECT c.*, fv.version AS firmware_version, fv.file_url AS firmware_url,
                   fv.checksum_sha256 AS firmware_checksum, fv.device_type AS firmware_device_type
            FROM ota_campaigns c
            JOIN firmware_versions fv ON fv.id = c.firmware_version_id
            WHERE c.id = $1 AND c.tenant_id = $2
            """,
            campaign_id,
            tenant_id,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Status breakdown
        status_counts = await conn.fetch(
            """
            SELECT status, COUNT(*)::int AS count
            FROM ota_device_status
            WHERE tenant_id = $1 AND campaign_id = $2
            GROUP BY status
            """,
            tenant_id,
            campaign_id,
        )

    breakdown = {r["status"]: r["count"] for r in status_counts}
    return {
        **dict(campaign),
        "status_breakdown": breakdown,
    }


@router.post("/ota/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        campaign = await conn.fetchrow(
            "SELECT id, status FROM ota_campaigns WHERE id = $1 AND tenant_id = $2",
            campaign_id,
            tenant_id,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign["status"] not in ("CREATED", "PAUSED"):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start campaign in status {campaign['status']}",
            )
        await conn.execute(
            """
            UPDATE ota_campaigns
            SET status = 'RUNNING', started_at = COALESCE(started_at, NOW())
            WHERE id = $1 AND tenant_id = $2
            """,
            campaign_id,
            tenant_id,
        )
    return {"id": campaign_id, "status": "RUNNING"}


@router.post("/ota/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        campaign = await conn.fetchrow(
            "SELECT id, status FROM ota_campaigns WHERE id = $1 AND tenant_id = $2",
            campaign_id,
            tenant_id,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign["status"] != "RUNNING":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause campaign in status {campaign['status']}",
            )
        await conn.execute(
            "UPDATE ota_campaigns SET status = 'PAUSED' WHERE id = $1 AND tenant_id = $2",
            campaign_id,
            tenant_id,
        )
    return {"id": campaign_id, "status": "PAUSED"}


@router.post("/ota/campaigns/{campaign_id}/abort")
async def abort_campaign(campaign_id: int, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        campaign = await conn.fetchrow(
            "SELECT id, status FROM ota_campaigns WHERE id = $1 AND tenant_id = $2",
            campaign_id,
            tenant_id,
        )
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign["status"] in ("COMPLETED", "ABORTED"):
            raise HTTPException(
                status_code=400,
                detail=f"Campaign already in terminal status {campaign['status']}",
            )

        # Mark all PENDING devices as SKIPPED
        await conn.execute(
            """
            UPDATE ota_device_status
            SET status = 'SKIPPED', completed_at = NOW()
            WHERE tenant_id = $1 AND campaign_id = $2 AND status = 'PENDING'
            """,
            tenant_id,
            campaign_id,
        )

        await conn.execute(
            """
            UPDATE ota_campaigns
            SET status = 'ABORTED', completed_at = NOW()
            WHERE id = $1 AND tenant_id = $2
            """,
            campaign_id,
            tenant_id,
        )
    return {"id": campaign_id, "status": "ABORTED"}


@router.get("/ota/campaigns/{campaign_id}/devices")
async def list_campaign_devices(
    campaign_id: int,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify campaign exists
        exists = await conn.fetchval(
            "SELECT 1 FROM ota_campaigns WHERE id = $1 AND tenant_id = $2",
            campaign_id,
            tenant_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Campaign not found")

        conditions = ["tenant_id = $1", "campaign_id = $2"]
        params: list[Any] = [tenant_id, campaign_id]
        if status:
            params.append(status.upper())
            conditions.append(f"status = ${len(params)}")
        where = " AND ".join(conditions)
        params.extend([limit, offset])

        rows = await conn.fetch(
            f"""
            SELECT device_id, status, progress_pct, error_message,
                   started_at, completed_at, created_at
            FROM ota_device_status
            WHERE {where}
            ORDER BY created_at ASC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM ota_device_status WHERE {' AND '.join(conditions[:len(conditions)])}",
            *params[:len(conditions)],
        )

    return {
        "campaign_id": campaign_id,
        "devices": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

---

## Step 5: Register the router in app.py

Edit file: `services/ui_iot/app.py`

Add the import alongside the other route imports (near line 45):

```python
from routes.ota import router as ota_router
```

Add the `include_router` call alongside the others (near line 186):

```python
app.include_router(ota_router)
```

---

## Verification

```bash
# 1. Apply migrations
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/081_firmware_versions.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/082_ota_campaigns.sql
docker exec -i iot-postgres psql -U iot -d iotcloud < db/migrations/083_ota_device_status.sql

# 2. Verify tables
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('firmware_versions','ota_campaigns','ota_device_status') ORDER BY table_name;"

# 3. Verify RLS is enabled
docker exec iot-postgres psql -U iot -d iotcloud -c "SELECT tablename, rowsecurity FROM pg_tables WHERE tablename IN ('firmware_versions','ota_campaigns','ota_device_status');"

# 4. Restart ui_iot and check for import errors
docker compose restart ui-iot
docker compose logs ui-iot --tail 20

# 5. Test firmware endpoint (with valid auth token)
curl -s http://localhost:8080/customer/firmware | python3 -m json.tool

# 6. Test campaign list endpoint
curl -s http://localhost:8080/customer/ota/campaigns | python3 -m json.tool
```
