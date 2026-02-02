# Task 004: Integration Routes Management

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

Integrations define WHERE to send webhooks (the URL). Integration routes define WHAT to send (which alerts trigger delivery). Routes link alert types and severities to specific integrations.

**Read first**:
- `services/ui_iot/routes/customer.py` (integration CRUD from Task 003)
- `services/ui_iot/db/queries.py`
- Database schema for `integration_routes` table

**Depends on**: Task 003

## Task

### 4.1 Add query functions to `services/ui_iot/db/queries.py`

**Function 1**: `fetch_integration_routes`
```
async def fetch_integration_routes(conn, tenant_id: str, limit: int = 100) -> List[dict]
```
- SELECT from integration_routes WHERE tenant_id = $1
- Join with integrations to get integration name
- ORDER BY created_at DESC
- LIMIT $2

**Function 2**: `fetch_integration_route`
```
async def fetch_integration_route(conn, tenant_id: str, route_id: str) -> dict | None
```
- SELECT single route by tenant_id AND route_id
- Return row or None

**Function 3**: `create_integration_route`
```
async def create_integration_route(conn, tenant_id: str, integration_id: str, alert_types: List[str], severities: List[str], enabled: bool = True) -> dict
```
- Verify integration_id belongs to tenant_id first
- Generate UUID for route_id
- INSERT into integration_routes
- Return created row

**Function 4**: `update_integration_route`
```
async def update_integration_route(conn, tenant_id: str, route_id: str, alert_types: List[str] = None, severities: List[str] = None, enabled: bool = None) -> dict | None
```
- UPDATE WHERE tenant_id = $1 AND route_id = $2
- Only update non-None fields
- Return updated row or None

**Function 5**: `delete_integration_route`
```
async def delete_integration_route(conn, tenant_id: str, route_id: str) -> bool
```
- DELETE WHERE tenant_id = $1 AND route_id = $2
- Return True if deleted, False if not found

### 4.2 Add Pydantic models

**RouteCreate**:
- `integration_id`: UUID, required
- `alert_types`: List[str], required, non-empty
- `severities`: List[str], required, non-empty
- `enabled`: bool, optional, default True

**RouteUpdate**:
- `alert_types`: List[str], optional
- `severities`: List[str], optional
- `enabled`: bool, optional

**UUID validation**:
- Use Pydantic's `UUID` type for `integration_id` field
- Pydantic will automatically return 422 for malformed UUIDs
- For path parameters (`route_id`), add explicit validation:

```python
from uuid import UUID

@router.get("/integration-routes/{route_id}")
async def get_route(route_id: str):
    try:
        UUID(route_id)  # Validate format
    except ValueError:
        raise HTTPException(400, "Invalid route_id format: must be a valid UUID")
```

This ensures malformed UUIDs return 400/422, not 500.

### 4.3 Add routes to `services/ui_iot/routes/customer.py`

**Route 1**: `GET /customer/integration-routes`
- Get tenant_id from context
- Call fetch_integration_routes
- Return list with integration names included

**Route 2**: `GET /customer/integration-routes/{route_id}`
- Path param: route_id
- Get tenant_id from context
- Call fetch_integration_route
- If None: return 404
- Return route details

**Route 3**: `POST /customer/integration-routes`
- Request body: RouteCreate
- Get tenant_id from context
- Validate integration_id belongs to tenant
- Validate alert_types against allowed values
- Validate severities against allowed values
- Call create_integration_route
- Return 201 with created route

**Route 4**: `PATCH /customer/integration-routes/{route_id}`
- Path param: route_id
- Request body: RouteUpdate
- **Reject empty payload**: If all fields are None/missing, return 400 with message "No fields to update"
- Apply list hygiene to alert_types/severities if provided
- Validate any provided fields against allowed values
- Call update_integration_route
- If None: return 404
- Return updated route

**Route 5**: `DELETE /customer/integration-routes/{route_id}`
- Path param: route_id
- Get tenant_id from context
- Call delete_integration_route
- If False: return 404
- Return 204 No Content

### 4.4 Validation constants and list hygiene

Define allowed values:

**Alert types** (from existing schema):
- `STALE_DEVICE`
- `LOW_BATTERY`
- `TEMPERATURE_ALERT`
- `CONNECTIVITY_ISSUE`
- `DEVICE_OFFLINE`

**Severities**:
- `CRITICAL`
- `WARNING`
- `INFO`

**List hygiene (apply to alert_types and severities)**:
1. Filter out empty strings: `["CRITICAL", "", "WARNING"]` → `["CRITICAL", "WARNING"]`
2. Strip whitespace from each item: `[" CRITICAL "]` → `["CRITICAL"]`
3. De-duplicate: `["CRITICAL", "CRITICAL"]` → `["CRITICAL"]`
4. Validate each item against allowed values
5. After hygiene, reject if list is empty

Reject requests with unknown values after hygiene is applied.

### 4.5 Role-based access

Apply `require_customer_admin` dependency to POST, PATCH, DELETE routes.
GET routes accessible to both admin and viewer roles.

### 4.6 Cross-tenant protection for integration_id

When creating a route, verify the integration_id belongs to the same tenant:

```python
integration = await fetch_integration(conn, tenant_id, body.integration_id)
if not integration:
    raise HTTPException(400, "Integration not found or belongs to different tenant")
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `services/ui_iot/db/queries.py` |
| MODIFY | `services/ui_iot/routes/customer.py` |

## Acceptance Criteria

- [ ] `GET /customer/integration-routes` lists routes for tenant
- [ ] `POST /customer/integration-routes` creates route linked to tenant's integration
- [ ] Cannot create route for integration belonging to other tenant
- [ ] `PATCH /customer/integration-routes/{id}` updates only tenant's routes
- [ ] `DELETE /customer/integration-routes/{id}` deletes only tenant's routes
- [ ] Invalid alert_types rejected with 400
- [ ] Invalid severities rejected with 400
- [ ] `customer_viewer` gets 403 on write operations
- [ ] Empty PATCH payload returns 400
- [ ] Duplicate values in lists are de-duplicated
- [ ] Empty strings in lists are filtered out
- [ ] List becomes empty after hygiene returns 400

**Test scenario**:
```
1. Login as customer1 (tenant-a)
2. Create integration via POST /customer/integrations
3. POST /customer/integration-routes with:
   - integration_id from step 2
   - alert_types: ["STALE_DEVICE", "LOW_BATTERY"]
   - severities: ["CRITICAL", "WARNING"]
4. Confirm 201, route created
5. GET /customer/integration-routes - confirm route in list
6. PATCH route to add "TEMPERATURE_ALERT" to alert_types
7. Confirm update successful
8. Login as customer2 (tenant-b)
9. Try POST route with customer1's integration_id - confirm 400
```

## Commit

```
Add integration route management for customers

- GET /customer/integration-routes: list routing rules
- POST /customer/integration-routes: create routing rule
- PATCH /customer/integration-routes/{id}: update rule
- DELETE /customer/integration-routes/{id}: remove rule
- Validate alert_types and severities against allowed values
- Verify integration belongs to tenant before linking

Part of Phase 2: Customer Integration Management
```
