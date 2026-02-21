# Task 2: Add Provisioning and Plan Discovery Endpoints

## File
`services/ui_iot/routes/carrier.py`

## Context

The existing `carrier.py` routes file has 7 endpoints (lines 86-568). We need to add 2 more:
1. `POST /devices/{device_id}/carrier/provision` — Provision/claim a new SIM for a device
2. `GET /carrier/integrations/{integration_id}/plans` — List available plans from a carrier

The file already imports everything needed: `get_carrier_provider`, `require_permission`, `check_account_feature`, `is_operator`, `_carrier_call_error`, `_load_integration`, `tenant_connection`, `get_tenant_id`, `get_db_pool`, Pydantic `BaseModel`, etc.

## Changes

### 1. Add ProvisionRequest Pydantic model

Add this after the existing `CarrierLinkRequest` model (line 84):

```python
class ProvisionRequest(BaseModel):
    carrier_integration_id: int
    iccid: str = Field(..., min_length=15, max_length=22)
    plan_id: int | None = None
```

### 2. Add provision endpoint

Add this endpoint after the existing `link_device_to_carrier` endpoint (after line 568). It should be placed logically near the `link` endpoint since they're related:

```python
@router.post(
    "/devices/{device_id}/carrier/provision",
    dependencies=[require_permission("carrier.links.write")],
)
async def provision_device_sim(
    device_id: str, body: ProvisionRequest, pool=Depends(get_db_pool)
):
    """Claim a new SIM from the carrier and link it to this device."""
    tenant_id = get_tenant_id()
    if not is_operator():
        async with tenant_connection(pool, tenant_id) as conn:
            gate = await check_account_feature(conn, tenant_id, "carrier_self_service")
            if not gate["allowed"]:
                raise HTTPException(status_code=403, detail=gate["message"])

    async with tenant_connection(pool, tenant_id) as conn:
        integration = await _load_integration(conn, tenant_id, body.carrier_integration_id)
        if not integration:
            raise HTTPException(status_code=400, detail="Invalid carrier_integration_id")

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            claim_result = await provider.claim_sim(body.iccid, body.plan_id)
        except Exception as e:
            raise _carrier_call_error(e)

        # Extract the carrier device ID from the claim response
        carrier_device_id = str(
            claim_result.get("id")
            or claim_result.get("device_id")
            or claim_result.get("deviceid")
            or ""
        )
        if not carrier_device_id:
            raise HTTPException(
                status_code=502,
                detail="Carrier claim succeeded but no device ID returned",
            )

        # Create or update the device_connections row
        try:
            await conn.execute(
                """
                INSERT INTO device_connections (tenant_id, device_id, carrier_integration_id, carrier_device_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (tenant_id, device_id)
                DO UPDATE SET
                    carrier_integration_id = EXCLUDED.carrier_integration_id,
                    carrier_device_id = EXCLUDED.carrier_device_id,
                    updated_at = now()
                """,
                tenant_id,
                device_id,
                body.carrier_integration_id,
                carrier_device_id,
            )
        except asyncpg.UndefinedColumnError:
            raise HTTPException(
                status_code=400,
                detail="carrier link columns not available; apply migration 106 first",
            )

    return {
        "provisioned": True,
        "device_id": device_id,
        "carrier_device_id": carrier_device_id,
        "carrier_integration_id": body.carrier_integration_id,
        "iccid": body.iccid,
        "claim_result": claim_result,
    }
```

### 3. Add plans listing endpoint

Add this endpoint after the existing `list_carrier_integrations` endpoint (logically grouped with integration management):

```python
@router.get("/carrier/integrations/{integration_id}/plans")
async def list_carrier_plans(integration_id: int, pool=Depends(get_db_pool)):
    """List available data plans from the carrier for this integration."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        integration = await _load_integration(conn, tenant_id, integration_id)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        provider = get_carrier_provider(integration)
        if not provider:
            raise HTTPException(status_code=400, detail="Unsupported carrier provider")

        try:
            plans = await provider.list_plans()
        except NotImplementedError:
            return {"plans": [], "note": "Plan listing not supported for this carrier"}
        except Exception as e:
            raise _carrier_call_error(e)

    return {"plans": plans, "carrier_name": integration.get("carrier_name")}
```

## Notes

- The provision endpoint reuses the same `carrier.links.write` permission and `carrier_self_service` feature gate as the existing `link_device_to_carrier` endpoint — consistent access control.
- The plans endpoint has no extra permission requirement (read-only, same as `list_carrier_integrations`).
- The provision endpoint handles the carrier-specific device ID extraction with fallbacks (`id`, `device_id`, `deviceid`) since different carrier APIs may return different field names.
- The `NotImplementedError` catch in plans endpoint gracefully handles carriers (like 1NCE) that don't support plan listing.

## Verification

```bash
# Check route registration
cd services/ui_iot && python -c "
from routes.carrier import router
routes = [(r.path, r.methods) for r in router.routes]
assert any('/devices/{device_id}/carrier/provision' in r[0] for r in routes), 'provision route missing'
assert any('/carrier/integrations/{integration_id}/plans' in r[0] for r in routes), 'plans route missing'
print('Routes registered:', routes)
"
```
