# Task 003: Integration CRUD Routes

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Phase 1 added read-only `GET /customer/integrations`. Customers now need to create, update, and delete their own webhook integrations. All operations must be strictly tenant-scoped.

**Read first**:
- `docs/CUSTOMER_PLANE_ARCHITECTURE.md` (Section 3.1: Customer-Plane Routes)
- `services/ui_iot/routes/customer.py` (existing GET route)
- `services/ui_iot/db/queries.py` (existing query patterns)
- Database schema for `integrations` table

**Depends on**: Tasks 001, 002

## Task

### 3.1 Add query functions to `services/ui_iot/db/queries.py`

**Function 1**: `create_integration`
```
async def create_integration(conn, tenant_id: str, name: str, webhook_url: str, enabled: bool = True) -> dict
```
- INSERT into integrations table
- Generate UUID for integration_id
- Set config_json with url
- Return the created integration row
- MUST include tenant_id in INSERT

**Function 2**: `update_integration`
```
async def update_integration(conn, tenant_id: str, integration_id: str, name: str = None, webhook_url: str = None, enabled: bool = None) -> dict | None
```
- UPDATE integrations WHERE tenant_id = $1 AND integration_id = $2
- Only update non-None fields
- Return updated row, or None if not found
- MUST include tenant_id in WHERE clause

**Function 3**: `delete_integration`
```
async def delete_integration(conn, tenant_id: str, integration_id: str) -> bool
```
- DELETE FROM integrations WHERE tenant_id = $1 AND integration_id = $2
- Return True if deleted, False if not found
- MUST include tenant_id in WHERE clause

**Function 4**: `fetch_integration`
```
async def fetch_integration(conn, tenant_id: str, integration_id: str) -> dict | None
```
- SELECT single integration by composite key
- Return row or None

### 3.2 Add Pydantic models

Add to `services/ui_iot/routes/customer.py` (or create `services/ui_iot/schemas.py`):

**IntegrationCreate**:
- `name`: str, required, 1-100 chars
- `webhook_url`: str, required, valid URL
- `enabled`: bool, optional, default True

**IntegrationUpdate**:
- `name`: str, optional
- `webhook_url`: str, optional
- `enabled`: bool, optional

### 3.3 Add routes to `services/ui_iot/routes/customer.py`

**Route 1**: `POST /customer/integrations`
- Request body: IntegrationCreate
- Get tenant_id from context
- Validate name and URL format
- Call create_integration
- Return 201 with created integration
- Redact URL in response

**Route 2**: `GET /customer/integrations/{integration_id}`
- Path param: integration_id
- Get tenant_id from context
- Call fetch_integration with BOTH tenant_id and integration_id
- If None: return 404
- Return integration (redact URL)

**Route 3**: `PATCH /customer/integrations/{integration_id}`
- Path param: integration_id
- Request body: IntegrationUpdate
- Get tenant_id from context
- **Reject empty payload**: If all fields are None/missing, return 400 with message "No fields to update"
- Validate any provided fields
- Call update_integration
- If None: return 404
- Return updated integration

**Route 4**: `DELETE /customer/integrations/{integration_id}`
- Path param: integration_id
- Get tenant_id from context
- Call delete_integration
- If False: return 404
- Return 204 No Content

### 3.4 Role-based access control

Add dependency for write operations:

```python
async def require_customer_admin(request: Request):
    user = get_user()
    if user.get("role") != "customer_admin":
        raise HTTPException(403, "Customer admin role required")
```

Apply to POST, PATCH, DELETE routes:
```python
@router.post("/integrations", dependencies=[Depends(require_customer_admin)])
```

GET routes remain accessible to both `customer_admin` and `customer_viewer`.

### 3.5 Input validation

**Name validation**:
- Length: 1-100 characters
- Pattern: alphanumeric, spaces, hyphens, underscores
- Strip whitespace

**URL validation** (basic, detailed validation in Task 006):
- Must be valid URL format
- Must have scheme (http or https)
- Must have host

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/db/queries.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |

## Acceptance Criteria

- [ ] `POST /customer/integrations` creates integration for tenant
- [ ] `GET /customer/integrations/{id}` returns integration if tenant matches
- [ ] `GET /customer/integrations/{id}` returns 404 if tenant doesn't match
- [ ] `PATCH /customer/integrations/{id}` updates only if tenant matches
- [ ] `DELETE /customer/integrations/{id}` deletes only if tenant matches
- [ ] `customer_viewer` gets 403 on POST/PATCH/DELETE
- [ ] `customer_admin` can perform all operations
- [ ] All queries include tenant_id in WHERE clause
- [ ] URLs redacted in responses (show only scheme://host)
- [ ] Empty PATCH payload returns 400

**Test scenario**:
```
1. Login as customer1 (tenant-a, customer_admin)
2. POST /customer/integrations with name="My Webhook", url="https://example.com/hook"
3. Confirm 201, integration created
4. GET /customer/integrations - confirm new integration in list
5. PATCH /customer/integrations/{id} with enabled=false
6. Confirm integration disabled
7. Login as customer2 (tenant-b)
8. GET /customer/integrations/{id from step 2} - confirm 404
9. DELETE attempt - confirm 404
```

## Commit

```
Add integration CRUD routes for customers

- POST /customer/integrations: create webhook integration
- GET /customer/integrations/{id}: fetch single integration
- PATCH /customer/integrations/{id}: update integration
- DELETE /customer/integrations/{id}: remove integration
- Role check: customer_admin required for writes
- All operations tenant-scoped via JWT

Part of Phase 2: Customer Integration Management
```
