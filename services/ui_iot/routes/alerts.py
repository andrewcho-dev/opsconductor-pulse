"""Alert and alert rule management routes."""

from routes.customer import *  # noqa: F401,F403
from routes.customer import _normalize_optional_ids
from routes.customer import _with_rule_conditions

router = APIRouter(
    prefix="/customer",
    tags=["alerts"],
    dependencies=[
        Depends(JWTBearer()),
        Depends(inject_tenant_context),
        Depends(require_customer),
    ],
)

@router.get("/alert-digest-settings")
async def get_alert_digest_settings(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT frequency, email, last_sent_at
                FROM alert_digest_settings
                WHERE tenant_id = $1
                """,
                tenant_id,
            )
    except Exception:
        logger.exception("Failed to fetch alert digest settings")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        return {"frequency": "daily", "email": "", "last_sent_at": None}
    return {
        "frequency": row["frequency"],
        "email": row["email"],
        "last_sent_at": row["last_sent_at"],
    }


@router.put("/alert-digest-settings")
async def put_alert_digest_settings(
    body: AlertDigestSettingsUpdate,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            await conn.execute(
                """
                INSERT INTO alert_digest_settings (tenant_id, frequency, email)
                VALUES ($1, $2, $3)
                ON CONFLICT (tenant_id)
                DO UPDATE SET
                    frequency = EXCLUDED.frequency,
                    email = EXCLUDED.email,
                    updated_at = now()
                """,
                tenant_id,
                body.frequency,
                body.email.strip(),
            )
    except Exception:
        logger.exception("Failed to upsert alert digest settings")
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"ok": True}


@router.get("/alerts")
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def list_alerts(
    request: Request,
    response: Response,
    status: str = Query("OPEN"),  # OPEN | ACKNOWLEDGED | CLOSED | ALL
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    valid = {"OPEN", "ACKNOWLEDGED", "CLOSED", "ALL"}
    status_filter = status.upper()
    if status_filter not in valid:
        raise HTTPException(status_code=400, detail="Invalid status")

    tenant_id = get_tenant_id()
    try:
        where = "tenant_id = $1" if status_filter == "ALL" else "tenant_id = $1 AND status = $2"
        params = [tenant_id] if status_filter == "ALL" else [tenant_id, status_filter]
        async with tenant_connection(pool, tenant_id) as conn:
            rows = await conn.fetch(
                f"""
                SELECT id AS alert_id, tenant_id, created_at, closed_at, device_id, site_id, alert_type,
                       fingerprint, status, severity, confidence, summary, details,
                       silenced_until, acknowledged_by, acknowledged_at,
                       escalation_level, escalated_at
                FROM fleet_alert
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
                """,
                *params,
            )
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM fleet_alert WHERE {where}",
                *params,
            )
    except Exception:
        logger.exception("Failed to fetch tenant alerts")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "tenant_id": tenant_id,
        "alerts": [dict(r) for r in rows],
        "total": int(total or 0),
        "status_filter": status_filter,
        "limit": limit,
        "offset": offset,
    }


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
                       severity, confidence, summary, status, created_at
                FROM fleet_alert
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                alert_id,
            )
    except Exception:
        logger.exception("Failed to fetch tenant alert")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"tenant_id": tenant_id, "alert": dict(row)}


@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_customer)])
async def acknowledge_alert(alert_id: str, request: Request, pool=Depends(get_db_pool)):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    user = get_user() or {}
    user_ref = user.get("email") or user.get("preferred_username") or user.get("sub", "unknown")
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'ACKNOWLEDGED',
                acknowledged_by = $3,
                acknowledged_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status = 'OPEN'
            RETURNING id, status
            """,
            tenant_id,
            alert_id_int,
            user_ref,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or not OPEN")

    logger.info(
        "alert acknowledged",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
            "acknowledged_by": user_ref,
        },
    )
    return {"alert_id": alert_id, "status": "ACKNOWLEDGED", "acknowledged_by": user_ref}


@router.patch("/alerts/{alert_id}/close", dependencies=[Depends(require_customer)])
async def close_alert_endpoint(alert_id: str, request: Request, pool=Depends(get_db_pool)):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET status = 'CLOSED', closed_at = now()
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, status
            """,
            tenant_id,
            alert_id_int,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or already closed")

    logger.info(
        "alert closed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
        },
    )
    return {"alert_id": alert_id, "status": "CLOSED"}


@router.patch("/alerts/{alert_id}/silence", dependencies=[Depends(require_customer)])
async def silence_alert(
    alert_id: str,
    body: SilenceRequest,
    request: Request,
    pool=Depends(get_db_pool),
):
    try:
        alert_id_int = int(alert_id)
        if alert_id_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid alert_id")

    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            UPDATE fleet_alert
            SET silenced_until = now() + ($3 || ' minutes')::interval
            WHERE tenant_id = $1 AND id = $2 AND status IN ('OPEN', 'ACKNOWLEDGED')
            RETURNING id, silenced_until
            """,
            tenant_id,
            alert_id_int,
            str(body.minutes),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found or closed")

    silenced_until = row["silenced_until"]
    logger.info(
        "alert silenced",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "tenant_id": tenant_id,
            "alert_id": alert_id_int,
            "minutes": body.minutes,
            "silenced_until": silenced_until.isoformat() if silenced_until else None,
        },
    )
    return {"alert_id": alert_id, "silenced_until": silenced_until.isoformat()}


@router.get("/alert-rule-templates", dependencies=[Depends(require_customer)])
async def list_alert_rule_templates(device_type: str | None = Query(None)):
    templates = ALERT_RULE_TEMPLATES
    if device_type:
        templates = [tmpl for tmpl in templates if tmpl["device_type"] == device_type]
    return {"templates": templates, "total": len(templates)}


@router.post("/alert-rule-templates/apply", dependencies=[Depends(require_customer)])
@limiter.limit(CUSTOMER_RATE_LIMIT)
async def apply_alert_rule_templates(
    request: Request,
    response: Response,
    body: ApplyTemplatesRequest,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()
    template_map = {tmpl["template_id"]: tmpl for tmpl in ALERT_RULE_TEMPLATES}

    requested = [template_map[tid] for tid in body.template_ids if tid in template_map]
    if not requested:
        raise HTTPException(status_code=400, detail="No valid template_ids provided")

    created = []
    skipped = []

    async with tenant_connection(pool, tenant_id) as conn:
        for tmpl in requested:
            existing = await conn.fetchval(
                "SELECT id FROM alert_rules WHERE tenant_id = $1 AND name = $2",
                tenant_id,
                tmpl["name"],
            )
            if existing:
                skipped.append(tmpl["template_id"])
                continue

            row = await conn.fetchrow(
                """
                INSERT INTO alert_rules
                    (tenant_id, name, description, metric_name, operator, threshold,
                     severity, duration_seconds, device_type, site_ids, enabled)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,true)
                RETURNING id, name
                """,
                tenant_id,
                tmpl["name"],
                tmpl["description"],
                tmpl["metric_name"],
                tmpl["operator"],
                tmpl["threshold"],
                tmpl["severity"],
                tmpl["duration_seconds"],
                tmpl["device_type"],
                body.site_ids or None,
            )
            created.append(
                {"id": row["id"], "name": row["name"], "template_id": tmpl["template_id"]}
            )

    return {"created": created, "skipped": skipped}


@router.get("/alert-rules")
async def list_alert_rules(pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rules = await fetch_alert_rules(conn, tenant_id)
    except Exception:
        logger.exception("Failed to fetch alert rules")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"tenant_id": tenant_id, "rules": [_with_rule_conditions(rule) for rule in rules]}


@router.get("/alert-rules/{rule_id}")
async def get_alert_rule(rule_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await fetch_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to fetch alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return _with_rule_conditions(rule)


@router.post("/alert-rules", dependencies=[Depends(require_customer_admin)])
async def create_alert_rule_endpoint(request: Request, body: AlertRuleCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    conditions_json = None
    match_mode = body.match_mode
    conditions_list = None
    if isinstance(body.conditions, list):
        conditions_json = [condition.model_dump() for condition in body.conditions]
        conditions_list = conditions_json
    elif body.conditions is not None:
        conditions_obj = body.conditions.model_dump()
        conditions_json = conditions_obj
        conditions_list = conditions_obj.get("conditions")
        if body.match_mode == "all":
            match_mode = "any" if conditions_obj.get("combinator") == "OR" else "all"
    anomaly_conditions_json = (
        body.anomaly_conditions.model_dump() if body.anomaly_conditions else None
    )
    gap_conditions_json = body.gap_conditions.model_dump() if body.gap_conditions else None
    rule_type = body.rule_type

    if rule_type == "anomaly":
        if anomaly_conditions_json is None:
            raise HTTPException(status_code=422, detail="anomaly_conditions is required")
        metric_name = anomaly_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(anomaly_conditions_json["z_threshold"])
        conditions_payload = anomaly_conditions_json
    elif rule_type == "telemetry_gap":
        if gap_conditions_json is None:
            raise HTTPException(status_code=422, detail="gap_conditions is required")
        metric_name = gap_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(gap_conditions_json["gap_minutes"])
        conditions_payload = gap_conditions_json
    elif conditions_list:
        first_condition = conditions_list[0]
        metric_name = first_condition["metric_name"]
        operator = first_condition["operator"]
        threshold = first_condition["threshold"]
        for cond in conditions_list:
            if cond["operator"] not in VALID_OPERATORS:
                raise HTTPException(status_code=400, detail="Invalid operator value")
            if not METRIC_NAME_PATTERN.match(cond["metric_name"]):
                raise HTTPException(status_code=400, detail="Invalid metric_name format")
        conditions_payload = conditions_json
    else:
        if body.operator not in VALID_OPERATORS:
            raise HTTPException(status_code=400, detail="Invalid operator value")
        if body.metric_name is None or not METRIC_NAME_PATTERN.match(body.metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        if body.threshold is None:
            raise HTTPException(status_code=400, detail="threshold is required")
        metric_name = body.metric_name
        operator = body.operator
        threshold = body.threshold
        conditions_payload = None

    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")
    group_ids = _normalize_optional_ids(body.group_ids, "group_ids")
    duration_minutes = body.duration_minutes
    duration_seconds = body.duration_seconds
    if duration_minutes is not None:
        duration_seconds = duration_minutes * 60
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await create_alert_rule(
                conn,
                tenant_id=tenant_id,
                name=body.name,
                rule_type=rule_type,
                metric_name=metric_name,
                operator=operator,
                threshold=threshold,
                severity=body.severity,
                duration_seconds=duration_seconds,
                duration_minutes=duration_minutes,
                description=body.description,
                site_ids=body.site_ids,
                group_ids=group_ids,
                conditions=conditions_payload,
                match_mode=match_mode,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to create alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    audit = getattr(request.app.state, "audit", None)
    if audit:
        user = get_user()
        username = (
            user.get("preferred_username")
            or user.get("email")
            or user.get("sub")
            or "unknown"
        )
        audit.config_changed(
            tenant_id,
            "rule",
            rule.get("rule_id"),
            "create",
            body.name,
            user_id=user.get("sub") or "unknown",
            username=username,
            ip_address=request.client.host if request.client else None,
            details={"metric": metric_name, "threshold": threshold},
        )
    return JSONResponse(status_code=201, content=jsonable_encoder(_with_rule_conditions(rule)))


@router.patch("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def update_alert_rule_endpoint(rule_id: str, body: AlertRuleUpdate, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    if (
        body.name is None
        and body.rule_type is None
        and body.metric_name is None
        and body.operator is None
        and body.threshold is None
        and body.severity is None
        and body.duration_seconds is None
        and body.description is None
        and body.site_ids is None
        and body.group_ids is None
        and body.conditions is None
        and body.match_mode is None
        and body.anomaly_conditions is None
        and body.gap_conditions is None
        and body.enabled is None
    ):
        raise HTTPException(status_code=400, detail="No fields to update")

    conditions_json = None
    match_mode = body.match_mode
    conditions_list = None
    if isinstance(body.conditions, list):
        conditions_json = [condition.model_dump() for condition in body.conditions]
        conditions_list = conditions_json
    elif body.conditions is not None:
        conditions_obj = body.conditions.model_dump()
        conditions_json = conditions_obj
        conditions_list = conditions_obj.get("conditions")
        if body.match_mode is None:
            match_mode = "any" if conditions_obj.get("combinator") == "OR" else "all"
    anomaly_conditions_json = (
        body.anomaly_conditions.model_dump() if body.anomaly_conditions else None
    )
    gap_conditions_json = body.gap_conditions.model_dump() if body.gap_conditions else None
    if body.rule_type == "anomaly":
        if anomaly_conditions_json is None:
            raise HTTPException(status_code=422, detail="anomaly_conditions is required")
        metric_name = anomaly_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(anomaly_conditions_json["z_threshold"])
        conditions_payload = anomaly_conditions_json
    elif body.rule_type == "telemetry_gap":
        if gap_conditions_json is None:
            raise HTTPException(status_code=422, detail="gap_conditions is required")
        metric_name = gap_conditions_json["metric_name"]
        if not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
        operator = "GT"
        threshold = float(gap_conditions_json["gap_minutes"])
        conditions_payload = gap_conditions_json
    elif conditions_list:
        for cond in conditions_list:
            if cond["operator"] not in VALID_OPERATORS:
                raise HTTPException(status_code=400, detail="Invalid operator value")
            if not METRIC_NAME_PATTERN.match(cond["metric_name"]):
                raise HTTPException(status_code=400, detail="Invalid metric_name format")
        first_condition = conditions_list[0]
        metric_name = first_condition["metric_name"]
        operator = first_condition["operator"]
        threshold = first_condition["threshold"]
        conditions_payload = conditions_json
    else:
        metric_name = body.metric_name
        operator = body.operator
        threshold = body.threshold
        conditions_payload = None
        if operator is not None and operator not in VALID_OPERATORS:
            raise HTTPException(status_code=400, detail="Invalid operator value")
        if metric_name is not None and not METRIC_NAME_PATTERN.match(metric_name):
            raise HTTPException(status_code=400, detail="Invalid metric_name format")
    if body.site_ids is not None:
        for site_id in body.site_ids:
            if site_id is None or not str(site_id).strip():
                raise HTTPException(status_code=400, detail="Invalid site_id value")
    group_ids = _normalize_optional_ids(body.group_ids, "group_ids")
    duration_minutes = body.duration_minutes
    duration_seconds = body.duration_seconds
    if duration_minutes is not None:
        duration_seconds = duration_minutes * 60

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            rule = await update_alert_rule(
                conn,
                tenant_id=tenant_id,
                rule_id=rule_id,
                name=body.name,
                rule_type=body.rule_type,
                metric_name=metric_name,
                operator=operator,
                threshold=threshold,
                severity=body.severity,
                duration_seconds=duration_seconds,
                duration_minutes=duration_minutes,
                description=body.description,
                site_ids=body.site_ids,
                group_ids=group_ids,
                conditions=conditions_payload,
                match_mode=match_mode,
                enabled=body.enabled,
            )
    except Exception:
        logger.exception("Failed to update alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return _with_rule_conditions(rule)


@router.delete("/alert-rules/{rule_id}", dependencies=[Depends(require_customer_admin)])
async def delete_alert_rule_endpoint(rule_id: str, pool=Depends(get_db_pool)):
    if not validate_uuid(rule_id):
        raise HTTPException(status_code=400, detail="Invalid rule_id format: must be a valid UUID")

    tenant_id = get_tenant_id()
    try:
        p = pool
        async with tenant_connection(p, tenant_id) as conn:
            deleted = await delete_alert_rule(conn, tenant_id, rule_id)
    except Exception:
        logger.exception("Failed to delete alert rule")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return Response(status_code=204)

