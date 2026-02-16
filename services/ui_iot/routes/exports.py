"""Data export, reports, audit log, and delivery status routes."""

import json
import os
import uuid

from fastapi.responses import FileResponse

from routes.customer import *  # noqa: F401,F403
from schemas.exports import (
    ExportCreateRequest,
    ExportCreateResponse,
    ExportJobResponse,
    ExportListResponse,
)

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
    """List recent notification delivery attempts for the tenant."""
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


# ------ NEW ASYNC EXPORT ENDPOINTS ------

VALID_TIME_RANGES = {"1h", "6h", "24h", "7d", "30d", "90d"}


@router.post("/exports", status_code=202, response_model=ExportCreateResponse)
async def create_export(
    body: ExportCreateRequest,
    pool=Depends(get_db_pool),
):
    """Create an asynchronous data export job.

    The export is processed in the background. Use the returned export_id
    to poll for status and download the result when complete.

    Supported export types:
    - devices: All devices matching filters
    - alerts: Alert history matching filters
    - telemetry: Raw telemetry data matching filters

    Supported formats: csv, json
    """
    tenant_id = get_tenant_id()
    user = get_user()

    # Validate time_range if provided
    if body.filters.time_range and body.filters.time_range not in VALID_TIME_RANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time_range. Must be one of: {sorted(VALID_TIME_RANGES)}",
        )

    # Estimate row count for user feedback
    estimated_rows = None
    async with tenant_connection(pool, tenant_id) as conn:
        if body.export_type == "devices":
            estimated_rows = await conn.fetchval(
                "SELECT COUNT(*) FROM device_registry WHERE tenant_id = $1",
                tenant_id,
            )
        elif body.export_type == "alerts":
            estimated_rows = await conn.fetchval(
                "SELECT COUNT(*) FROM fleet_alert WHERE tenant_id = $1",
                tenant_id,
            )
        elif body.export_type == "telemetry":
            # Rough estimate based on time range
            range_interval = body.filters.time_range or "24h"
            interval_map = {
                "1h": "1 hour",
                "6h": "6 hours",
                "24h": "24 hours",
                "7d": "7 days",
                "30d": "30 days",
                "90d": "90 days",
            }
            pg_interval = interval_map.get(range_interval, "24 hours")
            estimated_rows = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM telemetry
                WHERE tenant_id = $1
                  AND time > NOW() - '{pg_interval}'::interval
                """,
                tenant_id,
            )

        # Insert export job
        export_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO export_jobs
                (id, tenant_id, export_type, format, filters, status, created_by)
            VALUES ($1, $2, $3, $4, $5::jsonb, 'PENDING', $6)
            """,
            export_id,
            tenant_id,
            body.export_type,
            body.format,
            json.dumps(body.filters.model_dump(exclude_none=True)),
            user.get("sub") if user else None,
        )

        # Store callback_url if provided
        if body.callback_url:
            await conn.execute(
                "UPDATE export_jobs SET callback_url = $1 WHERE id = $2",
                body.callback_url,
                export_id,
            )

    return ExportCreateResponse(
        export_id=export_id,
        status="PENDING",
        estimated_rows=estimated_rows,
    )


@router.get("/exports", response_model=ExportListResponse)
async def list_exports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    """List export jobs for the authenticated tenant.

    Returns most recent exports first. Includes status, row count,
    and download URL for completed exports.
    """
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, export_type, format, filters, status,
                   file_size_bytes, row_count, error, callback_url,
                   created_at, started_at, completed_at, expires_at
            FROM export_jobs
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id,
            limit,
            offset,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM export_jobs WHERE tenant_id = $1",
            tenant_id,
        )

    exports = []
    for row in rows:
        export = ExportJobResponse(
            export_id=str(row["id"]),
            tenant_id=row["tenant_id"],
            export_type=row["export_type"],
            format=row["format"],
            filters=row["filters"] or {},
            status=row["status"],
            file_size_bytes=row["file_size_bytes"],
            row_count=row["row_count"],
            error=row["error"],
            download_url=(
                f"/api/v1/customer/exports/{row['id']}/download"
                if row["status"] == "COMPLETED"
                else None
            ),
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            expires_at=row["expires_at"],
        )
        exports.append(export)

    return ExportListResponse(exports=exports, total=total or 0)


@router.get("/exports/{export_id}", response_model=ExportJobResponse)
async def get_export_status(
    export_id: str,
    pool=Depends(get_db_pool),
):
    """Get the status of an export job.

    Poll this endpoint to check if the export has completed.
    When status is COMPLETED, the download_url field will be populated.
    """
    tenant_id = get_tenant_id()
    if not validate_uuid(export_id):
        raise HTTPException(status_code=400, detail="Invalid export_id")

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, tenant_id, export_type, format, filters, status,
                   file_size_bytes, row_count, error, callback_url,
                   created_at, started_at, completed_at, expires_at
            FROM export_jobs
            WHERE id = $1 AND tenant_id = $2
            """,
            export_id,
            tenant_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Export job not found")

    return ExportJobResponse(
        export_id=str(row["id"]),
        tenant_id=row["tenant_id"],
        export_type=row["export_type"],
        format=row["format"],
        filters=row["filters"] or {},
        status=row["status"],
        file_size_bytes=row["file_size_bytes"],
        row_count=row["row_count"],
        error=row["error"],
        download_url=(
            f"/api/v1/customer/exports/{row['id']}/download"
            if row["status"] == "COMPLETED"
            else None
        ),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        expires_at=row["expires_at"],
    )


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    pool=Depends(get_db_pool),
):
    """Download a completed export file.

    Returns the export data as a streaming response with chunked transfer encoding.
    The Content-Type header matches the export format (text/csv or application/json).
    """
    tenant_id = get_tenant_id()
    if not validate_uuid(export_id):
        raise HTTPException(status_code=400, detail="Invalid export_id")

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, export_type, format, status, file_path, row_count
            FROM export_jobs
            WHERE id = $1 AND tenant_id = $2
            """,
            export_id,
            tenant_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Export job not found")

    if row["status"] != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=f"Export is not ready. Current status: {row['status']}",
        )

    file_path = row["file_path"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=410, detail="Export file no longer available")

    export_format = row["format"]
    media_type = "text/csv" if export_format == "csv" else "application/json"
    filename = f"{row['export_type']}-export-{export_id[:8]}.{export_format}"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
        headers={"X-Export-Row-Count": str(row["row_count"] or 0)},
    )


@router.get("/export/devices")
async def export_devices(
    format: str = Query("csv"),
    status: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    pool=Depends(get_db_pool),
):
    """Export device list as CSV for the tenant."""
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
    """Export alert history as CSV for the tenant."""
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
