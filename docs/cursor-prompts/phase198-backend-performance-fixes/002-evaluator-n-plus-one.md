# Task 2: Eliminate N+1 Group Membership Queries in Evaluator

## Context

`services/evaluator_iot/evaluator.py:1445-1460` (approximately) runs one `SELECT FROM device_group_members` query per rule per device when checking group-filtered rules. For a device matching 50+ rules, this is 50+ sequential queries in the hot evaluation path.

The fix: fetch all group memberships for a device **once** at the start of rule evaluation, cache them in a set, and filter in memory.

## Actions

1. Read `services/evaluator_iot/evaluator.py` focusing on the rule evaluation loop — the section that iterates over rules and checks group membership for each one.

2. Identify the outermost evaluation function that receives `device_id` and `rules`. Before the rule loop, add a single batch fetch:

```python
# Fetch all group IDs this device belongs to — ONE query before the rule loop
device_groups: set[str] = set()
if any(r.get("group_ids") for r in rules):
    rows = await conn.fetch(
        """
        SELECT group_id
        FROM device_group_members
        WHERE tenant_id = $1 AND device_id = $2
        """,
        tenant_id,
        device_id,
    )
    device_groups = {row["group_id"] for row in rows}
```

3. In the rule loop, replace the per-rule `SELECT FROM device_group_members` query with an in-memory membership check:

```python
# OLD: per-rule DB query
is_member = await conn.fetchval(
    "SELECT 1 FROM device_group_members WHERE tenant_id=$1 AND device_id=$2 AND group_id = ANY($3::text[]) LIMIT 1",
    tenant_id, device_id, rule["group_ids"]
)

# NEW: in-memory check using pre-fetched set
is_member = bool(device_groups.intersection(rule["group_ids"]))
```

4. If there are other places in the evaluator that similarly query group membership per-rule inside a loop, apply the same pre-fetch pattern.

5. Do not change any rule evaluation logic beyond the membership lookup mechanism.

## Verification

```bash
# Only one device_group_members query per evaluation call, not one per rule
grep -n 'device_group_members' services/evaluator_iot/evaluator.py
# Should appear once in the pre-fetch and once or zero times inside the rule loop
# (the loop reference should be the in-memory check, not a DB call)
```
