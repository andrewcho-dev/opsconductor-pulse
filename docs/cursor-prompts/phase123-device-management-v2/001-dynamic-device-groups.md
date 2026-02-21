# Task 001: Dynamic Device Groups

## Goal

Add query-based (dynamic) device groups that resolve membership at read time based on a JSONB filter. Devices matching the filter criteria (status, tags, site_id) are automatically included without explicit member assignment.

## 1. Database Migration

Create file: `db/migrations/081_dynamic_device_groups.sql`

```sql
BEGIN;

-- Dynamic device groups store a query_filter instead of explicit member rows.
CREATE TABLE IF NOT EXISTS dynamic_device_groups (
    tenant_id    TEXT        NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    group_id     TEXT        NOT NULL,
    name         TEXT        NOT NULL,
    description  TEXT        NULL,
    query_filter JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, group_id)
);

CREATE INDEX IF NOT EXISTS idx_dynamic_device_groups_tenant
    ON dynamic_device_groups(tenant_id);

-- RLS (matches existing device_groups pattern from migration 061)
ALTER TABLE dynamic_device_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS dynamic_device_groups_tenant_isolation ON dynamic_device_groups;
CREATE POLICY dynamic_device_groups_tenant_isolation ON dynamic_device_groups
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON TABLE dynamic_device_groups IS
    'Device groups whose membership is resolved dynamically from query_filter JSONB.';
COMMENT ON COLUMN dynamic_device_groups.query_filter IS
    'Filter object. Supported keys: status (text), tags (text[]), site_id (text). Example: {"status":"ONLINE","tags":["production"],"site_id":"site-01"}';

COMMIT;
```

## 2. Backend API

Edit file: `services/ui_iot/routes/devices.py`

### 2a. Pydantic models

Add these models near the existing `DeviceGroupCreate` model (around line 1366):

```python
class DynamicGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    group_id: str | None = None
    query_filter: dict[str, Any] = Field(
        ...,
        description="Filter object. Supported keys: status, tags, site_id",
    )

class DynamicGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    query_filter: dict[str, Any] | None = None
```

### 2b. Query resolver helper function

Add this helper function before the endpoint definitions. It builds a parameterized SQL WHERE clause from the JSONB filter:

```python
def _build_dynamic_group_query(
    query_filter: dict[str, Any],
    tenant_id: str,
) -> tuple[str, list]:
    """
    Build SQL WHERE clause + params from a dynamic group query_filter.

    Supported filter keys:
      - status: str -> matches device_state.status
      - tags: list[str] -> device has ANY of the listed tags
      - site_id: str -> matches device_registry.site_id

    Returns (where_clause, params) where params[0] is always tenant_id.
    """
    conditions = ["dr.tenant_id = $1"]
    params: list[Any] = [tenant_id]
    idx = 2  # next parameter index

    if "status" in query_filter:
        conditions.append(f"ds.status = ${idx}")
        params.append(query_filter["status"])
        idx += 1

    if "tags" in query_filter:
        tag_list = query_filter["tags"]
        if isinstance(tag_list, str):
            tag_list = [tag_list]
        conditions.append(
            f"EXISTS (SELECT 1 FROM device_tags dt "
            f"WHERE dt.tenant_id = dr.tenant_id "
            f"AND dt.device_id = dr.device_id "
            f"AND dt.tag = ANY(${idx}::text[]))"
        )
        params.append(tag_list)
        idx += 1

    if "site_id" in query_filter:
        conditions.append(f"dr.site_id = ${idx}")
        params.append(query_filter["site_id"])
        idx += 1

    where_clause = " AND ".join(conditions)
    return where_clause, params
```

### 2c. Resolve members helper

```python
async def _resolve_dynamic_group_members(
    conn, tenant_id: str, query_filter: dict[str, Any]
) -> list[dict]:
    """Execute the dynamic group filter and return matching devices."""
    where_clause, params = _build_dynamic_group_query(query_filter, tenant_id)
    sql = f"""
        SELECT
            dr.device_id,
            COALESCE(dr.metadata->>'name', dr.device_id) AS name,
            COALESCE(ds.status, 'UNKNOWN') AS status,
            dr.site_id
        FROM device_registry dr
        LEFT JOIN device_state ds
            ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE {where_clause}
          AND dr.status != 'DECOMMISSIONED'
        ORDER BY dr.device_id
        LIMIT 500
    """
    rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]
```

### 2d. CRUD Endpoints

Add these endpoints after the existing static device-group endpoints (~line 1543):

```python
@router.post("/device-groups/dynamic", status_code=201)
async def create_dynamic_group(body: DynamicGroupCreate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    group_id = (body.group_id or f"dgrp-{uuid.uuid4().hex[:8]}").strip()
    if not group_id:
        raise HTTPException(status_code=400, detail="Invalid group_id")

    # Validate filter keys
    allowed_keys = {"status", "tags", "site_id"}
    invalid_keys = set(body.query_filter.keys()) - allowed_keys
    if invalid_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported filter keys: {', '.join(invalid_keys)}. Allowed: {', '.join(allowed_keys)}",
        )

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO dynamic_device_groups (tenant_id, group_id, name, description, query_filter)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (tenant_id, group_id) DO NOTHING
                RETURNING group_id, name, description, query_filter, created_at, updated_at
                """,
                tenant_id,
                group_id,
                body.name.strip(),
                body.description,
                json.dumps(body.query_filter),
            )
    except Exception:
        logger.exception("Failed to create dynamic device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=409, detail="Group ID already exists")
    result = dict(row)
    result["query_filter"] = json.loads(result["query_filter"]) if isinstance(result["query_filter"], str) else result["query_filter"]
    return result


@router.get("/device-groups/{group_id}/members")
async def get_dynamic_group_members(group_id: str, pool=Depends(get_db_pool)):
    """Resolve members of a dynamic group by executing its query_filter.
    Falls back to static group members if group_id is a static group."""
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            # Check dynamic groups first
            dg_row = await conn.fetchrow(
                "SELECT query_filter FROM dynamic_device_groups WHERE tenant_id = $1 AND group_id = $2",
                tenant_id,
                group_id,
            )
            if dg_row:
                qf = dg_row["query_filter"]
                if isinstance(qf, str):
                    qf = json.loads(qf)
                members = await _resolve_dynamic_group_members(conn, tenant_id, qf)
                return {"group_id": group_id, "group_type": "dynamic", "members": members, "total": len(members)}

            # Fall back to static group
            sg_row = await conn.fetchval(
                "SELECT 1 FROM device_groups WHERE tenant_id = $1 AND group_id = $2",
                tenant_id,
                group_id,
            )
            if not sg_row:
                raise HTTPException(status_code=404, detail="Group not found")

            # Reuse existing static member query
            rows = await conn.fetch(
                """
                SELECT
                    dr.device_id,
                    COALESCE(dr.metadata->>'name', dr.device_id) AS name,
                    COALESCE(ds.status, 'UNKNOWN') AS status,
                    dr.site_id,
                    m.added_at
                FROM device_group_members m
                JOIN device_registry dr
                    ON dr.tenant_id = m.tenant_id AND dr.device_id = m.device_id
                LEFT JOIN device_state ds
                    ON ds.tenant_id = m.tenant_id AND ds.device_id = m.device_id
                WHERE m.tenant_id = $1 AND m.group_id = $2
                ORDER BY dr.device_id
                """,
                tenant_id,
                group_id,
            )
            return {"group_id": group_id, "group_type": "static", "members": [dict(r) for r in rows], "total": len(rows)}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to resolve group members")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/device-groups/{group_id}/dynamic")
async def update_dynamic_group(group_id: str, body: DynamicGroupUpdate, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "query_filter" in updates:
        allowed_keys = {"status", "tags", "site_id"}
        invalid_keys = set(updates["query_filter"].keys()) - allowed_keys
        if invalid_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported filter keys: {', '.join(invalid_keys)}",
            )
        updates["query_filter"] = json.dumps(updates["query_filter"])

    if "name" in updates:
        updates["name"] = str(updates["name"]).strip()
        if not updates["name"]:
            raise HTTPException(status_code=400, detail="Invalid name")

    set_parts = [f"{field} = ${idx + 2}" for idx, field in enumerate(updates.keys())]
    params = [tenant_id] + list(updates.values()) + [group_id]
    set_clause = ", ".join(set_parts) + ", updated_at = now()"

    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE dynamic_device_groups
                SET {set_clause}
                WHERE tenant_id = $1 AND group_id = ${len(params)}
                RETURNING group_id, name, description, query_filter, created_at, updated_at
                """,
                *params,
            )
    except Exception:
        logger.exception("Failed to update dynamic device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Dynamic group not found")
    result = dict(row)
    result["query_filter"] = json.loads(result["query_filter"]) if isinstance(result["query_filter"], str) else result["query_filter"]
    return result


@router.delete("/device-groups/{group_id}/dynamic")
async def delete_dynamic_group(group_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    try:
        async with tenant_connection(pool, tenant_id) as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM dynamic_device_groups
                WHERE tenant_id = $1 AND group_id = $2
                RETURNING group_id
                """,
                tenant_id,
                group_id,
            )
    except Exception:
        logger.exception("Failed to delete dynamic device group")
        raise HTTPException(status_code=500, detail="Internal server error")
    if not row:
        raise HTTPException(status_code=404, detail="Dynamic group not found")
    return {"group_id": group_id, "deleted": True}
```

### 2e. Extend list_device_groups

Modify the existing `list_device_groups` endpoint (~line 1341) to also return dynamic groups. After the existing static groups query, add a second query for dynamic groups and merge results:

```python
# After the existing static groups fetch, add:
dynamic_rows = await conn.fetch(
    """
    SELECT group_id, name, description, query_filter, created_at
    FROM dynamic_device_groups
    WHERE tenant_id = $1
    ORDER BY name
    """,
    tenant_id,
)
dynamic_groups = []
for dr in dynamic_rows:
    d = dict(dr)
    d["group_type"] = "dynamic"
    d["member_count"] = None  # Resolved on demand
    qf = d.get("query_filter")
    if isinstance(qf, str):
        d["query_filter"] = json.loads(qf)
    dynamic_groups.append(d)

# Annotate static groups
for g in groups:
    g["group_type"] = "static"

return {"groups": groups + dynamic_groups, "total": len(groups) + len(dynamic_groups)}
```

## 3. Frontend

### 3a. API client functions

Edit file: `frontend/src/services/api/devices.ts`

Add new interfaces and functions after the existing group functions (~line 355):

```typescript
export interface DynamicDeviceGroup {
  group_id: string;
  name: string;
  description: string | null;
  query_filter: Record<string, unknown>;
  group_type: "dynamic";
  created_at: string;
}

export interface DynamicGroupFilter {
  status?: string;
  tags?: string[];
  site_id?: string;
}

export async function createDynamicGroup(data: {
  name: string;
  description?: string;
  query_filter: DynamicGroupFilter;
}): Promise<DynamicDeviceGroup> {
  return apiPost("/customer/device-groups/dynamic", data);
}

export async function updateDynamicGroup(
  groupId: string,
  data: { name?: string; description?: string; query_filter?: DynamicGroupFilter }
): Promise<DynamicDeviceGroup> {
  return apiPatch(`/customer/device-groups/${encodeURIComponent(groupId)}/dynamic`, data);
}

export async function deleteDynamicGroup(groupId: string): Promise<void> {
  await apiDelete(`/customer/device-groups/${encodeURIComponent(groupId)}/dynamic`);
}

export async function fetchGroupMembersV2(
  groupId: string
): Promise<{ group_id: string; group_type: string; members: DeviceGroupMember[]; total: number }> {
  return apiGet(`/customer/device-groups/${encodeURIComponent(groupId)}/members`);
}
```

### 3b. DeviceGroupsPage.tsx changes

Edit file: `frontend/src/features/devices/DeviceGroupsPage.tsx`

Key changes:

1. **Add a "Dynamic" toggle** in the create group dialog:
   - Add state: `const [isDynamic, setIsDynamic] = useState(false);`
   - Add filter state: `const [filterStatus, setFilterStatus] = useState("");`
   - Add filter state: `const [filterTags, setFilterTags] = useState<string[]>([]);`
   - Add filter state: `const [filterSiteId, setFilterSiteId] = useState("");`

2. **Dynamic group create mutation**:
   ```typescript
   const createDynamicMutation = useMutation({
     mutationFn: createDynamicGroup,
     onSuccess: async () => {
       await queryClient.invalidateQueries({ queryKey: ["device-groups"] });
       setCreateOpen(false);
       resetForm();
     },
   });
   ```

3. **In the Create Dialog**, add a Switch component for "Dynamic Group" toggle. When toggled on, show the filter builder UI instead of the static member list:
   ```tsx
   {isDynamic && (
     <div className="space-y-2">
       <Label>Status Filter</Label>
       <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
         <option value="">Any status</option>
         <option value="ONLINE">ONLINE</option>
         <option value="STALE">STALE</option>
       </select>

       <Label>Tags (comma-separated)</Label>
       <Input
         value={filterTags.join(",")}
         onChange={(e) => setFilterTags(e.target.value.split(",").filter(Boolean))}
       />

       <Label>Site ID</Label>
       <Input value={filterSiteId} onChange={(e) => setFilterSiteId(e.target.value)} />
     </div>
   )}
   ```

4. **In the group list**, show a badge for dynamic groups: `group.group_type === "dynamic"` renders a `<Badge variant="secondary">Dynamic</Badge>`.

5. **Members panel**: When the selected group is dynamic, use `fetchGroupMembersV2` and hide the "Add Device" dropdown since membership is automatic. Show the query_filter as read-only JSON or as filter pills.

6. **Delete**: Detect group_type and call `deleteDynamicGroup` vs `deleteDeviceGroup` accordingly.

## 4. Verification

```bash
# 1. Apply migration
docker compose exec iot-postgres psql -U iot -d iotcloud -f /migrations/081_dynamic_device_groups.sql

# 2. Create dynamic group via API
curl -s -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/customer/device-groups/dynamic \
  -H "Content-Type: application/json" \
  -d '{"name":"Online Devices","query_filter":{"status":"ONLINE"}}' | jq .
# Expect: group_id, name, query_filter in response

# 3. Resolve members
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/device-groups/dgrp-XXXXX/members | jq .
# Expect: group_type: "dynamic", members list matching filter

# 4. Update filter
curl -s -H "Authorization: Bearer $TOKEN" \
  -X PATCH http://localhost:8000/customer/device-groups/dgrp-XXXXX/dynamic \
  -H "Content-Type: application/json" \
  -d '{"query_filter":{"status":"ONLINE","tags":["production"]}}' | jq .

# 5. Verify membership changes dynamically
# Set a device offline, re-query members -- it should disappear from the group

# 6. Frontend: open /device-groups, click "Create Group", toggle "Dynamic", set filter, verify members update
```
