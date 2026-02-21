# Prompt 001 — Backend: Add Filter Params + Total Count to `fetch_devices_v2()`

## Context

`fetch_devices_v2()` in `services/ui_iot/db/queries.py` currently takes only `tenant_id`, `limit`, `offset`. It returns a list of device dicts with no total count.

## Your Task

**Read `services/ui_iot/db/queries.py` fully** — find `fetch_devices_v2()` and understand the existing SQL.

Then update `fetch_devices_v2()` to accept and apply filter parameters. The function signature becomes:

```python
async def fetch_devices_v2(
    conn,
    tenant_id: str,
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,          # "ONLINE" | "STALE" | "OFFLINE" | None
    tags: list[str] | None = None,      # device must have ALL listed tags (AND logic)
    q: str | None = None,               # prefix/contains search
    site_id: str | None = None,         # exact match on site_id
) -> dict:                              # returns {"devices": [...], "total": int}
```

### SQL Changes

Build the WHERE clause dynamically. Use `asyncpg` positional parameters (`$1`, `$2`, etc.) — build the param list alongside the WHERE clauses.

**Base WHERE:** `dr.tenant_id = $1`

**Status filter** (`status` param):
- `ONLINE` / `STALE` maps to `COALESCE(ds.status, 'OFFLINE')` — filter on the joined device_state status
- Add: `AND COALESCE(ds.status, 'OFFLINE') = $N`

**Tag filter** (`tags` param — AND logic, device must have ALL tags):
```sql
AND (
  SELECT COUNT(DISTINCT dt.tag)
  FROM device_tags dt
  WHERE dt.tenant_id = dr.tenant_id
    AND dt.device_id = dr.device_id
    AND dt.tag = ANY($N::text[])
) = {len(tags)}
```

**Search filter** (`q` param — prefix/contains match):
```sql
AND (
  dr.device_id ILIKE $N
  OR dr.model ILIKE $N
  OR dr.serial_number ILIKE $N
  OR dr.site_id ILIKE $N
  OR dr.address ILIKE $N
)
```
Pass `q` as `f"%{q}%"` (contains match). For the `$N` param, use the same parameter number for all ILIKE conditions (same value repeated is fine in SQL).

**Site filter** (`site_id` param):
```sql
AND dr.site_id = $N
```

### Total Count

Add a COUNT query that uses the same WHERE clause (without LIMIT/OFFSET):

```sql
SELECT COUNT(*) FROM device_registry dr
LEFT JOIN device_state ds ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
WHERE [same WHERE clauses]
```

Run both queries (count + data) in the same connection. Return:

```python
return {"devices": [dict(r) for r in rows], "total": total_count}
```

### Also add: `fetch_fleet_summary()`

New function in the same file:

```python
async def fetch_fleet_summary(conn, tenant_id: str) -> dict:
    """Returns counts of devices by status for the fleet summary widget."""
    rows = await conn.fetch(
        """
        SELECT
            COALESCE(ds.status, 'OFFLINE') AS status,
            COUNT(*) AS count
        FROM device_registry dr
        LEFT JOIN device_state ds
          ON ds.tenant_id = dr.tenant_id AND ds.device_id = dr.device_id
        WHERE dr.tenant_id = $1
          AND dr.status = 'ACTIVE'
        GROUP BY COALESCE(ds.status, 'OFFLINE')
        """,
        tenant_id,
    )
    summary = {"ONLINE": 0, "STALE": 0, "OFFLINE": 0}
    for row in rows:
        summary[row["status"]] = row["count"]
    summary["total"] = sum(summary.values())
    return summary
```

## Acceptance Criteria

- [ ] `fetch_devices_v2()` accepts `status`, `tags`, `q`, `site_id` params
- [ ] Returns `{"devices": [...], "total": int}` (not just a list)
- [ ] `status=None` returns all statuses (no filter)
- [ ] `tags=[]` or `tags=None` returns all devices (no tag filter)
- [ ] `q=None` returns all devices (no search filter)
- [ ] `fetch_fleet_summary()` exists and returns `{ONLINE, STALE, OFFLINE, total}`
- [ ] `pytest -m unit -v` passes — update any existing tests that call `fetch_devices_v2()` to handle the new return shape `{"devices": [...], "total": N}`
