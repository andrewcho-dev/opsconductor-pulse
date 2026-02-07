import os
import json
import hashlib
import secrets
from uuid import UUID
from datetime import datetime, timezone, timedelta

import asyncpg
import logging
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PG_HOST = os.getenv("PG_HOST", "iot-postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB   = os.getenv("PG_DB", "iotcloud")
PG_USER = os.getenv("PG_USER", "iot")
PG_PASS = os.getenv("PG_PASS", "iot_dev")

ADMIN_KEY = os.getenv("ADMIN_KEY", "change-me-now")
ACTIVATION_TTL_MINUTES = int(os.getenv("ACTIVATION_TTL_MINUTES", "60"))
app = FastAPI(title="IoT Provisioning API", version="0.1")

pool: asyncpg.Pool | None = None

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_config_json(value) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}

async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS,
            min_size=1, max_size=5
        )
    return pool

DDL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS device_registry (
  tenant_id            TEXT NOT NULL,
  device_id            TEXT NOT NULL,
  site_id              TEXT NOT NULL,
  status               TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE|REVOKED
  provisioned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  provision_token_hash TEXT NULL,
  device_pubkey        TEXT NULL,
  fw_version           TEXT NULL,
  metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (tenant_id, device_id)
);

ALTER TABLE device_registry
  ADD COLUMN IF NOT EXISTS provision_token_hash TEXT,
  ADD COLUMN IF NOT EXISTS device_pubkey TEXT,
  ADD COLUMN IF NOT EXISTS fw_version TEXT;

CREATE TABLE IF NOT EXISTS device_activation (
  tenant_id             TEXT NOT NULL,
  device_id             TEXT NOT NULL,
  activation_code_hash  TEXT NOT NULL,
  site_id               TEXT NOT NULL,
  expires_at            TIMESTAMPTZ NOT NULL,
  used_at               TIMESTAMPTZ NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, device_id, activation_code_hash)
);

CREATE INDEX IF NOT EXISTS device_activation_lookup_idx
  ON device_activation (tenant_id, device_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS device_token_history (
  tenant_id   TEXT NOT NULL,
  device_id   TEXT NOT NULL,
  token_hash  TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at  TIMESTAMPTZ NULL,
  reason      TEXT NULL
);

CREATE INDEX IF NOT EXISTS device_token_hist_idx
  ON device_token_history (tenant_id, device_id, created_at DESC);
"""

@app.on_event("startup")
async def startup():
    p = await get_pool()
    async with p.acquire() as conn:
        for stmt in DDL.strip().split(";"):
            s = stmt.strip()
            if s:
                await conn.execute(s + ";")

def require_admin(x_admin_key: str | None):
    if x_admin_key is None or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized (missing/invalid X-Admin-Key)")

# -------------------------
# Models
# -------------------------

class AdminCreateDevice(BaseModel):
    tenant_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    fw_version: str | None = None
    metadata: dict = Field(default_factory=dict)

class AdminCreateDeviceResponse(BaseModel):
    tenant_id: str
    device_id: str
    site_id: str
    activation_code: str
    expires_at: str

class DeviceActivateRequest(BaseModel):
    tenant_id: str
    device_id: str
    activation_code: str

class DeviceActivateResponse(BaseModel):
    tenant_id: str
    device_id: str
    provision_token: str

class AdminRotateTokenResponse(BaseModel):
    tenant_id: str
    device_id: str
    new_provision_token: str

class AdminCreateIntegration(BaseModel):
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    headers: dict = Field(default_factory=dict)
    enabled: bool = True

class AdminIntegrationResponse(BaseModel):
    tenant_id: str
    integration_id: str
    name: str
    type: str
    enabled: bool
    url: str
    created_at: str

class AdminCreateRoute(BaseModel):
    tenant_id: str = Field(min_length=1)
    integration_id: UUID
    name: str = Field(min_length=1)
    enabled: bool = True
    min_severity: int | None = None
    alert_types: list[str] | None = None
    site_ids: list[str] | None = None
    device_prefixes: list[str] | None = None
    deliver_on: list[str] | None = None
    priority: int = 100

class AdminRouteResponse(BaseModel):
    tenant_id: str
    route_id: str
    integration_id: str
    name: str
    enabled: bool
    min_severity: int | None
    alert_types: list[str] | None
    site_ids: list[str] | None
    device_prefixes: list[str] | None
    deliver_on: list[str]
    priority: int
    created_at: str

# -------------------------
# Admin endpoints
# -------------------------

@app.post("/api/admin/devices", response_model=AdminCreateDeviceResponse)
async def admin_create_device(payload: AdminCreateDevice, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)

    activation_code = secrets.token_urlsafe(18)
    activation_hash = sha256_hex(activation_code)
    expires_at = now_utc() + timedelta(minutes=ACTIVATION_TTL_MINUTES)

    p = await get_pool()
    async with p.acquire() as conn:
        # upsert device_registry
        await conn.execute(
            """
            INSERT INTO device_registry (tenant_id, device_id, site_id, status, fw_version, metadata)
            VALUES ($1,$2,$3,'ACTIVE',$4,$5::jsonb)
            ON CONFLICT (tenant_id, device_id)
            DO UPDATE SET
              site_id=EXCLUDED.site_id,
              status='ACTIVE',
              fw_version=COALESCE(EXCLUDED.fw_version, device_registry.fw_version),
              metadata=EXCLUDED.metadata
            """,
            payload.tenant_id, payload.device_id, payload.site_id, payload.fw_version, json.dumps(payload.metadata)
        )

        # insert activation record (multiple codes over time allowed)
        await conn.execute(
            """
            INSERT INTO device_activation (tenant_id, device_id, activation_code_hash, site_id, expires_at)
            VALUES ($1,$2,$3,$4,$5)
            """,
            payload.tenant_id, payload.device_id, activation_hash, payload.site_id, expires_at
        )

    return AdminCreateDeviceResponse(
        tenant_id=payload.tenant_id,
        device_id=payload.device_id,
        site_id=payload.site_id,
        activation_code=activation_code,
        expires_at=expires_at.isoformat()
    )

@app.get("/api/admin/devices")
async def admin_list_devices(
    x_admin_key: str | None = Header(default=None),
    tenant_id: str | None = Query(default=None),
    site_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    require_admin(x_admin_key)

    clauses = []
    args = []
    if tenant_id:
        clauses.append(f"tenant_id=${len(args)+1}")
        args.append(tenant_id)
    if site_id:
        clauses.append(f"site_id=${len(args)+1}")
        args.append(site_id)
    if status:
        clauses.append(f"status=${len(args)+1}")
        args.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    q = f"""
    SELECT tenant_id, device_id, site_id, status, provisioned_at, fw_version, (provision_token_hash IS NOT NULL) AS token_set
    FROM device_registry
    {where}
    ORDER BY tenant_id, site_id, device_id
    LIMIT {limit}
    """

    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(q, *args)
        return [dict(r) for r in rows]

@app.post("/api/admin/devices/{tenant_id}/{device_id}/revoke")
async def admin_revoke_device(tenant_id: str, device_id: str, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)

    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """
            UPDATE device_registry
            SET status='REVOKED'
            WHERE tenant_id=$1 AND device_id=$2
            """,
            tenant_id, device_id
        )
    return {"ok": True}

@app.post("/api/admin/devices/{tenant_id}/{device_id}/rotate-token", response_model=AdminRotateTokenResponse)
async def admin_rotate_token(tenant_id: str, device_id: str, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)

    new_token = "tok-" + secrets.token_urlsafe(24)
    token_hash = sha256_hex(new_token)

    p = await get_pool()
    async with p.acquire() as conn:
        # mark old token history as revoked (best-effort)
        await conn.execute(
            """
            UPDATE device_token_history
            SET revoked_at=now(), reason='ROTATED'
            WHERE tenant_id=$1 AND device_id=$2 AND revoked_at IS NULL
            """,
            tenant_id, device_id
        )
        # set new token hash
        await conn.execute(
            """
            UPDATE device_registry
            SET provision_token_hash=$3
            WHERE tenant_id=$1 AND device_id=$2
            """,
            tenant_id, device_id, token_hash
        )
        # record new history
        await conn.execute(
            """
            INSERT INTO device_token_history (tenant_id, device_id, token_hash)
            VALUES ($1,$2,$3)
            """,
            tenant_id, device_id, token_hash
        )

    return AdminRotateTokenResponse(tenant_id=tenant_id, device_id=device_id, new_provision_token=new_token)

@app.post("/api/admin/integrations", response_model=AdminIntegrationResponse)
async def admin_create_integration(payload: AdminCreateIntegration, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)

    url = payload.url.strip()
    headers = payload.headers or {}
    config = {"url": url, "headers": headers}

    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO integrations (tenant_id, name, type, enabled, config_json)
            VALUES ($1,$2,'webhook',$3,$4::jsonb)
            RETURNING tenant_id, integration_id, name, type, enabled, config_json, created_at
            """,
            payload.tenant_id,
            payload.name,
            payload.enabled,
            json.dumps(config)
        )

    cfg = normalize_config_json(row["config_json"])
    return AdminIntegrationResponse(
        tenant_id=row["tenant_id"],
        integration_id=str(row["integration_id"]),
        name=row["name"],
        type=row["type"],
        enabled=row["enabled"],
        url=cfg.get("url", ""),
        created_at=row["created_at"].isoformat()
    )

@app.get("/api/admin/integrations")
async def admin_list_integrations(
    x_admin_key: str | None = Header(default=None),
    tenant_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    require_admin(x_admin_key)

    clauses = []
    args = []
    if tenant_id:
        clauses.append(f"tenant_id=${len(args)+1}")
        args.append(tenant_id)
    if enabled is not None:
        clauses.append(f"enabled=${len(args)+1}")
        args.append(enabled)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    q = f"""
    SELECT tenant_id, integration_id, name, type, enabled, config_json, created_at
    FROM integrations
    {where}
    ORDER BY created_at DESC
    LIMIT {limit}
    """

    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(q, *args)

    output = []
    for row in rows:
        cfg = normalize_config_json(row["config_json"])
        output.append(
            {
                "tenant_id": row["tenant_id"],
                "integration_id": str(row["integration_id"]),
                "name": row["name"],
                "type": row["type"],
                "enabled": row["enabled"],
                "url": cfg.get("url", ""),
                "created_at": row["created_at"].isoformat(),
            }
        )

    return output

@app.post("/api/admin/integration-routes", response_model=AdminRouteResponse)
async def admin_create_route(payload: AdminCreateRoute, x_admin_key: str | None = Header(default=None)):
    require_admin(x_admin_key)

    deliver_on = payload.deliver_on or ["OPEN"]
    deliver_on = [d.upper() for d in deliver_on if isinstance(d, str)]
    deliver_on = [d for d in deliver_on if d == "OPEN"]
    if not deliver_on:
        deliver_on = ["OPEN"]

    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO integration_routes (
              tenant_id, integration_id, name, enabled, min_severity, alert_types,
              site_ids, device_prefixes, deliver_on, priority
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING tenant_id, route_id, integration_id, name, enabled, min_severity,
                      alert_types, site_ids, device_prefixes, deliver_on, priority, created_at
            """,
            payload.tenant_id,
            payload.integration_id,
            payload.name,
            payload.enabled,
            payload.min_severity,
            payload.alert_types,
            payload.site_ids,
            payload.device_prefixes,
            deliver_on,
            payload.priority,
        )

    return AdminRouteResponse(
        tenant_id=row["tenant_id"],
        route_id=str(row["route_id"]),
        integration_id=str(row["integration_id"]),
        name=row["name"],
        enabled=row["enabled"],
        min_severity=row["min_severity"],
        alert_types=row["alert_types"],
        site_ids=row["site_ids"],
        device_prefixes=row["device_prefixes"],
        deliver_on=row["deliver_on"],
        priority=row["priority"],
        created_at=row["created_at"].isoformat(),
    )

@app.get("/api/admin/integration-routes")
async def admin_list_routes(
    x_admin_key: str | None = Header(default=None),
    tenant_id: str | None = Query(default=None),
    integration_id: UUID | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
):
    require_admin(x_admin_key)

    clauses = []
    args = []
    if tenant_id:
        clauses.append(f"tenant_id=${len(args)+1}")
        args.append(tenant_id)
    if integration_id:
        clauses.append(f"integration_id=${len(args)+1}")
        args.append(integration_id)
    if enabled is not None:
        clauses.append(f"enabled=${len(args)+1}")
        args.append(enabled)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    q = f"""
    SELECT tenant_id, route_id, integration_id, name, enabled, min_severity,
           alert_types, site_ids, device_prefixes, deliver_on, priority, created_at
    FROM integration_routes
    {where}
    ORDER BY priority ASC, created_at DESC
    LIMIT {limit}
    """

    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(q, *args)

    output = []
    for row in rows:
        output.append(
            {
                "tenant_id": row["tenant_id"],
                "route_id": str(row["route_id"]),
                "integration_id": str(row["integration_id"]),
                "name": row["name"],
                "enabled": row["enabled"],
                "min_severity": row["min_severity"],
                "alert_types": row["alert_types"],
                "site_ids": row["site_ids"],
                "device_prefixes": row["device_prefixes"],
                "deliver_on": row["deliver_on"],
                "priority": row["priority"],
                "created_at": row["created_at"].isoformat(),
            }
        )

    return output

# -------------------------
# Device-facing endpoint
# -------------------------

@app.post("/api/device/activate", response_model=DeviceActivateResponse)
async def device_activate(payload: DeviceActivateRequest):
    activation_hash = sha256_hex(payload.activation_code)

    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT tenant_id, device_id, site_id, expires_at, used_at
            FROM device_activation
            WHERE tenant_id=$1 AND device_id=$2 AND activation_code_hash=$3
            """,
            payload.tenant_id, payload.device_id, activation_hash
        )

        if row is None:
            raise HTTPException(status_code=400, detail="Invalid activation code")

        if row["used_at"] is not None:
            raise HTTPException(status_code=400, detail="Activation code already used")

        if now_utc() > row["expires_at"]:
            raise HTTPException(status_code=400, detail="Activation code expired")

        # issue new provision token
        token = "tok-" + secrets.token_urlsafe(24)
        token_hash = sha256_hex(token)

        # set in registry + mark activation used + record history
        await conn.execute(
            """
            UPDATE device_registry
            SET provision_token_hash=$3, status='ACTIVE'
            WHERE tenant_id=$1 AND device_id=$2
            """,
            payload.tenant_id, payload.device_id, token_hash
        )
        await conn.execute(
            """
            UPDATE device_activation
            SET used_at=now()
            WHERE tenant_id=$1 AND device_id=$2 AND activation_code_hash=$3
            """,
            payload.tenant_id, payload.device_id, activation_hash
        )
        await conn.execute(
            """
            INSERT INTO device_token_history (tenant_id, device_id, token_hash)
            VALUES ($1,$2,$3)
            """,
            payload.tenant_id, payload.device_id, token_hash
        )

    return DeviceActivateResponse(tenant_id=payload.tenant_id, device_id=payload.device_id, provision_token=token)
