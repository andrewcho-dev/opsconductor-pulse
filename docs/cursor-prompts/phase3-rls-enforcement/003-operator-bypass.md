# Task 003: Operator Bypass with Audit

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Operators bypass RLS using the `pulse_operator` role. This cross-tenant access must be audited for security and compliance. Every operator query should log what was accessed.

**Read first**:
- `services/ui_iot/db/pool.py` (operator_connection wrapper)
- `services/ui_iot/routes/operator.py` (current audit logging)
- `services/ui_iot/db/audit.py` (audit functions)

**Depends on**: Task 002 (connection wrappers)

## Task

### 3.1 Enhance audit logging for RLS bypass

The `operator_audit_log` table already exists. We need to ensure:
1. Every operator route logs access BEFORE executing queries
2. Logs capture the RLS bypass context
3. No operator query executes without an audit entry

### 3.2 Update audit function

Modify `services/ui_iot/db/audit.py`:

Add a field to track RLS bypass:
```python
async def log_operator_access(
    conn,
    user_id: str,
    action: str,
    tenant_filter: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    rls_bypassed: bool = True  # New field
) -> None:
```

**Note**: The audit log table may need a new column. If so, create migration `005_audit_rls_bypass.sql`:
```sql
ALTER TABLE operator_audit_log ADD COLUMN IF NOT EXISTS rls_bypassed BOOLEAN DEFAULT true;
```

### 3.3 Verify all operator routes log before query

Check each operator route in `services/ui_iot/routes/operator.py`:

**Pattern to enforce**:
```python
@router.get("/devices")
async def list_all_devices(request: Request, ...):
    user = get_user()
    ip, user_agent = get_request_metadata(request)
    pool = request.app.state.pool

    # 1. Log BEFORE query (use regular connection for audit)
    async with pool.acquire() as conn:
        await log_operator_access(
            conn,
            user_id=user["sub"],
            action="list_all_devices",
            tenant_filter=tenant_filter,
            ip_address=ip,
            user_agent=user_agent,
            rls_bypassed=True
        )

    # 2. Execute query with operator connection
    async with operator_connection(pool) as conn:
        devices = await conn.fetch("SELECT * FROM device_state ...")

    return {"devices": devices}
```

**Important**: Audit logging uses a regular connection (not operator_connection) because the audit table is not subject to RLS.

### 3.4 Routes to verify

Ensure these operator routes all log before querying:

| Route | Action to log |
|-------|---------------|
| `GET /operator/dashboard` | `view_dashboard` |
| `GET /operator/devices` | `list_all_devices` |
| `GET /operator/tenants/{tid}/devices` | `list_tenant_devices` |
| `GET /operator/tenants/{tid}/devices/{did}` | `view_device` |
| `GET /operator/alerts` | `list_all_alerts` |
| `GET /operator/quarantine` | `view_quarantine` |
| `GET /operator/integrations` | `list_all_integrations` |
| `GET /operator/settings` | `view_settings` |
| `POST /operator/settings` | `update_settings` |

### 3.5 Add audit query for compliance

Add function to `services/ui_iot/db/audit.py`:

```python
async def fetch_operator_audit_log(
    conn,
    user_id: str | None = None,
    action: str | None = None,
    since: datetime | None = None,
    limit: int = 100
) -> list[dict]:
    """Fetch audit log entries for compliance review."""
    query = """
        SELECT id, user_id, action, tenant_filter, resource_type,
               resource_id, ip_address, user_agent, rls_bypassed, created_at
        FROM operator_audit_log
        WHERE ($1::text IS NULL OR user_id = $1)
          AND ($2::text IS NULL OR action = $2)
          AND ($3::timestamptz IS NULL OR created_at >= $3)
        ORDER BY created_at DESC
        LIMIT $4
    """
    return await conn.fetch(query, user_id, action, since, limit)
```

### 3.6 Add audit endpoint for operator_admin

Add to `services/ui_iot/routes/operator.py`:

```python
@router.get("/audit-log", dependencies=[Depends(require_operator_admin)])
async def get_audit_log(
    request: Request,
    user_id: str | None = None,
    action: str | None = None,
    since: str | None = None,
    limit: int = Query(default=100, le=1000)
):
    """View operator audit log (operator_admin only)."""
    # ... implementation
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `db/migrations/005_audit_rls_bypass.sql` (if column needed) |
| MODIFY | `services/ui_iot/db/audit.py` |
| MODIFY | `services/ui_iot/routes/operator.py` |

## Acceptance Criteria

- [ ] Every operator route logs to `operator_audit_log` before querying
- [ ] Audit entries include `rls_bypassed=true` for operator queries
- [ ] `GET /operator/audit-log` returns audit entries (operator_admin only)
- [ ] Audit log captures user_id, action, timestamp for all operator access
- [ ] No operator query can execute without an audit entry

**Test**:
```bash
# 1. Access operator route
curl -H "Authorization: Bearer <operator_token>" http://localhost:8080/operator/devices

# 2. Check audit log
docker exec -i iot-postgres psql -U iot -d iotcloud -c \
  "SELECT user_id, action, rls_bypassed, created_at FROM operator_audit_log ORDER BY created_at DESC LIMIT 5;"

# 3. Verify entry exists for the request
```

## Commit

```
Enhance operator audit logging for RLS bypass

- Add rls_bypassed column to audit log
- Ensure all operator routes log before querying
- Add fetch_operator_audit_log for compliance
- Add GET /operator/audit-log endpoint (admin only)
- Every RLS bypass is now auditable

Part of Phase 3: RLS Enforcement
```
