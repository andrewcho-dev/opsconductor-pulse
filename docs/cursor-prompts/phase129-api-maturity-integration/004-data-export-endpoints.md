# Task 004 -- Async Data Export Endpoints with Background Processing

## Commit Message
```
feat: add async data export with background processing and chunked download
```

## Context

The existing export endpoints in `routes/exports.py` are synchronous -- they query the full dataset, format it in memory, and stream the response. This breaks for large tenants (100k+ devices, millions of telemetry rows). This task adds an async export system: the user creates an export job, a background worker processes it to a file, and the user downloads the result.

The existing synchronous export endpoints (`/export/devices`, `/export/alerts`) will remain as-is for backward compatibility (they serve the "quick export" use case). The new async endpoints are for large-scale exports.

## Step 1: Create the database migration

Create a new migration file. Find the existing migration directory convention (likely `migrations/` or `db/migrations/`).

```sql
-- Migration: create export_jobs table
-- Phase 129 - Async data export infrastructure

CREATE TABLE IF NOT EXISTS export_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       TEXT NOT NULL REFERENCES tenants(tenant_id),
    export_type     TEXT NOT NULL CHECK (export_type IN ('devices', 'alerts', 'telemetry')),
    format          TEXT NOT NULL DEFAULT 'csv' CHECK (format IN ('json', 'csv')),
    filters         JSONB NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    file_path       TEXT,
    file_size_bytes BIGINT,
    row_count       INTEGER,
    error           TEXT,
    callback_url    TEXT,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Index for the worker to find pending jobs efficiently
CREATE INDEX IF NOT EXISTS idx_export_jobs_status
    ON export_jobs (status, created_at)
    WHERE status = 'PENDING';

-- Index for tenant queries
CREATE INDEX IF NOT EXISTS idx_export_jobs_tenant
    ON export_jobs (tenant_id, created_at DESC);

-- Enable RLS
ALTER TABLE export_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY export_jobs_tenant_isolation ON export_jobs
    USING (tenant_id = current_setting('app.tenant_id', true));
```

Place this in the appropriate migration directory following existing naming conventions.

## Step 2: Create Pydantic schemas

Create `services/ui_iot/schemas/exports.py`:

```python
"""Pydantic models for async data export."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ExportFilters(BaseModel):
    """Filters applied to the export query."""
    time_range: Optional[str] = Field(
        None,
        description="Time range for data: 1h, 6h, 24h, 7d, 30d, 90d",
    )
    device_ids: Optional[list[str]] = Field(
        None,
        description="Filter to specific device IDs",
    )
    site_ids: Optional[list[str]] = Field(
        None,
        description="Filter to specific site IDs",
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status (e.g., OPEN, CLOSED for alerts; ONLINE, OFFLINE for devices)",
    )
    alert_types: Optional[list[str]] = Field(
        None,
        description="Filter alerts by type (THRESHOLD, NO_HEARTBEAT, etc.)",
    )
    metric_names: Optional[list[str]] = Field(
        None,
        description="Filter telemetry to specific metric names",
    )


class ExportCreateRequest(BaseModel):
    """Request to create a new async export job."""
    export_type: str = Field(
        ...,
        description="Type of data to export",
        pattern="^(devices|alerts|telemetry)$",
    )
    format: str = Field(
        default="csv",
        description="Output format",
        pattern="^(json|csv)$",
    )
    filters: ExportFilters = Field(
        default_factory=ExportFilters,
        description="Optional filters to narrow the export",
    )
    callback_url: Optional[str] = Field(
        None,
        description="URL to POST result notification when export completes",
    )


class ExportJobResponse(BaseModel):
    """Response for a single export job."""
    export_id: str
    tenant_id: str
    export_type: str
    format: str
    filters: dict
    status: str
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    error: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class ExportCreateResponse(BaseModel):
    """Response when creating a new export job."""
    export_id: str
    status: str = "PENDING"
    estimated_rows: Optional[int] = None
    message: str = "Export job created. Poll status endpoint for progress."


class ExportListResponse(BaseModel):
    """Response listing export jobs."""
    exports: list[ExportJobResponse]
    total: int
```

## Step 3: Add export endpoints to routes/exports.py

Add the new async export endpoints to `services/ui_iot/routes/exports.py`. These go ALONGSIDE the existing synchronous export endpoints (do not delete or modify the existing ones).

```python
# Add these imports at the top of exports.py:
import uuid
from schemas.exports import (
    ExportCreateRequest,
    ExportCreateResponse,
    ExportJobResponse,
    ExportListResponse,
)

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
                "1h": "1 hour", "6h": "6 hours", "24h": "24 hours",
                "7d": "7 days", "30d": "30 days", "90d": "90 days",
            }
            pg_interval = interval_map.get(range_interval, "24 hours")
            estimated_rows = await conn.fetchval(
                f"SELECT COUNT(*) FROM telemetry WHERE tenant_id = $1 AND time > NOW() - '{pg_interval}'::interval",
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

        # Store callback_url in filters if provided
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
    validate_uuid(export_id)

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
    validate_uuid(export_id)

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

    import aiofiles

    async def file_iterator():
        async with aiofiles.open(file_path, mode="rb") as f:
            while True:
                chunk = await f.read(64 * 1024)  # 64KB chunks
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Row-Count": str(row["row_count"] or 0),
        },
    )
```

**Note:** Add `import os` and `import aiofiles` to the imports. If `aiofiles` is not a dependency, use synchronous file reading in a threadpool instead:

```python
# Alternative without aiofiles:
from fastapi.responses import FileResponse

return FileResponse(
    path=file_path,
    media_type=media_type,
    filename=filename,
    headers={"X-Export-Row-Count": str(row["row_count"] or 0)},
)
```

## Step 4: Create the background export worker

Create `services/ops_worker/workers/export_worker.py`:

```python
"""Background worker for processing async data export jobs."""

import csv
import io
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

EXPORT_DIR = os.getenv("EXPORT_DIR", "/tmp/pulse-exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

TIME_RANGE_MAP = {
    "1h": "1 hour",
    "6h": "6 hours",
    "24h": "24 hours",
    "7d": "7 days",
    "30d": "30 days",
    "90d": "90 days",
}


async def run_export_tick(pool):
    """Process pending export jobs. Called periodically by the worker loop."""
    async with pool.acquire() as conn:
        # Claim a pending job (prevents other workers from processing the same job)
        row = await conn.fetchrow(
            """
            UPDATE export_jobs
            SET status = 'PROCESSING', started_at = NOW()
            WHERE id = (
                SELECT id FROM export_jobs
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, tenant_id, export_type, format, filters, callback_url
            """
        )

    if not row:
        return  # No pending jobs

    export_id = str(row["id"])
    tenant_id = row["tenant_id"]
    export_type = row["export_type"]
    export_format = row["format"]
    filters = row["filters"] or {}
    callback_url = row["callback_url"]

    logger.info(
        "export_job_started",
        extra={
            "export_id": export_id,
            "tenant_id": tenant_id,
            "export_type": export_type,
            "format": export_format,
        },
    )

    try:
        file_path, row_count = await _process_export(
            pool, tenant_id, export_type, export_format, filters, export_id
        )

        file_size = os.path.getsize(file_path) if file_path else 0

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE export_jobs
                SET status = 'COMPLETED',
                    file_path = $1,
                    file_size_bytes = $2,
                    row_count = $3,
                    completed_at = NOW()
                WHERE id = $4
                """,
                file_path,
                file_size,
                row_count,
                export_id,
            )

        logger.info(
            "export_job_completed",
            extra={
                "export_id": export_id,
                "row_count": row_count,
                "file_size": file_size,
            },
        )

        # Notify callback URL if provided
        if callback_url:
            await _send_callback(callback_url, export_id, "COMPLETED", row_count)

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
        logger.exception(
            "export_job_failed",
            extra={"export_id": export_id, "error": error_msg},
        )

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE export_jobs
                SET status = 'FAILED',
                    error = $1,
                    completed_at = NOW()
                WHERE id = $2
                """,
                error_msg,
                export_id,
            )

        if callback_url:
            await _send_callback(callback_url, export_id, "FAILED", 0, error_msg)


async def _process_export(
    pool, tenant_id: str, export_type: str, export_format: str,
    filters: dict, export_id: str,
) -> tuple[str, int]:
    """Process an export job and write results to a temp file.

    Returns: (file_path, row_count)
    """
    file_path = os.path.join(EXPORT_DIR, f"{export_id}.{export_format}")

    async with pool.acquire() as conn:
        # Set tenant context for RLS
        await conn.execute(
            "SELECT set_config('app.tenant_id', $1, true)", tenant_id
        )

        if export_type == "devices":
            return await _export_devices(conn, tenant_id, filters, file_path, export_format)
        elif export_type == "alerts":
            return await _export_alerts(conn, tenant_id, filters, file_path, export_format)
        elif export_type == "telemetry":
            return await _export_telemetry(conn, tenant_id, filters, file_path, export_format)
        else:
            raise ValueError(f"Unknown export type: {export_type}")


async def _export_devices(conn, tenant_id, filters, file_path, fmt) -> tuple[str, int]:
    """Export device data."""
    conditions = ["dr.tenant_id = $1"]
    params = [tenant_id]
    idx = 2

    if filters.get("status"):
        conditions.append(f"ds.status = ${idx}")
        params.append(filters["status"].upper())
        idx += 1

    if filters.get("site_ids"):
        conditions.append(f"dr.site_id = ANY(${idx}::text[])")
        params.append(filters["site_ids"])
        idx += 1

    if filters.get("device_ids"):
        conditions.append(f"dr.device_id = ANY(${idx}::text[])")
        params.append(filters["device_ids"])
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT dr.device_id, COALESCE(dr.name, dr.device_id) AS name,
               dr.model, dr.device_type, dr.site_id,
               COALESCE(ds.status, 'UNKNOWN') AS status,
               ds.last_seen_at, dr.tags, dr.created_at
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE {where}
        ORDER BY dr.device_id
        """,
        *params,
    )

    return _write_rows(
        file_path, fmt, rows,
        fieldnames=["device_id", "name", "model", "device_type", "site_id",
                     "status", "last_seen_at", "tags", "created_at"],
    )


async def _export_alerts(conn, tenant_id, filters, file_path, fmt) -> tuple[str, int]:
    """Export alert data."""
    conditions = ["tenant_id = $1"]
    params = [tenant_id]
    idx = 2

    if filters.get("status"):
        conditions.append(f"status = ${idx}")
        params.append(filters["status"].upper())
        idx += 1

    time_range = filters.get("time_range", "30d")
    pg_interval = TIME_RANGE_MAP.get(time_range, "30 days")
    conditions.append(f"created_at >= NOW() - '{pg_interval}'::interval")

    if filters.get("alert_types"):
        conditions.append(f"alert_type = ANY(${idx}::text[])")
        params.append(filters["alert_types"])
        idx += 1

    if filters.get("device_ids"):
        conditions.append(f"device_id = ANY(${idx}::text[])")
        params.append(filters["device_ids"])
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT id AS alert_id, device_id, site_id, alert_type, severity,
               status, summary, created_at, acknowledged_at, closed_at
        FROM fleet_alert
        WHERE {where}
        ORDER BY created_at DESC
        """,
        *params,
    )

    return _write_rows(
        file_path, fmt, rows,
        fieldnames=["alert_id", "device_id", "site_id", "alert_type", "severity",
                     "status", "summary", "created_at", "acknowledged_at", "closed_at"],
    )


async def _export_telemetry(conn, tenant_id, filters, file_path, fmt) -> tuple[str, int]:
    """Export telemetry data. Processes in chunks to handle large datasets."""
    conditions = ["tenant_id = $1"]
    params = [tenant_id]
    idx = 2

    time_range = filters.get("time_range", "24h")
    pg_interval = TIME_RANGE_MAP.get(time_range, "24 hours")
    conditions.append(f"time >= NOW() - '{pg_interval}'::interval")

    if filters.get("device_ids"):
        conditions.append(f"device_id = ANY(${idx}::text[])")
        params.append(filters["device_ids"])
        idx += 1

    if filters.get("site_ids"):
        conditions.append(f"site_id = ANY(${idx}::text[])")
        params.append(filters["site_ids"])
        idx += 1

    where = " AND ".join(conditions)

    # For large telemetry exports, use cursor-based iteration
    # First pass: discover metric keys
    sample_rows = await conn.fetch(
        f"""
        SELECT metrics FROM telemetry
        WHERE {where}
        LIMIT 1000
        """,
        *params,
    )

    metric_keys = sorted({
        key for row in sample_rows
        for key in ((row["metrics"] or {}).keys())
    })

    # Fetch all rows
    rows = await conn.fetch(
        f"""
        SELECT time, device_id, site_id, seq, metrics
        FROM telemetry
        WHERE {where}
        ORDER BY time ASC
        LIMIT 1000000
        """,
        *params,
    )

    if fmt == "csv":
        fieldnames = ["time", "device_id", "site_id", "seq", *metric_keys]
        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                metrics = row["metrics"] or {}
                csv_row = {
                    "time": row["time"].isoformat() if row["time"] else "",
                    "device_id": row["device_id"],
                    "site_id": row["site_id"] or "",
                    "seq": row["seq"],
                }
                for key in metric_keys:
                    csv_row[key] = metrics.get(key, "")
                writer.writerow(csv_row)
        return file_path, len(rows)
    else:
        data = []
        for row in rows:
            data.append({
                "time": row["time"].isoformat() if row["time"] else None,
                "device_id": row["device_id"],
                "site_id": row["site_id"],
                "seq": row["seq"],
                "metrics": row["metrics"] or {},
            })
        with open(file_path, "w") as f:
            json.dump({"telemetry": data, "count": len(data)}, f, default=str)
        return file_path, len(rows)


def _write_rows(file_path: str, fmt: str, rows, fieldnames: list[str]) -> tuple[str, int]:
    """Write query results to a file in the specified format."""
    if fmt == "csv":
        with open(file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                csv_row = {}
                for key in fieldnames:
                    value = row.get(key)
                    if isinstance(value, list):
                        csv_row[key] = ",".join(str(v) for v in value)
                    elif isinstance(value, datetime):
                        csv_row[key] = value.isoformat()
                    else:
                        csv_row[key] = value
                writer.writerow(csv_row)
        return file_path, len(rows)
    else:
        data = [dict(row) for row in rows]
        with open(file_path, "w") as f:
            json.dump({"data": data, "count": len(data)}, f, default=str)
        return file_path, len(rows)


async def _send_callback(
    callback_url: str,
    export_id: str,
    status: str,
    row_count: int,
    error: str | None = None,
) -> None:
    """POST export completion notification to the callback URL."""
    payload = {
        "export_id": export_id,
        "status": status,
        "row_count": row_count,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        payload["error"] = error

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(callback_url, json=payload)
    except Exception as exc:
        logger.warning(
            "export_callback_failed",
            extra={
                "export_id": export_id,
                "callback_url": callback_url,
                "error": str(exc),
            },
        )


async def run_export_cleanup(pool):
    """Delete expired export files and records. Called periodically."""
    async with pool.acquire() as conn:
        expired = await conn.fetch(
            """
            DELETE FROM export_jobs
            WHERE expires_at < NOW()
            RETURNING id, file_path
            """
        )

    for row in expired:
        file_path = row["file_path"]
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    if expired:
        logger.info("export_cleanup", extra={"cleaned": len(expired)})
```

## Step 5: Register the export worker in ops_worker/main.py

In `services/ops_worker/main.py`, add the export worker to the worker loop:

```python
# Add import:
from workers.export_worker import run_export_tick, run_export_cleanup

# In the main() function, add two new worker tasks:
# Export processor: runs every 5 seconds (to pick up PENDING jobs quickly)
asyncio.create_task(worker_loop(run_export_tick, pool, interval=5))

# Export cleanup: runs every hour (to clean up expired export files)
asyncio.create_task(worker_loop(run_export_cleanup, pool, interval=3600))
```

Find the existing pattern in `main.py` where other workers are registered and follow the same pattern:

```python
async def main():
    pool = await get_pool()
    tasks = [
        asyncio.create_task(worker_loop(run_health_monitor, pool, interval=60)),
        asyncio.create_task(worker_loop(run_metrics_collector, pool, interval=5)),
        asyncio.create_task(worker_loop(run_escalation_tick, pool, interval=30)),
        asyncio.create_task(worker_loop(run_report_tick, pool, interval=86400)),
        asyncio.create_task(worker_loop(run_jobs_expiry_tick, pool, interval=60)),
        asyncio.create_task(worker_loop(run_commands_expiry_tick, pool, interval=60)),
        # NEW:
        asyncio.create_task(worker_loop(run_export_tick, pool, interval=5)),
        asyncio.create_task(worker_loop(run_export_cleanup, pool, interval=3600)),
    ]
    await asyncio.gather(*tasks)
```

## Step 6: Add aiofiles dependency (if using async file streaming)

If using the `aiofiles` approach for the download endpoint, add it to the service's requirements:

```
# In services/ui_iot/requirements.txt or pyproject.toml:
aiofiles>=23.0
```

Alternatively, use FastAPI's `FileResponse` which handles file streaming without `aiofiles`.

## Step 7: Ensure EXPORT_DIR is shared between ui_iot and ops_worker

Both services need access to the same directory for export files. In Docker Compose, add a shared volume:

```yaml
# In docker-compose.yml:
volumes:
  export-data:

services:
  ui-iot:
    volumes:
      - export-data:/tmp/pulse-exports

  ops-worker:
    volumes:
      - export-data:/tmp/pulse-exports
```

Or use a named volume or bind mount that both services can access.

## Verification

```bash
# 1. Create a device export
EXPORT=$(curl -s -X POST http://localhost:8080/api/v1/customer/exports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"export_type":"devices","format":"csv"}')
echo $EXPORT | jq .
EXPORT_ID=$(echo $EXPORT | jq -r .export_id)

# 2. Poll for status
sleep 10
curl -s "http://localhost:8080/api/v1/customer/exports/${EXPORT_ID}" \
  -H "Authorization: Bearer $TOKEN" | jq .status
# Expected: "COMPLETED" (may need longer for large datasets)

# 3. Download the file
curl -s "http://localhost:8080/api/v1/customer/exports/${EXPORT_ID}/download" \
  -H "Authorization: Bearer $TOKEN" -o devices.csv
head -5 devices.csv
# Expected: CSV with device_id, name, model, etc.

# 4. Create a telemetry export with filters
curl -s -X POST http://localhost:8080/api/v1/customer/exports \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{
    "export_type": "telemetry",
    "format": "json",
    "filters": {
      "time_range": "1h",
      "device_ids": ["dev-001"]
    }
  }' | jq .

# 5. List all exports
curl -s "http://localhost:8080/api/v1/customer/exports" \
  -H "Authorization: Bearer $TOKEN" | jq '.exports | length'

# 6. Verify download of non-ready export returns 409
curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8080/api/v1/customer/exports/${EXPORT_ID}/download" \
  -H "Authorization: Bearer $TOKEN"
# (If still PENDING: Expected 409)

# 7. Verify tenant isolation -- export from another tenant returns 404
curl -s -o /dev/null -w "%{http_code}" \
  "http://localhost:8080/api/v1/customer/exports/wrong-uuid/download" \
  -H "Authorization: Bearer $OTHER_TOKEN"
# Expected: 404
```

## Notes

- The export worker uses `FOR UPDATE SKIP LOCKED` to prevent multiple worker instances from processing the same job. This is safe for multi-instance deployments.
- Export files are stored with a 24-hour TTL. The cleanup worker removes expired files.
- The `EXPORT_DIR` environment variable controls where files are written. Ensure adequate disk space.
- For very large telemetry exports (millions of rows), the `LIMIT 1000000` cap prevents OOM. Consider adding streaming cursor support in a future iteration.
- The callback_url feature uses `send_webhook()` style POST but without HMAC signing. If the export callback needs signing, the tenant should use the main notification channel system instead.
