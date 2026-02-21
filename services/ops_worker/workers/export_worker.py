"""Background worker for processing async data export jobs."""

import csv
import io
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

try:
    import boto3
    from botocore.config import Config
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]
import httpx
from shared.config import require_env, optional_env

logger = logging.getLogger(__name__)

S3_ENDPOINT = optional_env("S3_ENDPOINT", "http://iot-minio:9000")
S3_BUCKET = optional_env("S3_BUCKET", "exports")
S3_ACCESS_KEY = require_env("S3_ACCESS_KEY")
S3_SECRET_KEY = require_env("S3_SECRET_KEY")
S3_REGION = optional_env("S3_REGION", "us-east-1")


def get_s3_client():
    if boto3 is None or Config is None:
        raise RuntimeError(
            "boto3 is required for S3 export operations. Install it with: pip install boto3"
        )
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )

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
        local_path, row_count = await _process_export(
            pool, tenant_id, export_type, export_format, filters, export_id
        )

        file_size = os.path.getsize(local_path) if local_path else 0

        # Upload to S3-compatible storage; store the object key in export_jobs.file_path.
        s3_key = f"{export_id}.{export_format}"
        s3 = get_s3_client()
        s3.upload_file(local_path, S3_BUCKET, s3_key)

        try:
            os.remove(local_path)
        except OSError:
            pass

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
                s3_key,
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
    pool,
    tenant_id: str,
    export_type: str,
    export_format: str,
    filters: dict,
    export_id: str,
) -> tuple[str, int]:
    """Process an export job and write results to a temp file.

    Returns: (file_path, row_count)
    """
    file_path = os.path.join(tempfile.gettempdir(), f"pulse-export-{export_id}.{export_format}")

    async with pool.acquire() as conn:
        # Set tenant context for RLS
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", tenant_id)

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
        file_path,
        fmt,
        rows,
        fieldnames=[
            "device_id",
            "name",
            "model",
            "device_type",
            "site_id",
            "status",
            "last_seen_at",
            "tags",
            "created_at",
        ],
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
        file_path,
        fmt,
        rows,
        fieldnames=[
            "alert_id",
            "device_id",
            "site_id",
            "alert_type",
            "severity",
            "status",
            "summary",
            "created_at",
            "acknowledged_at",
            "closed_at",
        ],
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

    metric_keys = sorted({key for row in sample_rows for key in ((row["metrics"] or {}).keys())})

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
            data.append(
                {
                    "time": row["time"].isoformat() if row["time"] else None,
                    "device_id": row["device_id"],
                    "site_id": row["site_id"],
                    "seq": row["seq"],
                    "metrics": row["metrics"] or {},
                }
            )
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
                row_dict = dict(row)
                csv_row = {}
                for key in fieldnames:
                    value = row_dict.get(key)
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

    s3 = None
    if expired:
        try:
            s3 = get_s3_client()
        except Exception:
            s3 = None

    for row in expired:
        s3_key = row["file_path"]
        if s3 and s3_key:
            try:
                s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            except Exception:
                pass

    if expired:
        logger.info("export_cleanup", extra={"cleaned": len(expired)})

