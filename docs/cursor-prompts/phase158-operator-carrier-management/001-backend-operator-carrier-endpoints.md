# Task 1: Backend — Operator Carrier Endpoints

## File to Modify

`services/ui_iot/routes/operator.py`

## What to Do

Add 4 new endpoints at the end of the file (before the final line), following the exact patterns already established in this file. Also add a `_mask_carrier_secret` helper near the top of the file (after the existing imports and models).

### Step 1: Add helper function

After the last Pydantic model definition and before the first `@router` decorator, add:

```python
def _mask_carrier_secret(value) -> str | None:
    """Mask a carrier API key for safe display."""
    if not value:
        return None
    v = str(value)
    if len(v) <= 4:
        return "****"
    return f"...{v[-4:]}"
```

### Step 2: Add Pydantic models

After the existing model definitions (near the other `BaseModel` classes), add:

```python
class OperatorCarrierIntegrationCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    carrier_name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True
    api_key: str | None = None
    api_secret: str | None = None
    api_base_url: str | None = None
    account_id: str | None = None
    sync_enabled: bool = True
    sync_interval_minutes: int = Field(default=60, ge=5, le=1440)
    config: dict = Field(default_factory=dict)
```

No separate update model needed — reuse `CarrierIntegrationUpdate` from `carrier.py` by importing it, OR define a minimal one inline:

```python
class OperatorCarrierIntegrationUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None
    api_key: str | None = None
    api_secret: str | None = None
    api_base_url: str | None = None
    account_id: str | None = None
    sync_enabled: bool | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    config: dict | None = None
```

### Step 3: Add the 4 endpoints

Add these at the end of the file, before any closing code.

#### Endpoint 1: GET /carrier-integrations

```python
@router.get("/carrier-integrations")
async def operator_list_carrier_integrations(
    request: Request,
    tenant_id: str | None = Query(None),
    carrier_name: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    conditions = []
    params = []
    idx = 1

    if tenant_id:
        conditions.append(f"tenant_id = ${idx}")
        params.append(tenant_id)
        idx += 1
    if carrier_name:
        conditions.append(f"carrier_name = ${idx}")
        params.append(carrier_name)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with operator_connection(pool) as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, tenant_id, carrier_name, display_name, enabled,
                   account_id, api_key, sync_enabled, sync_interval_minutes,
                   last_sync_at, last_sync_status, last_sync_error, created_at
            FROM carrier_integrations
            {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, limit, offset,
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM carrier_integrations {where}",
            *params,
        )

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="list_carrier_integrations",
            tenant_filter=tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "integrations": [
            {
                "id": r["id"],
                "tenant_id": r["tenant_id"],
                "carrier_name": r["carrier_name"],
                "display_name": r["display_name"],
                "enabled": r["enabled"],
                "account_id": r["account_id"],
                "api_key_masked": _mask_carrier_secret(r["api_key"]),
                "sync_enabled": r["sync_enabled"],
                "sync_interval_minutes": r["sync_interval_minutes"],
                "last_sync_at": r["last_sync_at"],
                "last_sync_status": r["last_sync_status"],
                "last_sync_error": r["last_sync_error"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

#### Endpoint 2: POST /carrier-integrations

```python
@router.post("/carrier-integrations", status_code=201)
async def operator_create_carrier_integration(
    data: OperatorCarrierIntegrationCreate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    try:
        async with operator_connection(pool) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO carrier_integrations
                    (tenant_id, carrier_name, display_name, enabled,
                     api_key, api_secret, api_base_url, account_id,
                     config, sync_enabled, sync_interval_minutes)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11)
                RETURNING id, tenant_id, carrier_name, display_name, enabled,
                          account_id, sync_enabled, sync_interval_minutes,
                          last_sync_at, last_sync_status, last_sync_error,
                          api_key, created_at
                """,
                data.tenant_id, data.carrier_name, data.display_name, data.enabled,
                data.api_key, data.api_secret, data.api_base_url, data.account_id,
                json.dumps(data.config), data.sync_enabled, data.sync_interval_minutes,
            )
    except Exception:
        logger.exception("Failed to create carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="create_carrier_integration",
            tenant_filter=data.tenant_id,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "carrier_name": row["carrier_name"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
        "account_id": row["account_id"],
        "api_key_masked": _mask_carrier_secret(row["api_key"]),
        "sync_enabled": row["sync_enabled"],
        "sync_interval_minutes": row["sync_interval_minutes"],
        "last_sync_at": row["last_sync_at"],
        "last_sync_status": row["last_sync_status"],
        "last_sync_error": row["last_sync_error"],
        "created_at": row["created_at"],
    }
```

#### Endpoint 3: PUT /carrier-integrations/{integration_id}

```python
@router.put("/carrier-integrations/{integration_id}")
async def operator_update_carrier_integration(
    integration_id: int,
    data: OperatorCarrierIntegrationUpdate,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    sets: list[str] = []
    params: list = [integration_id]
    idx = 2

    def add_set(col: str, val):
        nonlocal idx
        sets.append(f"{col} = ${idx}")
        params.append(val)
        idx += 1

    if data.display_name is not None:   add_set("display_name", data.display_name)
    if data.enabled is not None:        add_set("enabled", data.enabled)
    if data.api_key is not None:        add_set("api_key", data.api_key)
    if data.api_secret is not None:     add_set("api_secret", data.api_secret)
    if data.api_base_url is not None:   add_set("api_base_url", data.api_base_url)
    if data.account_id is not None:     add_set("account_id", data.account_id)
    if data.sync_enabled is not None:   add_set("sync_enabled", data.sync_enabled)
    if data.sync_interval_minutes is not None: add_set("sync_interval_minutes", data.sync_interval_minutes)
    if data.config is not None:
        sets.append(f"config = ${idx}::jsonb")
        params.append(json.dumps(data.config))
        idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets.append("updated_at = now()")

    try:
        async with operator_connection(pool) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE carrier_integrations
                SET {", ".join(sets)}
                WHERE id = $1
                RETURNING id, tenant_id, carrier_name, display_name, enabled,
                          account_id, sync_enabled, sync_interval_minutes,
                          last_sync_at, last_sync_status, last_sync_error,
                          api_key, created_at
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="update_carrier_integration",
            tenant_filter=str(row["tenant_id"]),
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "carrier_name": row["carrier_name"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
        "account_id": row["account_id"],
        "api_key_masked": _mask_carrier_secret(row["api_key"]),
        "sync_enabled": row["sync_enabled"],
        "sync_interval_minutes": row["sync_interval_minutes"],
        "last_sync_at": row["last_sync_at"],
        "last_sync_status": row["last_sync_status"],
        "last_sync_error": row["last_sync_error"],
        "created_at": row["created_at"],
    }
```

#### Endpoint 4: DELETE /carrier-integrations/{integration_id}

```python
@router.delete("/carrier-integrations/{integration_id}")
async def operator_delete_carrier_integration(
    integration_id: int,
    request: Request,
    _: None = Depends(require_operator_admin),
):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = await get_pool()

    try:
        async with operator_connection(pool) as conn:
            async with conn.transaction():
                # Unlink devices first
                try:
                    await conn.execute(
                        """
                        UPDATE device_connections
                        SET carrier_integration_id = NULL, updated_at = now()
                        WHERE carrier_integration_id = $1
                        """,
                        integration_id,
                    )
                except asyncpg.UndefinedColumnError:
                    raise HTTPException(
                        status_code=400,
                        detail="carrier link columns not available; apply migration 106 first",
                    )

                deleted = await conn.fetchval(
                    "DELETE FROM carrier_integrations WHERE id = $1 RETURNING 1",
                    integration_id,
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to delete carrier integration")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")

    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="delete_carrier_integration",
            tenant_filter=None,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True,
        )

    return {"deleted": True, "id": integration_id}
```

## Important Notes

- The `operator_connection(pool)` context manager bypasses RLS — that's the whole point: operators see all tenants.
- The DELETE endpoint does NOT scope by `tenant_id` in its WHERE clause (unlike the customer version). It uses `WHERE id = $1` since operators manage all tenants.
- The DELETE unlinks `device_connections` rows without tenant scoping (all rows for that integration, which by definition belong to one tenant via the integration's own `tenant_id`).
- The `_mask_carrier_secret` helper mirrors `_mask_secret` from `carrier.py` — we define our own copy to avoid cross-module import coupling.
- `asyncpg` is already imported at the top of `operator.py`.
- `json` is already imported at the top of `operator.py`.
- `get_pool` is the local alias for the DB pool (check the file — it may be `get_db_pool` from dependencies or a local wrapper).

## Verification

```bash
cd services/ui_iot && python -c "
from routes.operator import router
routes = [(r.path, r.methods) for r in router.routes]
carrier_routes = [r for r in routes if 'carrier' in r[0]]
print('Operator carrier routes:', carrier_routes)
assert len(carrier_routes) >= 3
print('OK')
"
```
