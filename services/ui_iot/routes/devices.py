"""Device management routes - CRUD, tokens, uptime, tags, groups, maintenance windows."""

from routes.customer import *  # noqa: F401,F403
from routes.customer import _normalize_optional_ids
from routes.customer import _normalize_tags
from middleware.permissions import require_permission
from typing import Any, Optional

from shared.logging import get_logger
from shared.twin import compute_delta, sync_status

router = APIRouter(
    prefix="/customer",
    tags=["devices"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

twin_logger = get_logger("pulse.twin")
commands_logger = get_logger("pulse.commands")


class TwinDesiredUpdate(BaseModel):
    desired: dict[str, Any]


class TwinResponse(BaseModel):
    device_id: str
    desired: dict[str, Any]
    reported: dict[str, Any]
    delta: dict[str, Any]
    desired_version: int
    reported_version: int
    sync_status: str
    shadow_updated_at: str | None


class CommandCreate(BaseModel):
    command_type: str = Field(..., min_length=1, max_length=100)
    command_params: dict[str, Any] = Field(default_factory=dict)
    expires_in_minutes: int = Field(default=60, ge=1, le=10080)


async def _publish_shadow_desired(
    tenant_id: str, device_id: str, desired: dict[str, Any], desired_version: int
) -> None:
    topic = f"tenant/{tenant_id}/device/{device_id}/shadow/desired"
    payload = json.dumps(
        {
            "desired": desired,
            "version": desired_version,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )
    result = await publish_alert(
        topic=topic,
        payload=payload,
        qos=1,
        retain=True,
    )
    if result.success:
        twin_logger.info(
            "shadow_desired_published",
            extra={"device_id": device_id, "version": desired_version},
        )
        return
    twin_logger.warning(
        "shadow_desired_publish_failed",
        extra={"device_id": device_id, "error": result.error or "unknown_error"},
    )


async def _clear_shadow_desired_retained(tenant_id: str, device_id: str) -> None:
    topic = f"tenant/{tenant_id}/device/{device_id}/shadow/desired"
    result = await publish_alert(
        topic=topic,
        payload="",
        qos=1,
        retain=True,
    )
    if not result.success:
        twin_logger.warning(
            "shadow_clear_failed",
            extra={"device_id": device_id, "error": result.error or "unknown_error"},
        )


def _jsonb_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}

@router.post(
    "/devices",
    status_code=201,
    dependencies=[require_permission("devices.create")],
)
async def create_device(device: DeviceCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        subscription_id = device.subscription_id
        if not subscription_id:
            sub = await conn.fetchrow(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE tenant_id = $1
                  AND subscription_type = 'MAIN'
                  AND status = 'ACTIVE'
                  AND active_device_count < device_limit
                ORDER BY created_at
                LIMIT 1
                """,
                tenant_id,
            )
            if not sub:
                raise HTTPException(403, "No MAIN subscription with available capacity")
            subscription_id = sub["subscription_id"]

        try:
            await create_device_on_subscription(
                conn,
                tenant_id,
                device.device_id,
                device.site_id,
                subscription_id,
                actor_id=user.get("sub") if user else None,
            )
        except ValueError as exc:
            message = str(exc)
            status_code = 403 if "limit" in message.lower() else 400
            raise HTTPException(status_code, message)

    return {
        "device_id": device.device_id,
        "subscription_id": subscription_id,
        "status": "created",
    }


@router.get("/devices/{device_id}/tokens")
async def list_device_tokens(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")
            rows = await conn.fetch(
                """
                SELECT id, client_id, label, created_at, revoked_at
                FROM device_api_tokens
                WHERE tenant_id = $1 AND device_id = $2 AND revoked_at IS NULL
                ORDER BY created_at DESC
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to list device tokens")
        raise HTTPException(status_code=500, detail="Internal server error")

    tokens = []
    for row in rows:
        token = dict(row)
        if token.get("revoked_at") is not None:
            continue
        token["id"] = str(token["id"])
        tokens.append(token)
    return {"device_id": device_id, "tokens": tokens, "total": len(tokens)}


@router.delete(
    "/devices/{device_id}/tokens/{token_id}",
    status_code=204,
    dependencies=[require_permission("devices.tokens.revoke")],
)
async def revoke_device_token(device_id: str, token_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE device_api_tokens
                SET revoked_at = now()
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND id = $3::uuid
                  AND revoked_at IS NULL
                RETURNING id
                """,
                tenant_id,
                device_id,
                token_id,
            )
    except Exception:
        logger.exception("Failed to revoke device token")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    return Response(status_code=204)


@router.post(
    "/devices/{device_id}/tokens/rotate",
    status_code=201,
    dependencies=[require_permission("devices.tokens.rotate")],
)
async def rotate_device_token(
    device_id: str,
    body: TokenRotateRequest,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE device_api_tokens
                    SET revoked_at = now()
                    WHERE tenant_id = $1 AND device_id = $2 AND revoked_at IS NULL
                    """,
                    tenant_id,
                    device_id,
                )

                client_id = f"{tenant_id[:8]}-{device_id[:8]}-{uuid.uuid4().hex[:8]}"
                password = secrets.token_urlsafe(32)
                token_hash = bcrypt.hash(password)
                await conn.execute(
                    """
                    INSERT INTO device_api_tokens (tenant_id, device_id, client_id, token_hash, label)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    tenant_id,
                    device_id,
                    client_id,
                    token_hash,
                    body.label.strip() or "rotated",
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to rotate device token")
        raise HTTPException(status_code=500, detail="Internal server error")

    broker_url = os.environ.get("MQTT_BROKER_URL", "mqtt://localhost:1883")
    return {"client_id": client_id, "password": password, "broker_url": broker_url}


@router.post(
    "/devices/import",
    dependencies=[require_permission("devices.import")],
)
async def import_devices_csv(file: UploadFile = File(...), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()
    raw = await file.read()
    if len(raw) > 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 1 MB)")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    required_columns = {"name", "device_type"}
    if not required_columns.issubset(set(headers)):
        raise HTTPException(status_code=400, detail="Missing required CSV columns: name, device_type")

    rows = list(reader)
    if len(rows) > 500:
        raise HTTPException(status_code=400, detail="CSV row limit exceeded (max 500)")

    results: list[dict] = []
    imported = 0
    failed = 0

    async with tenant_connection(pool, tenant_id) as conn:
        for idx, row in enumerate(rows, start=1):
            name = (row.get("name") or "").strip()
            device_type = (row.get("device_type") or "").strip().lower()
            site_id = (row.get("site_id") or "").strip() or "default-site"
            tags_value = (row.get("tags") or "").strip()
            tags = _normalize_tags(tags_value.split(",")) if tags_value else []

            if not name:
                failed += 1
                results.append(
                    {"row": idx, "name": name, "status": "error", "message": "name is required"}
                )
                continue
            if device_type not in SUPPORTED_DEVICE_TYPES:
                failed += 1
                results.append(
                    {
                        "row": idx,
                        "name": name,
                        "status": "error",
                        "message": f"unsupported device_type: {device_type}",
                    }
                )
                continue

            subscription_id = await conn.fetchval(
                """
                SELECT subscription_id
                FROM subscriptions
                WHERE tenant_id = $1
                  AND subscription_type = 'MAIN'
                  AND status = 'ACTIVE'
                  AND active_device_count < device_limit
                ORDER BY created_at
                LIMIT 1
                """,
                tenant_id,
            )
            if not subscription_id:
                failed += 1
                results.append(
                    {
                        "row": idx,
                        "name": name,
                        "status": "error",
                        "message": "No active subscription capacity",
                    }
                )
                continue

            base_id = re.sub(r"[^A-Za-z0-9-]+", "-", name).strip("-").upper() or "DEVICE"
            device_id = f"{base_id}-{uuid.uuid4().hex[:6]}"
            try:
                async with conn.transaction():
                    await create_device_on_subscription(
                        conn,
                        tenant_id,
                        device_id,
                        site_id,
                        subscription_id,
                        actor_id=user.get("sub") if user else None,
                    )

                    if tags:
                        await conn.executemany(
                            """
                            INSERT INTO device_tags (tenant_id, device_id, tag)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                            """,
                            [(tenant_id, device_id, tag) for tag in tags],
                        )

                    client_id = f"{tenant_id[:8]}-{device_id[:8]}-{uuid.uuid4().hex[:8]}"
                    password = secrets.token_urlsafe(32)
                    await conn.execute(
                        """
                        INSERT INTO device_api_tokens (tenant_id, device_id, client_id, token_hash, label)
                        VALUES ($1, $2, $3, $4, 'default')
                        """,
                        tenant_id,
                        device_id,
                        client_id,
                        bcrypt.hash(password),
                    )
            except Exception as exc:
                failed += 1
                results.append(
                    {"row": idx, "name": name, "status": "error", "message": str(exc)}
                )
                continue

            imported += 1
            results.append({"row": idx, "name": name, "status": "ok", "device_id": device_id})

    return {
        "total": len(rows),
        "imported": imported,
        "failed": failed,
        "results": results,
    }


@router.get("/devices/{device_id}/uptime")
async def get_device_uptime(
    device_id: str,
    range: Literal["24h", "7d", "30d"] = Query("24h"),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    range_seconds = UPTIME_RANGES_SECONDS[range]
    range_start = datetime.now(timezone.utc) - timedelta(seconds=range_seconds)
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(
                    EXTRACT(EPOCH FROM (LEAST(COALESCE(closed_at, now()), now()) - GREATEST(created_at, $3)))
                ), 0) AS offline_seconds
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND alert_type = 'NO_TELEMETRY'
                  AND created_at < now()
                  AND COALESCE(closed_at, now()) > $3
                """,
                tenant_id,
                device_id,
                range_start,
            )
            is_offline = await conn.fetchval(
                """
                SELECT 1
                FROM fleet_alert
                WHERE tenant_id = $1
                  AND device_id = $2
                  AND alert_type = 'NO_TELEMETRY'
                  AND status = 'OPEN'
                LIMIT 1
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to compute device uptime")
        raise HTTPException(status_code=500, detail="Internal server error")

    offline_seconds = max(0, int(float(row["offline_seconds"] or 0)))
    offline_seconds = min(offline_seconds, range_seconds)
    uptime_pct = round(((range_seconds - offline_seconds) / range_seconds) * 100, 1)
    return {
        "device_id": device_id,
        "range": range,
        "uptime_pct": uptime_pct,
        "offline_seconds": offline_seconds,
        "range_seconds": range_seconds,
        "status": "offline" if is_offline else "online",
    }


@router.get("/fleet/uptime-summary")
async def get_fleet_uptime_summary(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    range_seconds = UPTIME_RANGES_SECONDS["24h"]
    range_start = datetime.now(timezone.utc) - timedelta(seconds=range_seconds)
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            counts = await conn.fetchrow(
                """
                WITH open_gap AS (
                    SELECT DISTINCT device_id
                    FROM fleet_alert
                    WHERE tenant_id = $1
                      AND alert_type = 'NO_TELEMETRY'
                      AND status = 'OPEN'
                )
                SELECT
                    COUNT(*) AS total_devices,
                    COUNT(*) FILTER (WHERE og.device_id IS NULL) AS online,
                    COUNT(*) FILTER (WHERE og.device_id IS NOT NULL) AS offline
                FROM device_registry dr
                LEFT JOIN open_gap og
                  ON og.device_id = dr.device_id
                WHERE dr.tenant_id = $1
                """,
                tenant_id,
            )
            avg_row = await conn.fetchrow(
                """
                WITH device_offline AS (
                    SELECT
                        dr.device_id,
                        COALESCE(SUM(
                            EXTRACT(EPOCH FROM (
                                LEAST(COALESCE(fa.closed_at, now()), now()) - GREATEST(fa.created_at, $2)
                            ))
                        ), 0) AS offline_seconds
                    FROM device_registry dr
                    LEFT JOIN fleet_alert fa
                      ON fa.tenant_id = dr.tenant_id
                     AND fa.device_id = dr.device_id
                     AND fa.alert_type = 'NO_TELEMETRY'
                     AND fa.created_at < now()
                     AND COALESCE(fa.closed_at, now()) > $2
                    WHERE dr.tenant_id = $1
                    GROUP BY dr.device_id
                )
                SELECT COALESCE(AVG(
                    (( $3 - LEAST(offline_seconds, $3) ) / $3::numeric) * 100
                ), 100) AS avg_uptime_pct
                FROM device_offline
                """,
                tenant_id,
                range_start,
                range_seconds,
            )
    except Exception:
        logger.exception("Failed to compute fleet uptime summary")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "total_devices": int(counts["total_devices"] or 0),
        "online": int(counts["online"] or 0),
        "offline": int(counts["offline"] or 0),
        "avg_uptime_pct": round(float(avg_row["avg_uptime_pct"] or 100), 1),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/devices")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_devices(
    request: Request,
    response: Response,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    tags: str | None = Query(None),
    tag: str | None = Query(None, description="Filter by a single tag"),
    q: str | None = Query(None, max_length=100),
    site_id: str | None = Query(None),
    include_decommissioned: bool = Query(False),
    pool=Depends(get_db_pool),
):
    if status is not None and status.upper() not in VALID_DEVICE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status value")
    status = status.upper() if status else None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    if tag:
        tag_list = list(dict.fromkeys((tag_list or []) + [tag.strip()]))
    if search and not q:
        q = search

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            result = await fetch_devices_v2(
                conn,
                tenant_id,
                limit=limit,
                offset=offset,
                status=status,
                tags=tag_list,
                q=q,
                site_id=site_id,
                include_decommissioned=include_decommissioned,
            )
            devices = result["devices"]
            if devices:
                device_ids = [device["device_id"] for device in devices]
                rows = await conn.fetch(
                    """
                    SELECT
                        d.device_id,
                        d.subscription_id,
                        s.subscription_type,
                        s.status as subscription_status
                    FROM device_registry d
                    LEFT JOIN subscriptions s ON d.subscription_id = s.subscription_id
                    WHERE d.tenant_id = $1 AND d.device_id = ANY($2::text[])
                    """,
                    tenant_id,
                    device_ids,
                )
                subscription_map = {row["device_id"]: dict(row) for row in rows}
                for device in devices:
                    subscription = subscription_map.get(device["device_id"])
                    if subscription:
                        device["subscription_id"] = subscription["subscription_id"]
                        device["subscription_type"] = subscription["subscription_type"]
                        device["subscription_status"] = subscription["subscription_status"]
    except Exception:
        logger.exception("Failed to fetch tenant devices")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "devices": devices,
        "total": result["total"],
        "limit": limit,
        "offset": offset,
    }


@router.get("/devices/summary")
async def get_fleet_summary(pool=Depends(get_db_pool)):
    """Fleet status summary: counts of ONLINE/STALE/OFFLINE devices."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            summary = await fetch_fleet_summary(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch fleet summary")
        raise HTTPException(status_code=500, detail="Internal server error")
    return summary


@router.delete(
    "/devices/{device_id}",
    dependencies=[require_permission("devices.delete")],
)
async def delete_device(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()

    p = pool
    async with tenant_connection(p, tenant_id) as conn:
        device = await conn.fetchrow(
            """
            SELECT subscription_id
            FROM device_registry
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
        if not device:
            raise HTTPException(404, "Device not found")

        async with conn.transaction():
            await conn.execute(
                """
                UPDATE device_registry
                SET status = 'DELETED'
                WHERE tenant_id = $1 AND device_id = $2
                """,
                tenant_id,
                device_id,
            )

            subscription_id = device["subscription_id"]
            if subscription_id:
                await conn.execute(
                    """
                    UPDATE subscriptions
                    SET active_device_count = GREATEST(0, active_device_count - 1), updated_at = now()
                    WHERE subscription_id = $1
                    """,
                    subscription_id,
                )

            await log_subscription_event(
                conn,
                tenant_id,
                event_type="DEVICE_REMOVED",
                actor_type="user",
                actor_id=user.get("sub") if user else None,
                details={"device_id": device_id, "subscription_id": subscription_id},
            )

    return {"device_id": device_id, "status": "deleted"}


@router.get("/devices/{device_id}")
async def get_device_detail(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            events = await fetch_device_events(conn, tenant_id, device_id, hours=24, limit=50)
            telemetry = await fetch_device_telemetry(conn, tenant_id, device_id, hours=6, limit=120)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch tenant device detail")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "device": device,
        "events": events,
        "telemetry": telemetry,
    }


@router.get("/devices/{device_id}/telemetry/history", dependencies=[Depends(require_customer)])
async def get_telemetry_history(
    device_id: str,
    metric: str = Query(...),
    range: str = Query("24h"),
    pool=Depends(get_db_pool),
):
    if range not in VALID_TELEMETRY_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid range. Must be one of: {list(VALID_TELEMETRY_RANGES.keys())}",
        )

    tenant_id = get_tenant_id()
    lookback, bucket = VALID_TELEMETRY_RANGES[range]

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                time_bucket($1::interval, time) AS bucket,
                AVG((metrics->>$2)::numeric) AS avg_val,
                MIN((metrics->>$2)::numeric) AS min_val,
                MAX((metrics->>$2)::numeric) AS max_val,
                COUNT(*) AS sample_count
            FROM telemetry
            WHERE tenant_id = $3
              AND device_id = $4
              AND time > now() - $5::interval
              AND metrics ? $2
            GROUP BY bucket
            ORDER BY bucket ASC
            """,
            bucket,
            metric,
            tenant_id,
            device_id,
            lookback,
        )

    return {
        "device_id": device_id,
        "metric": metric,
        "range": range,
        "bucket_size": bucket,
        "points": [
            {
                "time": row["bucket"].isoformat(),
                "avg": float(row["avg_val"]) if row["avg_val"] is not None else None,
                "min": float(row["min_val"]) if row["min_val"] is not None else None,
                "max": float(row["max_val"]) if row["max_val"] is not None else None,
                "count": row["sample_count"],
            }
            for row in rows
        ],
    }


@router.get("/devices/{device_id}/telemetry/export", dependencies=[Depends(require_customer)])
async def export_telemetry_csv(
    device_id: str,
    range: str = Query("24h"),
    limit: int = Query(5000, ge=1, le=10000),
    pool=Depends(get_db_pool),
):
    if range not in EXPORT_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid range. Must be one of: {list(EXPORT_RANGES.keys())}",
        )

    tenant_id = get_tenant_id()
    lookback = EXPORT_RANGES[range]
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT time, device_id, site_id, seq, metrics
            FROM telemetry
            WHERE tenant_id = $1
              AND device_id = $2
              AND time > now() - $3::interval
            ORDER BY time ASC
            LIMIT $4
            """,
            tenant_id,
            device_id,
            lookback,
            limit,
        )

    output = io.StringIO()
    writer = csv.writer(output)
    if not rows:
        writer.writerow(["time", "device_id", "site_id", "seq"])
    else:
        metric_keys = sorted(
            {
                key
                for row in rows
                for key in ((row["metrics"] or {}).keys())
            }
        )
        headers = ["time", "device_id", "site_id", "seq", *metric_keys]
        writer.writerow(headers)
        for row in rows:
            metrics = row["metrics"] or {}
            writer.writerow(
                [
                    row["time"].isoformat(),
                    row["device_id"],
                    row["site_id"] or "",
                    row["seq"],
                    *[metrics.get(k, "") for k in metric_keys],
                ]
            )
    output.seek(0)
    filename = f"{device_id}_telemetry_{range}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.patch(
    "/devices/{device_id}",
    dependencies=[require_permission("devices.update")],
)
async def update_device(device_id: str, body: DeviceUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided")

    tags_update = update_data.pop("tags", None)
    if "name" in update_data:
        update_data["model"] = update_data.pop("name")

    if update_data.get("address") and not (
        update_data.get("latitude") is not None and update_data.get("longitude") is not None
    ):
        coords = await geocode_address(update_data["address"])
        if coords:
            update_data["latitude"], update_data["longitude"] = coords

    if any(key in update_data for key in ("latitude", "longitude", "address")):
        update_data["location_source"] = "manual"

    fields = [
        "site_id",
        "latitude",
        "longitude",
        "address",
        "location_source",
        "mac_address",
        "imei",
        "iccid",
        "serial_number",
        "model",
        "manufacturer",
        "hw_revision",
        "fw_version",
        "notes",
    ]
    allowed_fields = set(fields)
    unknown_fields = [
        key for key, value in update_data.items()
        if value is not None and key not in allowed_fields
    ]
    if unknown_fields:
        raise HTTPException(status_code=400, detail="Invalid fields provided")

    sets: list[str] = []
    params: list[object] = [tenant_id, device_id]
    idx = 3

    for field in fields:
        if field in update_data:
            sets.append(f"{field} = ${idx}")
            params.append(update_data[field])
            idx += 1

    if not sets:
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    f"""
                    UPDATE device_registry
                    SET {", ".join(sets)}
                    WHERE tenant_id = $1 AND device_id = $2
                    RETURNING tenant_id, device_id
                    """,
                    *params,
                )
                if not row:
                    raise HTTPException(status_code=404, detail="Device not found")

                if tags_update is not None:
                    normalized_tags = _normalize_tags(tags_update)
                    await conn.execute(
                        "DELETE FROM device_tags WHERE tenant_id = $1 AND device_id = $2",
                        tenant_id,
                        device_id,
                    )
                    if normalized_tags:
                        await conn.executemany(
                            """
                            INSERT INTO device_tags (tenant_id, device_id, tag)
                            VALUES ($1, $2, $3)
                            ON CONFLICT DO NOTHING
                            """,
                            [(tenant_id, device_id, tag) for tag in normalized_tags],
                        )

            device = await fetch_device(conn, tenant_id, device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device attributes")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device": device}


@router.patch(
    "/devices/{device_id}/decommission",
    dependencies=[require_permission("devices.decommission")],
)
async def decommission_device(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE device_registry
                SET decommissioned_at = now(), status = 'REVOKED'
                WHERE tenant_id = $1 AND device_id = $2 AND decommissioned_at IS NULL
                RETURNING device_id, decommissioned_at
                """,
                tenant_id,
                device_id,
            )
    except Exception:
        logger.exception("Failed to decommission device")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Device not found or already decommissioned")
    await _clear_shadow_desired_retained(tenant_id, device_id)
    return {"device_id": row["device_id"], "decommissioned_at": row["decommissioned_at"].isoformat()}


@router.get("/devices/{device_id}/twin", response_model=TwinResponse)
async def get_device_twin(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT
              device_id,
              desired_state,
              reported_state,
              desired_version,
              reported_version,
              shadow_updated_at,
              last_seen_at AS last_seen
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    desired = _jsonb_to_dict(row["desired_state"])
    reported = _jsonb_to_dict(row["reported_state"])
    shadow_updated_at = row["shadow_updated_at"]
    return {
        "device_id": device_id,
        "desired": desired,
        "reported": reported,
        "delta": compute_delta(desired, reported),
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
        "sync_status": sync_status(
            row["desired_version"],
            row["reported_version"],
            row["last_seen"],
        ),
        "shadow_updated_at": shadow_updated_at.isoformat() if shadow_updated_at else None,
    }


@router.patch(
    "/devices/{device_id}/twin/desired",
    dependencies=[require_permission("devices.twin.write")],
)
async def update_desired_state(
    device_id: str, body: TwinDesiredUpdate, pool=Depends(get_db_pool)
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE device_state
            SET desired_state = $1::jsonb,
                desired_version = desired_version + 1,
                shadow_updated_at = NOW()
            WHERE tenant_id = $2 AND device_id = $3
            RETURNING device_id, desired_state, desired_version
            """,
            json.dumps(body.desired),
            tenant_id,
            device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    await _publish_shadow_desired(
        tenant_id,
        device_id,
        _jsonb_to_dict(row["desired_state"]),
        row["desired_version"],
    )
    return {
        "device_id": device_id,
        "desired": _jsonb_to_dict(row["desired_state"]),
        "desired_version": row["desired_version"],
    }


@router.get("/devices/{device_id}/twin/delta")
async def get_twin_delta(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT desired_state, reported_state, desired_version, reported_version
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    delta = compute_delta(_jsonb_to_dict(row["desired_state"]), _jsonb_to_dict(row["reported_state"]))
    return {
        "device_id": device_id,
        "delta": delta,
        "in_sync": len(delta) == 0,
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
    }


@router.post(
    "/devices/{device_id}/commands",
    status_code=201,
    dependencies=[require_permission("devices.commands.send")],
)
async def send_command(device_id: str, body: CommandCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    user = get_user()
    command_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=body.expires_in_minutes)

    async with tenant_connection(pool, tenant_id) as conn:
        exists = await conn.fetchval(
            "SELECT 1 FROM device_state WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            device_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Device not found")

        await conn.execute(
            """
            INSERT INTO device_commands
              (command_id, tenant_id, device_id, command_type, command_params, expires_at, created_by)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            """,
            command_id,
            tenant_id,
            device_id,
            body.command_type,
            json.dumps(body.command_params),
            expires_at,
            user.get("sub") if user else None,
        )

    topic = f"tenant/{tenant_id}/device/{device_id}/commands"
    payload = json.dumps(
        {
            "command_id": command_id,
            "type": body.command_type,
            "params": body.command_params,
            "expires_at": expires_at.isoformat(),
        }
    )
    broker_url = os.getenv("MQTT_BROKER_URL", "mqtt://iot-mqtt:1883")
    result = await publish_alert(
        broker_url=broker_url,
        topic=topic,
        payload=payload,
        qos=1,
        retain=False,
    )

    if result.success:
        async with tenant_connection(pool, tenant_id) as conn:
            await conn.execute(
                """
                UPDATE device_commands
                SET published_at = NOW(), status = 'queued'
                WHERE tenant_id = $1 AND command_id = $2
                """,
                tenant_id,
                command_id,
            )

    commands_logger.info(
        "command_dispatched",
        extra={
            "tenant_id": tenant_id,
            "command_id": command_id,
            "device_id": device_id,
            "command_type": body.command_type,
            "mqtt_ok": result.success,
        },
    )

    return {
        "command_id": command_id,
        "status": "queued",
        "mqtt_published": result.success,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/devices/{device_id}/commands")
async def list_device_commands(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        conditions = ["tenant_id = $1", "device_id = $2"]
        params: list[object] = [tenant_id, device_id]

        if status:
            normalized_status = status.lower()
            if normalized_status not in {"queued", "delivered", "missed", "expired"}:
                raise HTTPException(status_code=400, detail="Invalid status")
            params.append(normalized_status)
            conditions.append(f"status = ${len(params)}")

        where = " AND ".join(conditions)
        params.append(limit)
        rows = await conn.fetch(
            f"""
            SELECT
                command_id,
                command_type,
                command_params,
                status,
                published_at,
                acked_at,
                ack_details,
                expires_at,
                created_by,
                created_at
            FROM device_commands
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )

    return [dict(r) for r in rows]


@router.get("/devices/{device_id}/tags")
async def get_device_tags(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            rows = await conn.fetch(
                """
                SELECT tag
                FROM device_tags
                WHERE tenant_id = $1 AND device_id = $2
                ORDER BY tag
                """,
                tenant_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch device tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tags": [r["tag"] for r in rows]}


@router.put(
    "/devices/{device_id}/tags",
    dependencies=[require_permission("devices.tags.write")],
)
async def set_device_tags(device_id: str, body: TagListUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags(body.tags)
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                "DELETE FROM device_tags WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if tags:
                await conn.executemany(
                    """
                    INSERT INTO device_tags (tenant_id, device_id, tag)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                    """,
                    [(tenant_id, device_id, tag) for tag in tags],
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to update device tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tags": tags}


@router.post(
    "/devices/{device_id}/tags/{tag}",
    dependencies=[require_permission("devices.tags.write")],
)
async def add_device_tag(device_id: str, tag: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags([tag])
    if not tags:
        raise HTTPException(status_code=400, detail="Invalid tag")
    tag_value = tags[0]
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                """
                INSERT INTO device_tags (tenant_id, device_id, tag)
                VALUES ($1, $2, $3)
                ON CONFLICT (tenant_id, device_id, tag) DO NOTHING
                """,
                tenant_id,
                device_id,
                tag_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add device tag")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tag": tag_value}


@router.delete(
    "/devices/{device_id}/tags/{tag}",
    dependencies=[require_permission("devices.tags.write")],
)
async def remove_device_tag(device_id: str, tag: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    tags = _normalize_tags([tag])
    if not tags:
        raise HTTPException(status_code=400, detail="Invalid tag")
    tag_value = tags[0]
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Device not found")

            await conn.execute(
                """
                DELETE FROM device_tags
                WHERE tenant_id = $1 AND device_id = $2 AND tag = $3
                """,
                tenant_id,
                device_id,
                tag_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to remove device tag")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "device_id": device_id, "tag": tag_value}


@router.get("/tags")
async def list_tags(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT tag
                FROM device_tags
                WHERE tenant_id = $1
                ORDER BY tag
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch tags")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "tags": [r["tag"] for r in rows]}


@router.get("/device-groups")
async def list_device_groups(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT g.group_id, g.name, g.description, g.created_at,
                       COUNT(m.device_id)::int AS member_count
                FROM device_groups g
                LEFT JOIN device_group_members m
                    ON m.tenant_id = g.tenant_id AND m.group_id = g.group_id
                WHERE g.tenant_id = $1
                GROUP BY g.group_id, g.name, g.description, g.created_at
                ORDER BY g.name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch device groups")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"groups": [dict(r) for r in rows], "total": len(rows)}


@router.post(
    "/device-groups",
    status_code=201,
    dependencies=[require_permission("devices.groups.write")],
)
async def create_device_group(body: DeviceGroupCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    group_id = (body.group_id or f"grp-{uuid.uuid4().hex[:8]}").strip()
    if not group_id:
        raise HTTPException(status_code=400, detail="Invalid group_id")
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO device_groups (tenant_id, group_id, name, description)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, group_id) DO NOTHING
                RETURNING group_id, name, description, created_at, updated_at
                """,
                tenant_id,
                group_id,
                body.name.strip(),
                body.description,
            )
    except Exception:
        logger.exception("Failed to create device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=409, detail="Group ID already exists")
    return dict(row)


@router.patch(
    "/device-groups/{group_id}",
    dependencies=[require_permission("devices.groups.write")],
)
async def update_device_group(group_id: str, body: DeviceGroupUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "name" in updates:
        updates["name"] = str(updates["name"]).strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Invalid name")

    set_parts = [f"{field} = ${idx + 2}" for idx, field in enumerate(updates.keys())]
    params = [tenant_id] + list(updates.values()) + [group_id]
    set_clause = ", ".join(set_parts) + ", updated_at = now()"
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE device_groups
                SET {set_clause}
                WHERE tenant_id = $1 AND group_id = ${len(params)}
                RETURNING group_id, tenant_id, name, description, created_at, updated_at
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return dict(row)


@router.delete(
    "/device-groups/{group_id}",
    dependencies=[require_permission("devices.groups.write")],
)
async def delete_device_group(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM device_groups
                WHERE tenant_id = $1 AND group_id = $2
                RETURNING group_id
                """,
                tenant_id,
                group_id,
            )
    except Exception:
        logger.exception("Failed to delete device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"group_id": group_id, "deleted": True}


@router.get("/device-groups/{group_id}/devices")
async def list_group_members(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT
                    dr.device_id,
                    COALESCE(dr.metadata->>'name', dr.device_id) AS name,
                    COALESCE(ds.status, 'UNKNOWN') AS status,
                    dr.site_id,
                    m.added_at
                FROM device_group_members m
                JOIN device_registry dr
                    ON dr.tenant_id = m.tenant_id AND dr.device_id = m.device_id
                LEFT JOIN device_state ds
                    ON ds.tenant_id = m.tenant_id AND ds.device_id = m.device_id
                WHERE m.tenant_id = $1 AND m.group_id = $2
                ORDER BY name, dr.device_id
                """,
                tenant_id,
                group_id,
            )
    except Exception:
        logger.exception("Failed to fetch group members")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"group_id": group_id, "members": [dict(r) for r in rows], "total": len(rows)}


@router.put(
    "/device-groups/{group_id}/devices/{device_id}",
    dependencies=[require_permission("devices.groups.write")],
)
async def add_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            group = await conn.fetchrow(
                "SELECT group_id FROM device_groups WHERE tenant_id = $1 AND group_id = $2",
                tenant_id,
                group_id,
            )
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            device_exists = await conn.fetchval(
                "SELECT 1 FROM device_registry WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
            if not device_exists:
                raise HTTPException(status_code=404, detail="Device not found")
            await conn.execute(
                """
                INSERT INTO device_group_members (tenant_id, group_id, device_id)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                tenant_id,
                group_id,
                device_id,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add group member")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"group_id": group_id, "device_id": device_id, "action": "added"}


@router.delete(
    "/device-groups/{group_id}/devices/{device_id}",
    dependencies=[require_permission("devices.groups.write")],
)
async def remove_group_member(group_id: str, device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM device_group_members
                WHERE tenant_id = $1 AND group_id = $2 AND device_id = $3
                RETURNING device_id
                """,
                tenant_id,
                group_id,
                device_id,
            )
    except Exception:
        logger.exception("Failed to remove group member")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Device not in group")
    return {"group_id": group_id, "device_id": device_id, "action": "removed"}


@router.get("/maintenance-windows")
async def list_maintenance_windows(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT *
                FROM alert_maintenance_windows
                WHERE tenant_id = $1
                ORDER BY starts_at DESC
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch maintenance windows")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"windows": [dict(r) for r in rows], "total": len(rows)}


@router.post(
    "/maintenance-windows",
    status_code=201,
    dependencies=[require_permission("maintenance.create")],
)
async def create_maintenance_window(body: MaintenanceWindowCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    window_id = f"mw-{uuid.uuid4().hex[:8]}"
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO alert_maintenance_windows
                    (tenant_id, window_id, name, starts_at, ends_at, recurring, site_ids, device_types, enabled)
                VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)
                RETURNING *
                """,
                tenant_id,
                window_id,
                body.name,
                body.starts_at,
                body.ends_at,
                json.dumps(body.recurring) if body.recurring is not None else None,
                _normalize_optional_ids(body.site_ids, "site_ids"),
                _normalize_optional_ids(body.device_types, "device_types"),
                body.enabled,
            )
    except Exception:
        logger.exception("Failed to create maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    return dict(row)


@router.patch(
    "/maintenance-windows/{window_id}",
    dependencies=[require_permission("maintenance.update")],
)
async def update_maintenance_window(
    window_id: str,
    body: MaintenanceWindowUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "site_ids" in updates:
        updates["site_ids"] = _normalize_optional_ids(updates["site_ids"], "site_ids")
    if "device_types" in updates:
        updates["device_types"] = _normalize_optional_ids(updates["device_types"], "device_types")
    if "recurring" in updates:
        updates["recurring"] = json.dumps(updates["recurring"])

    set_parts: list[str] = []
    params: list = [tenant_id]
    idx = 2
    for key, value in updates.items():
        cast = "::jsonb" if key == "recurring" else ""
        set_parts.append(f"{key} = ${idx}{cast}")
        params.append(value)
        idx += 1
    params.append(window_id)
    set_clause = ", ".join(set_parts)
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE alert_maintenance_windows
                SET {set_clause}
                WHERE tenant_id = $1 AND window_id = ${len(params)}
                RETURNING *
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return dict(row)


@router.delete(
    "/maintenance-windows/{window_id}",
    dependencies=[require_permission("maintenance.delete")],
)
async def delete_maintenance_window(window_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM alert_maintenance_windows
                WHERE tenant_id = $1 AND window_id = $2
                RETURNING window_id
                """,
                tenant_id,
                window_id,
            )
    except Exception:
        logger.exception("Failed to delete maintenance window")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Window not found")
    return {"window_id": window_id, "deleted": True}

