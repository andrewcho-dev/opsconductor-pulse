"""Ad-hoc telemetry analytics -- query builder, aggregation, CSV export."""

import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from middleware.auth import JWTBearer
from middleware.tenant import inject_tenant_context, get_tenant_id, require_customer
from db.pool import tenant_connection
from dependencies import get_db_pool
from shared.logging import get_logger

logger = get_logger("pulse.analytics")

router = APIRouter(
    prefix="/api/v1/customer/analytics",
    tags=["analytics"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


class AnalyticsQueryRequest(BaseModel):
    metric: str = Field(..., min_length=1, max_length=100)
    aggregation: Literal["avg", "min", "max", "p95", "sum", "count"] = "avg"
    time_range: Literal["1h", "6h", "24h", "7d", "30d"] = "24h"
    group_by: Literal["device", "site", "group"] | None = None
    device_ids: list[str] | None = None
    group_id: str | None = None
    bucket_size: str | None = None  # e.g. "5 minutes", "1 hour"


class AnalyticsPoint(BaseModel):
    time: str
    value: float | None


class AnalyticsSeries(BaseModel):
    label: str
    points: list[AnalyticsPoint]


class AnalyticsSummary(BaseModel):
    min: float | None
    max: float | None
    avg: float | None
    total_points: int


class AnalyticsQueryResponse(BaseModel):
    series: list[AnalyticsSeries]
    summary: AnalyticsSummary


TIME_RANGE_MAP: dict[str, tuple[str, str]] = {
    "1h": ("1 hour", "1 minute"),
    "6h": ("6 hours", "5 minutes"),
    "24h": ("24 hours", "15 minutes"),
    "7d": ("7 days", "1 hour"),
    "30d": ("30 days", "6 hours"),
}

AGGREGATION_SQL: dict[str, str] = {
    "avg": "AVG((metrics->>$2)::numeric)",
    "min": "MIN((metrics->>$2)::numeric)",
    "max": "MAX((metrics->>$2)::numeric)",
    "sum": "SUM((metrics->>$2)::numeric)",
    "count": "COUNT(*)",
    "p95": "percentile_cont(0.95) WITHIN GROUP (ORDER BY (metrics->>$2)::numeric)",
}


@router.get("/metrics")
async def list_available_metrics(pool=Depends(get_db_pool)):
    """Return distinct metric names from recent telemetry for this tenant."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT k AS metric_name
                FROM telemetry, LATERAL jsonb_object_keys(metrics) AS k
                WHERE tenant_id = $1
                  AND time > now() - interval '7 days'
                ORDER BY metric_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to list analytics metrics")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"metrics": [row["metric_name"] for row in rows]}


@router.post("/query", response_model=AnalyticsQueryResponse)
async def run_analytics_query(body: AnalyticsQueryRequest, pool=Depends(get_db_pool)):
    """Execute an ad-hoc analytics query with time_bucket aggregation."""
    tenant_id = get_tenant_id()

    lookback, default_bucket = TIME_RANGE_MAP.get(body.time_range, TIME_RANGE_MAP["24h"])
    bucket = body.bucket_size or default_bucket

    agg_expr = AGGREGATION_SQL.get(body.aggregation)
    if not agg_expr:
        raise HTTPException(status_code=400, detail="Invalid aggregation")

    conditions = [
        "tenant_id = $3",
        "time > now() - $4::interval",
        "metrics ? $2",
    ]
    params: list = [bucket, body.metric, tenant_id, lookback]
    param_idx = 5

    if body.device_ids and len(body.device_ids) > 0:
        conditions.append(f"device_id = ANY(${param_idx}::text[])")
        params.append(body.device_ids)
        param_idx += 1

    if body.group_id:
        conditions.append(
            f"""device_id IN (
                SELECT device_id FROM device_group_members
                WHERE tenant_id = $3 AND group_id = ${param_idx}
            )"""
        )
        params.append(body.group_id)
        param_idx += 1

    where_clause = " AND ".join(conditions)

    if body.group_by == "device":
        group_col = "device_id"
        label_expr = "device_id"
    elif body.group_by == "site":
        group_col = "site_id"
        label_expr = "COALESCE(site_id, 'unknown')"
    elif body.group_by == "group":
        group_col = "device_id"
        label_expr = "device_id"
    else:
        group_col = None
        label_expr = "'all'"

    if group_col:
        query = f"""
            SELECT
                {label_expr} AS label,
                time_bucket($1::interval, time) AS bucket,
                {agg_expr} AS agg_value
            FROM telemetry
            WHERE {where_clause}
            GROUP BY label, bucket
            ORDER BY label, bucket ASC
        """
    else:
        query = f"""
            SELECT
                {label_expr} AS label,
                time_bucket($1::interval, time) AS bucket,
                {agg_expr} AS agg_value
            FROM telemetry
            WHERE {where_clause}
            GROUP BY bucket
            ORDER BY bucket ASC
        """

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(query, *params)
    except Exception:
        logger.exception("Analytics query failed")
        raise HTTPException(status_code=500, detail="Query execution failed")

    series_map: dict[str, list[AnalyticsPoint]] = {}
    all_values: list[float] = []

    for row in rows:
        label = str(row["label"])
        value = float(row["agg_value"]) if row["agg_value"] is not None else None
        point = AnalyticsPoint(time=row["bucket"].isoformat(), value=value)

        if label not in series_map:
            series_map[label] = []
        series_map[label].append(point)

        if value is not None:
            all_values.append(value)

    series = [
        AnalyticsSeries(label=label, points=points) for label, points in series_map.items()
    ]

    summary = AnalyticsSummary(
        min=round(min(all_values), 4) if all_values else None,
        max=round(max(all_values), 4) if all_values else None,
        avg=round(sum(all_values) / len(all_values), 4) if all_values else None,
        total_points=len(all_values),
    )

    return AnalyticsQueryResponse(series=series, summary=summary)


@router.get("/export")
async def export_analytics_csv(
    metric: str = Query(..., min_length=1),
    aggregation: Literal["avg", "min", "max", "p95", "sum", "count"] = Query("avg"),
    time_range: Literal["1h", "6h", "24h", "7d", "30d"] = Query("24h"),
    group_by: str | None = Query(None),
    device_ids: str | None = Query(None, description="Comma-separated device IDs"),
    group_id: str | None = Query(None),
    pool=Depends(get_db_pool),
):
    """Export analytics query results as CSV."""
    device_id_list = (
        [d.strip() for d in device_ids.split(",") if d.strip()] if device_ids else None
    )

    body = AnalyticsQueryRequest(
        metric=metric,
        aggregation=aggregation,
        time_range=time_range,
        group_by=group_by if group_by in ("device", "site", "group") else None,
        device_ids=device_id_list,
        group_id=group_id,
    )
    result = await run_analytics_query(body, pool)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["label", "time", "value"])

    for s in result.series:
        for point in s.points:
            writer.writerow([s.label, point.time, point.value if point.value is not None else ""])

    output.seek(0)
    filename = f"analytics_{metric}_{aggregation}_{time_range}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

