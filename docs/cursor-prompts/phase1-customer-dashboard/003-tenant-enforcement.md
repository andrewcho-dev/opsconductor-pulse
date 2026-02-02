# Task 003: Tenant Context and Query Builders

## Context

JWT middleware extracts user claims into `request.state.user`. Now we need helpers to propagate tenant context and query builders that enforce tenant isolation.

**Read first**:
- `docs/TENANT_CONTEXT_CONTRACT.md` (invariants)
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 2.2-2.4: Enforcement Patterns)
- `services/ui_iot/app.py` (see existing query patterns to replace)

**Depends on**: Task 002 (JWT middleware)

## Task

### 3.1 Create `services/ui_iot/middleware/tenant.py`

Implement tenant context propagation using context variables.

**Imports**:
- `contextvars` (ContextVar)
- `fastapi` (Request, HTTPException, Depends)
- `typing` (Optional)

**Context variables**:
- `tenant_context: ContextVar[str | None]` — current tenant_id
- `user_context: ContextVar[dict | None]` — full user payload from JWT

**Functions to implement**:

1. `def set_tenant_context(tenant_id: str | None, user: dict) -> None`:
   - Set both context vars
   - Called by middleware after JWT validation

2. `def get_tenant_id() -> str`:
   - Get tenant_id from context var
   - If None or empty: raise `RuntimeError("Tenant context not set — this is a bug")`
   - Return tenant_id
   - **CRITICAL**: This function must NEVER return None for customer routes

3. `def get_tenant_id_or_none() -> str | None`:
   - Get tenant_id from context var
   - Return it (may be None for operators)
   - Used only in operator routes

4. `def get_user() -> dict`:
   - Get user from context var
   - If None: raise RuntimeError
   - Return user dict

5. `def is_operator() -> bool`:
   - Get user from context
   - Check if `role` in `("operator", "operator_admin")`
   - Return bool

6. `def is_operator_admin() -> bool`:
   - Get user from context
   - Check if `role == "operator_admin"`
   - Return bool

**FastAPI Dependencies**:

7. `async def inject_tenant_context(request: Request) -> None`:
   - Get `user` from `request.state.user`
   - If not present: raise HTTPException(401)
   - Extract `tenant_id` from user (may be None for operators)
   - Call `set_tenant_context(tenant_id, user)`

8. `async def require_customer(request: Request) -> None`:
   - Depends on: `inject_tenant_context`
   - Get user from context
   - If role not in `("customer_viewer", "customer_admin")`: raise HTTPException(403, "Customer access required")

9. `async def require_operator(request: Request) -> None`:
   - Depends on: `inject_tenant_context`
   - If not `is_operator()`: raise HTTPException(403, "Operator access required")

10. `async def require_operator_admin(request: Request) -> None`:
    - Depends on: `inject_tenant_context`
    - If not `is_operator_admin()`: raise HTTPException(403, "Operator admin access required")

### 3.2 Create `services/ui_iot/db/__init__.py`

Empty `__init__.py` to make it a package.

### 3.3 Create `services/ui_iot/db/queries.py`

Query builder functions that REQUIRE tenant_id parameter.

**Imports**:
- `asyncpg`
- `typing` (Optional, List, Dict, Any)

**CRITICAL RULE**: Every function takes `tenant_id: str` as a required parameter. No defaults. No Optional.

**Functions to implement**:

1. `async def fetch_devices(conn, tenant_id: str, limit: int = 100, offset: int = 0) -> List[dict]`:
   ```sql
   SELECT tenant_id, device_id, site_id, status, last_seen_at,
          state->>'battery_pct' AS battery_pct,
          state->>'temp_c' AS temp_c,
          state->>'rssi_dbm' AS rssi_dbm,
          state->>'snr_db' AS snr_db
   FROM device_state
   WHERE tenant_id = $1
   ORDER BY site_id, device_id
   LIMIT $2 OFFSET $3
   ```
   - Validate tenant_id is not empty, raise ValueError if so

2. `async def fetch_device(conn, tenant_id: str, device_id: str) -> dict | None`:
   ```sql
   SELECT tenant_id, device_id, site_id, status, last_seen_at,
          state->>'battery_pct' AS battery_pct,
          state->>'temp_c' AS temp_c,
          state->>'rssi_dbm' AS rssi_dbm,
          state->>'snr_db' AS snr_db
   FROM device_state
   WHERE tenant_id = $1 AND device_id = $2
   ```
   - Validate BOTH tenant_id AND device_id are not empty

3. `async def fetch_device_count(conn, tenant_id: str) -> dict`:
   ```sql
   SELECT
     COUNT(*) AS total,
     COUNT(*) FILTER (WHERE status = 'ONLINE') AS online,
     COUNT(*) FILTER (WHERE status = 'STALE') AS stale
   FROM device_state
   WHERE tenant_id = $1
   ```

4. `async def fetch_alerts(conn, tenant_id: str, status: str = "OPEN", limit: int = 100) -> List[dict]`:
   ```sql
   SELECT alert_id, tenant_id, device_id, site_id, alert_type,
          severity, confidence, summary, status, created_at
   FROM fleet_alert
   WHERE tenant_id = $1 AND status = $2
   ORDER BY created_at DESC
   LIMIT $3
   ```

5. `async def fetch_delivery_attempts(conn, tenant_id: str, limit: int = 20) -> List[dict]`:
   ```sql
   SELECT tenant_id, job_id, attempt_no, ok, http_status,
          latency_ms, error, finished_at
   FROM delivery_attempts
   WHERE tenant_id = $1
   ORDER BY finished_at DESC
   LIMIT $2
   ```

6. `async def fetch_device_events(conn, tenant_id: str, device_id: str, limit: int = 50) -> List[dict]`:
   ```sql
   SELECT ingested_at, accepted, tenant_id, site_id, msg_type,
          payload->>'_reject_reason' AS reject_reason
   FROM raw_events
   WHERE tenant_id = $1 AND device_id = $2
   ORDER BY ingested_at DESC
   LIMIT $3
   ```
   - Validate BOTH tenant_id AND device_id

7. `async def fetch_device_telemetry(conn, tenant_id: str, device_id: str, limit: int = 120) -> List[dict]`:
   ```sql
   SELECT ingested_at,
          (payload->'metrics'->>'battery_pct')::float AS battery_pct,
          (payload->'metrics'->>'temp_c')::float AS temp_c,
          (payload->'metrics'->>'rssi_dbm')::int AS rssi_dbm
   FROM raw_events
   WHERE tenant_id = $1 AND device_id = $2
     AND msg_type = 'telemetry' AND accepted = true
   ORDER BY ingested_at DESC
   LIMIT $3
   ```
   - Validate BOTH tenant_id AND device_id

8. `async def fetch_integrations(conn, tenant_id: str, limit: int = 50) -> List[dict]`:
   ```sql
   SELECT tenant_id, integration_id, name, enabled,
          config_json->>'url' AS url, created_at
   FROM integrations
   WHERE tenant_id = $1
   ORDER BY created_at DESC
   LIMIT $2
   ```

### 3.4 Create `services/ui_iot/db/audit.py`

Operator audit logging.

**Function**:

1. `async def log_operator_access(conn, user_id: str, action: str, tenant_filter: str | None = None, resource_type: str | None = None, resource_id: str | None = None, ip_address: str | None = None, user_agent: str | None = None) -> None`:
   ```sql
   INSERT INTO operator_audit_log
     (user_id, action, tenant_filter, resource_type, resource_id, ip_address, user_agent)
   VALUES ($1, $2, $3, $4, $5, $6::inet, $7)
   ```
   - Handle case where audit table doesn't exist yet (log warning, don't crash)

## Files to Create/Modify

| Action | Path |
|--------|------|
| CREATE | `services/ui_iot/middleware/tenant.py` |
| CREATE | `services/ui_iot/db/__init__.py` |
| CREATE | `services/ui_iot/db/queries.py` |
| CREATE | `services/ui_iot/db/audit.py` |

## Acceptance Criteria

- [ ] `get_tenant_id()` raises RuntimeError when context not set
- [ ] `get_tenant_id()` returns tenant_id when properly set
- [ ] All query functions raise ValueError if tenant_id is empty
- [ ] `fetch_device()` requires both tenant_id AND device_id
- [ ] `is_operator()` returns True for operator roles, False for customer roles
- [ ] `require_customer` dependency raises 403 for operator users
- [ ] `require_operator` dependency raises 403 for customer users

## Commit

```
Add tenant context helpers and query builders

- Context vars for tenant_id and user propagation
- get_tenant_id() fails fast if context not set
- Query builders require tenant_id parameter (no defaults)
- Device queries use composite key (tenant_id, device_id)
- Audit logging for operator access

Part of Phase 1: Customer Read-Only Dashboard
```
