# Prompt 001 — Backend: POST /customer/integrations/{id}/test-send

Read `services/ui_iot/routes/customer.py` — find integration endpoints.
Read `services/delivery_worker/worker.py` — find the SSRF blocklist (blocked IPs/networks for webhook URLs). Reuse the same validation logic.

## Add Test-Send Endpoint

This endpoint:
1. Fetches the integration by id+tenant (must be type='webhook' and enabled)
2. Validates the webhook URL is not SSRF-blocked (reuse worker.py blocklist or inline the check)
3. Sends a synthetic test payload via httpx with a 10s timeout
4. Returns HTTP status code, latency, and success/failure

```python
TEST_PAYLOAD = {
    "test": True,
    "alert_id": 0,
    "site_id": "test-site",
    "device_id": "test-device",
    "alert_type": "TEST",
    "severity": 3,
    "summary": "This is a test notification from OpsConductor/Pulse",
    "status": "OPEN",
    "created_at": None,  # filled with now() at send time
}

@router.post("/integrations/{integration_id}/test-send", dependencies=[Depends(require_customer)])
async def test_send_integration(integration_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT integration_id, type, config_json, enabled
            FROM integrations
            WHERE tenant_id = $1 AND integration_id = $2
            """,
            tenant_id, integration_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Integration not found")
    if row["type"] != "webhook":
        raise HTTPException(status_code=400, detail="Test send only supported for webhook integrations")
    if not row["enabled"]:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    config = row["config_json"] or {}
    url = config.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Webhook URL not configured")

    # SSRF check — validate URL is not RFC1918 / loopback / metadata IP
    # Inline or import from a shared utility. Raise 400 if blocked.

    headers = config.get("headers", {})
    payload = {**TEST_PAYLOAD, "created_at": datetime.utcnow().isoformat() + "Z"}

    import time
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "success": resp.status_code < 400,
            "http_status": resp.status_code,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "success": False,
            "http_status": None,
            "latency_ms": latency_ms,
            "error": str(e),
        }
```

Import `httpx` and `datetime` at the top of the file if not already imported.

## Acceptance Criteria

- [ ] POST /customer/integrations/{id}/test-send exists
- [ ] Returns 404 if integration not found for tenant
- [ ] Returns 400 if type != webhook or disabled
- [ ] Returns 400 if URL is SSRF-blocked
- [ ] Returns `success`, `http_status`, `latency_ms` on success
- [ ] Returns `success=false`, `error` on connection failure
- [ ] `pytest -m unit -v` passes
