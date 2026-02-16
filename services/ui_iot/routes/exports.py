"""Data export, reports, audit log, and delivery status routes."""

from routes.customer import *  # noqa: F401,F403

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["exports"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

@router.get("/delivery-status")
async def delivery_status(
    limit: int = Query(20, ge=1, le=100),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            attempts = await fetch_delivery_attempts(conn, tenant_id, limit=limit)
    except Exception:
        logger.exception("Failed to fetch tenant delivery attempts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "attempts": attempts}


@router.get("/audit-log")
async def get_audit_log(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    search: str | None = Query(None),
):
    tenant_id = get_tenant_id()
    pool = request.app.state.pool

    async with tenant_connection(pool, tenant_id) as conn:

        where = ["tenant_id = $1"]
        params = [tenant_id]
        idx = 2

        if category:
            where.append(f"category = ${idx}")
            params.append(category)
            idx += 1

        if severity:
            where.append(f"severity = ${idx}")
            params.append(severity)
            idx += 1

        if entity_type:
            where.append(f"entity_type = ${idx}")
            params.append(entity_type)
            idx += 1

        if entity_id:
            where.append(f"entity_id = ${idx}")
            params.append(entity_id)
            idx += 1

        if start:
            where.append(f"timestamp >= ${idx}")
            params.append(start)
            idx += 1

        if end:
            where.append(f"timestamp <= ${idx}")
            params.append(end)
            idx += 1

        if search:
            where.append(f"message ILIKE ${idx}")
            params.append(f"%{search}%")
            idx += 1

        where_clause = " AND ".join(where)

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM audit_log WHERE {where_clause}",
            *params
        )

        rows = await conn.fetch(
            f"""
            SELECT timestamp, event_type, category, severity,
                   entity_type, entity_id, entity_name,
                   action, message, details,
                   source_service, actor_type, actor_id, actor_name
            FROM audit_log
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, limit, offset
        )

    return {
        "events": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/export/devices")
async def export_devices(
    format: str = Query("csv"),
    status: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    user = get_user() or {}
    async with tenant_connection(pool, tenant_id) as conn:
        where = ["dr.tenant_id = $1"]
        params: list[object] = [tenant_id]
        if status:
            params.append(status.upper())
            where.append(f"ds.status = ${len(params)}")
        if site_id:
            params.append(site_id)
            where.append(f"dr.site_id = ${len(params)}")
        where_sql = " AND ".join(where)
        rows = await conn.fetch(
            f"""
            SELECT dr.device_id,
                   COALESCE(dr.name, dr.device_id) AS name,
                   dr.model,
                   ds.status,
                   dr.site_id,
                   ds.last_seen_at,
                   dr.tags
            FROM device_registry dr
            LEFT JOIN device_state ds
              ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
            WHERE {where_sql}
            ORDER BY dr.device_id
            """,
            *params,
        )

        row_count = len(rows)
        await conn.execute(
            """
            INSERT INTO report_runs (tenant_id, report_type, status, triggered_by, row_count, completed_at)
            VALUES ($1, 'device_export', 'done', $2, $3, NOW())
            """,
            tenant_id,
            f"user:{user.get('sub', 'unknown')}",
            row_count,
        )

    if format.lower() == "json":
        return {"devices": [dict(row) for row in rows], "count": len(rows)}

    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Invalid format")

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["device_id", "name", "model", "status", "site_id", "last_seen_at", "tags"],
    )
    writer.writeheader()
    for row in rows:
        payload = dict(row)
        tags = payload.get("tags") or []
        if isinstance(tags, list):
            payload["tags"] = ",".join(str(item) for item in tags)
        writer.writerow(payload)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="devices-{date_str}.csv"'},
    )


@router.get("/export/alerts")
async def export_alerts(
    format: str = Query("csv"),
    status: str = Query("ALL"),
    days: int = Query(7, ge=1, le=365),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    user = get_user() or {}
    status_filter = status.upper()
    valid_statuses = {"OPEN", "ACKNOWLEDGED", "CLOSED", "ALL"}
    if status_filter not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    async with tenant_connection(pool, tenant_id) as conn:
        where = [
            "tenant_id = $1",
            "created_at >= NOW() - ($2 || ' days')::INTERVAL",
        ]
        params: list[object] = [tenant_id, str(days)]
        if status_filter != "ALL":
            params.append(status_filter)
            where.append(f"status = ${len(params)}")
        where_sql = " AND ".join(where)
        rows = await conn.fetch(
            f"""
            SELECT id AS alert_id, device_id, alert_type, severity, status, created_at,
                   acknowledged_at, closed_at, summary
            FROM fleet_alert
            WHERE {where_sql}
            ORDER BY created_at DESC
            """,
            *params,
        )
        await conn.execute(
            """
            INSERT INTO report_runs (tenant_id, report_type, status, triggered_by, row_count, completed_at)
            VALUES ($1, 'alert_export', 'done', $2, $3, NOW())
            """,
            tenant_id,
            f"user:{user.get('sub', 'unknown')}",
            len(rows),
        )

    if format.lower() == "json":
        return {"alerts": [dict(row) for row in rows], "count": len(rows)}
    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Invalid format")

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "alert_id",
            "device_id",
            "alert_type",
            "severity",
            "status",
            "created_at",
            "acknowledged_at",
            "closed_at",
            "summary",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="alerts-{date_str}.csv"'},
    )


@router.get("/reports/sla-summary")
async def get_sla_summary(
    days: int = Query(30, ge=1, le=365),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    user = get_user() or {}
    report = await generate_sla_report(pool, tenant_id, days)
    async with tenant_connection(pool, tenant_id) as conn:
        await conn.execute(
            """
            INSERT INTO report_runs (tenant_id, report_type, status, triggered_by, parameters, completed_at)
            VALUES ($1, 'sla_summary', 'done', $2, $3::jsonb, NOW())
            """,
            tenant_id,
            f"user:{user.get('sub', 'unknown')}",
            json.dumps(report),
        )
    return report


@router.get("/reports/runs")
async def list_report_runs(limit: int = Query(50, ge=1, le=200), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT run_id, report_type, status, triggered_by, row_count, created_at, completed_at
            FROM report_runs
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            tenant_id,
            limit,
        )
    return {"runs": [dict(row) for row in rows]}
