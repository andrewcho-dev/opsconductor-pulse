# Phase 90 — Backend: CSV/JSON Export Endpoints

## Add to `services/ui_iot/routes/customer.py`

### GET /customer/export/devices

Query params:
- `format: str = Query("csv")` — `"csv"` or `"json"`
- `status: Optional[str] = None` — filter by device status
- `site_id: Optional[str] = None` — filter by site

Logic:
1. Fetch all devices for tenant (no pagination — full export)
2. If `format == "csv"`:
   - Use `io.StringIO` + `csv.DictWriter`
   - Columns: `device_id, name, model, status, site_id, last_seen_at, tags`
   - `tags` serialized as `key=value,key=value` string
   - Return `StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
     headers={"Content-Disposition": f'attachment; filename="devices-{date}.csv"})`
3. If `format == "json"`:
   - Return `JSONResponse({"devices": [...], "count": N})`
4. Record in `report_runs`:
   ```python
   await conn.execute(
       "INSERT INTO report_runs (tenant_id, report_type, status, triggered_by, row_count, completed_at) "
       "VALUES ($1, 'device_export', 'done', $2, $3, NOW())",
       tenant_id, f"user:{user_id}", row_count
   )
   ```

### GET /customer/export/alerts

Query params:
- `format: str = Query("csv")` — `"csv"` or `"json"`
- `status: str = Query("ALL")` — `OPEN | ACKNOWLEDGED | CLOSED | ALL`
- `days: int = Query(7, ge=1, le=365)` — look-back window

Logic:
1. Fetch alerts WHERE `created_at >= NOW() - INTERVAL '{days} days'`
   and status matches (skip status filter if `ALL`)
2. CSV columns: `alert_id, device_id, alert_type, severity, status, created_at,
   acknowledged_at, closed_at, summary`
3. Return StreamingResponse or JSONResponse, same pattern as above
4. Record in `report_runs` with `report_type = 'alert_export'`
