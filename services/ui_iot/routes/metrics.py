"""Metric catalog, normalized metrics, and metric mapping routes."""

from routes.customer import *  # noqa: F401,F403

router = APIRouter(
    prefix="/api/v1/customer",
    tags=["metrics"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)


@router.get("/metrics/reference")
async def get_metrics_reference(pool=Depends(get_db_pool)):
    """Return discovered raw metrics, mappings, and normalized metrics."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            raw_rows = await conn.fetch(
                """
                SELECT DISTINCT key AS metric_name
                FROM telemetry
                CROSS JOIN LATERAL jsonb_object_keys(metrics) AS key
                WHERE tenant_id = $1
                  AND time > NOW() - INTERVAL '7 days'
                  AND metrics IS NOT NULL
                  AND jsonb_typeof(metrics) = 'object'
                ORDER BY metric_name
                LIMIT 200
                """,
                tenant_id,
            )
            mapping_rows = await conn.fetch(
                """
                SELECT raw_metric, normalized_name
                FROM metric_mappings
                WHERE tenant_id = $1
                """,
                tenant_id,
            )
            normalized_rows = await conn.fetch(
                """
                SELECT normalized_name, display_unit, description, expected_min, expected_max
                FROM normalized_metrics
                WHERE tenant_id = $1
                ORDER BY normalized_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch metrics reference")
        raise HTTPException(status_code=500, detail="Internal server error")

    raw_metrics = [r["metric_name"] for r in raw_rows]
    mapping_by_raw = {r["raw_metric"]: r["normalized_name"] for r in mapping_rows}
    mapped_from: dict[str, list[str]] = {}
    for row in mapping_rows:
        mapped_from.setdefault(row["normalized_name"], []).append(row["raw_metric"])

    normalized_metrics = [
        {
            "name": row["normalized_name"],
            "display_unit": row["display_unit"],
            "description": row["description"],
            "expected_min": row["expected_min"],
            "expected_max": row["expected_max"],
            "mapped_from": sorted(mapped_from.get(row["normalized_name"], [])),
        }
        for row in normalized_rows
    ]

    raw_metrics_response = [
        {"name": name, "mapped_to": mapping_by_raw.get(name)}
        for name in raw_metrics
    ]
    unmapped = [name for name in raw_metrics if name not in mapping_by_raw]

    return {
        "raw_metrics": raw_metrics_response,
        "normalized_metrics": normalized_metrics,
        "unmapped": unmapped,
    }


@router.get("/metrics/catalog")
async def list_metric_catalog(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT metric_name, description, unit, expected_min, expected_max,
                       created_at, updated_at
                FROM metric_catalog
                WHERE tenant_id = $1
                ORDER BY metric_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch metric catalog")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metrics": [dict(r) for r in rows]}


@router.post("/metrics/catalog", dependencies=[Depends(require_customer_admin)])
async def upsert_metric_catalog(payload: MetricCatalogUpsert, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    metric_name = payload.metric_name.strip()
    if not metric_name:
        raise HTTPException(status_code=400, detail="metric_name is required")
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO metric_catalog (
                    tenant_id, metric_name, description, unit, expected_min, expected_max
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, metric_name)
                DO UPDATE SET
                    description = EXCLUDED.description,
                    unit = EXCLUDED.unit,
                    expected_min = EXCLUDED.expected_min,
                    expected_max = EXCLUDED.expected_max,
                    updated_at = NOW()
                RETURNING metric_name, description, unit, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                metric_name,
                payload.description,
                payload.unit,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to upsert metric catalog entry")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.delete("/metrics/catalog/{metric_name}", dependencies=[Depends(require_customer_admin)])
async def delete_metric_catalog(metric_name: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM metric_catalog
                WHERE tenant_id = $1 AND metric_name = $2
                """,
                tenant_id,
                metric_name,
            )
    except Exception:
        logger.exception("Failed to delete metric catalog entry")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not check_delete_result(result):
        raise HTTPException(status_code=404, detail="Metric not found")

    return Response(status_code=204)


@router.get("/normalized-metrics")
async def list_normalized_metrics(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rows = await conn.fetch(
                """
                SELECT normalized_name, display_unit, description, expected_min, expected_max,
                       created_at, updated_at
                FROM normalized_metrics
                WHERE tenant_id = $1
                ORDER BY normalized_name
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch normalized metrics")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "metrics": [dict(r) for r in rows]}


@router.post("/normalized-metrics", dependencies=[Depends(require_customer_admin)])
async def create_normalized_metric(payload: NormalizedMetricCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(payload.normalized_name)
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO normalized_metrics (
                    tenant_id, normalized_name, display_unit, description, expected_min, expected_max
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, normalized_name)
                DO NOTHING
                RETURNING normalized_name, display_unit, description, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                normalized_name,
                payload.display_unit,
                payload.description,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to create normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=409, detail="Normalized metric already exists")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.patch("/normalized-metrics/{name}", dependencies=[Depends(require_customer_admin)])
async def update_normalized_metric(name: str, payload: NormalizedMetricUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(name)
    if payload.expected_min is not None and payload.expected_max is not None:
        if payload.expected_min > payload.expected_max:
            raise HTTPException(status_code=400, detail="expected_min must be <= expected_max")
    if (
        payload.display_unit is None
        and payload.description is None
        and payload.expected_min is None
        and payload.expected_max is None
    ):
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE normalized_metrics
                SET display_unit = $3,
                    description = $4,
                    expected_min = $5,
                    expected_max = $6,
                    updated_at = NOW()
                WHERE tenant_id = $1 AND normalized_name = $2
                RETURNING normalized_name, display_unit, description, expected_min, expected_max,
                          created_at, updated_at
                """,
                tenant_id,
                normalized_name,
                payload.display_unit,
                payload.description,
                payload.expected_min,
                payload.expected_max,
            )
    except Exception:
        logger.exception("Failed to update normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Normalized metric not found")

    return {"tenant_id": tenant_id, "metric": dict(row)}


@router.delete("/normalized-metrics/{name}", dependencies=[Depends(require_customer_admin)])
async def delete_normalized_metric(name: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    normalized_name = _validate_name(name)
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM normalized_metrics
                WHERE tenant_id = $1 AND normalized_name = $2
                """,
                tenant_id,
                normalized_name,
            )
    except Exception:
        logger.exception("Failed to delete normalized metric")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not check_delete_result(result):
        raise HTTPException(status_code=404, detail="Normalized metric not found")

    return Response(status_code=204)


@router.get("/metric-mappings")
async def list_metric_mappings(normalized_name: str | None = Query(None), pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            if normalized_name:
                normalized_name = _validate_name(normalized_name)
                rows = await conn.fetch(
                    """
                    SELECT raw_metric, normalized_name, multiplier, offset_value, created_at
                    FROM metric_mappings
                    WHERE tenant_id = $1 AND normalized_name = $2
                    ORDER BY raw_metric
                    """,
                    tenant_id,
                    normalized_name,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT raw_metric, normalized_name, multiplier, offset_value, created_at
                    FROM metric_mappings
                    WHERE tenant_id = $1
                    ORDER BY raw_metric
                    """,
                    tenant_id,
                )
    except Exception:
        logger.exception("Failed to fetch metric mappings")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "mappings": [dict(r) for r in rows]}


@router.post("/metric-mappings", dependencies=[Depends(require_customer_admin)])
async def create_metric_mapping(payload: MetricMappingCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = payload.raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    normalized_name = _validate_name(payload.normalized_name)
    multiplier = payload.multiplier if payload.multiplier is not None else 1
    offset_value = payload.offset_value if payload.offset_value is not None else 0

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            exists = await conn.fetchval(
                """
                SELECT 1 FROM normalized_metrics
                WHERE tenant_id = $1 AND normalized_name = $2
                """,
                tenant_id,
                normalized_name,
            )
            if not exists:
                raise HTTPException(status_code=404, detail="Normalized metric not found")

            row = await conn.fetchrow(
                """
                INSERT INTO metric_mappings (
                    tenant_id, raw_metric, normalized_name, multiplier, offset_value
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (tenant_id, raw_metric)
                DO UPDATE SET
                    normalized_name = EXCLUDED.normalized_name,
                    multiplier = EXCLUDED.multiplier,
                    offset_value = EXCLUDED.offset_value
                RETURNING raw_metric, normalized_name, multiplier, offset_value, created_at
                """,
                tenant_id,
                raw_metric,
                normalized_name,
                multiplier,
                offset_value,
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "mapping": dict(row)}


@router.patch("/metric-mappings/{raw_metric}", dependencies=[Depends(require_customer_admin)])
async def update_metric_mapping(raw_metric: str, payload: MetricMappingUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    if payload.multiplier is None and payload.offset_value is None:
        raise HTTPException(status_code=400, detail="No fields provided")

    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                UPDATE metric_mappings
                SET multiplier = COALESCE($3, multiplier),
                    offset_value = COALESCE($4, offset_value)
                WHERE tenant_id = $1 AND raw_metric = $2
                RETURNING raw_metric, normalized_name, multiplier, offset_value, created_at
                """,
                tenant_id,
                raw_metric,
                payload.multiplier,
                payload.offset_value,
            )
    except Exception:
        logger.exception("Failed to update metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Metric mapping not found")

    return {"tenant_id": tenant_id, "mapping": dict(row)}


@router.delete("/metric-mappings/{raw_metric}", dependencies=[Depends(require_customer_admin)])
async def delete_metric_mapping(raw_metric: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    raw_metric = raw_metric.strip()
    if not METRIC_NAME_PATTERN.match(raw_metric):
        raise HTTPException(status_code=400, detail="Invalid raw metric name")
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            result = await conn.execute(
                """
                DELETE FROM metric_mappings
                WHERE tenant_id = $1 AND raw_metric = $2
                """,
                tenant_id,
                raw_metric,
            )
    except Exception:
        logger.exception("Failed to delete metric mapping")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result.endswith("0"):
        raise HTTPException(status_code=404, detail="Metric mapping not found")

    return Response(status_code=204)

