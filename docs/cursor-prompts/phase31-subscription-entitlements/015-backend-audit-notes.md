# 015: Backend - Add Notes and Transaction Ref to Subscription Audit

## Task

Update the operator subscription API to accept and log notes and transaction references for audit compliance.

## File to Modify

`services/ui_iot/routes/operator.py`

## Changes Required

### 1. Update SubscriptionUpsert Model

Find the `SubscriptionUpsert` class and add:

```python
class SubscriptionUpsert(BaseModel):
    device_limit: int = Field(..., ge=0)
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None
    plan_id: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(TRIAL|ACTIVE|GRACE|SUSPENDED|EXPIRED)$")
    notes: Optional[str] = None  # Reason for change (required by UI)
    transaction_ref: Optional[str] = None  # External reference (invoice, PO, etc.)
```

### 2. Update the upsert_tenant_subscription Endpoint

Find the `@router.post("/tenants/{tenant_id}/subscription")` endpoint.

Update the audit log insert to include notes and transaction_ref in the details:

```python
# Build details object for audit
audit_details = {}
if data.notes:
    audit_details["notes"] = data.notes
if data.transaction_ref:
    audit_details["transaction_ref"] = data.transaction_ref
if current and data.device_limit != current['device_limit']:
    audit_details["previous_limit"] = current['device_limit']
    audit_details["new_limit"] = data.device_limit
if current and data.status and data.status != current['status']:
    audit_details["previous_status"] = current['status']
    audit_details["new_status"] = data.status

# Audit log
await conn.execute(
    """
    INSERT INTO subscription_audit
        (tenant_id, event_type, actor_type, actor_id, previous_state, new_state, details, ip_address)
    VALUES ($1, $2, 'admin', $3, $4, $5, $6, $7)
    """,
    tenant_id,
    event_type,
    user.get('sub') if user else None,
    json.dumps(previous_state, default=str) if previous_state else None,
    json.dumps(new_state, default=str),
    json.dumps(audit_details) if audit_details else None,
    ip
)
```

### 3. Return More Info in Response

Update the response to confirm what was logged:

```python
return {
    "tenant_id": row['tenant_id'],
    "device_limit": row['device_limit'],
    "term_end": row['term_end'].isoformat() if row['term_end'] else None,
    "status": row['status'],
    "event_type": event_type,
    "notes_logged": bool(data.notes),
    "transaction_ref_logged": bool(data.transaction_ref),
    "updated": True,
}
```

## Verification

After changes, test:

```bash
curl -X POST /operator/tenants/tenant-a/subscription \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_limit": 100,
    "status": "ACTIVE",
    "notes": "Extended subscription per invoice INV-2024-001",
    "transaction_ref": "INV-2024-001"
  }'
```

Check audit log:
```sql
SELECT event_type, actor_id, details, event_timestamp
FROM subscription_audit
WHERE tenant_id = 'tenant-a'
ORDER BY event_timestamp DESC
LIMIT 5;
```

Should show `details` containing notes and transaction_ref.
