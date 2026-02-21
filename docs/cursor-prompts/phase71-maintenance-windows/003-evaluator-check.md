# Prompt 003 — Evaluator: is_in_maintenance() Check

Read `services/evaluator_iot/evaluator.py` — find `is_silenced()` and the locations where `open_or_update_alert()` is called.

## Add is_in_maintenance() Helper

```python
from datetime import datetime, timezone

async def is_in_maintenance(conn, tenant_id: str,
                             site_id: str = None,
                             device_type: str = None) -> bool:
    """
    Returns True if the tenant has an active maintenance window that applies
    to the given site_id and/or device_type.
    """
    now = datetime.now(timezone.utc)
    rows = await conn.fetch(
        """
        SELECT window_id, recurring, site_ids, device_types, starts_at, ends_at
        FROM alert_maintenance_windows
        WHERE tenant_id = $1
          AND enabled = true
          AND starts_at <= $2
          AND (ends_at IS NULL OR ends_at > $2)
        """,
        tenant_id, now
    )
    for row in rows:
        # Check site filter
        if row["site_ids"] and site_id not in row["site_ids"]:
            continue
        # Check device_type filter
        if row["device_types"] and device_type not in row["device_types"]:
            continue
        # Check recurring schedule if present
        recurring = row["recurring"]
        if recurring:
            dow = now.weekday()  # 0=Monday in Python; adjust if schema uses 0=Sunday
            # dow: schema 0=Sunday → Python: Sunday=6 → map accordingly
            schema_dow = (now.weekday() + 1) % 7  # convert to 0=Sunday
            allowed_dows = recurring.get("dow", list(range(7)))
            if schema_dow not in allowed_dows:
                continue
            start_h = recurring.get("start_hour", 0)
            end_h = recurring.get("end_hour", 24)
            current_hour = now.hour
            if not (start_h <= current_hour < end_h):
                continue
        return True  # active window matches
    return False
```

## Wire into Evaluation Loop

In EVERY place where `open_or_update_alert()` is called, add a maintenance window check BEFORE calling it:

```python
if await is_in_maintenance(conn, tenant_id, site_id=site_id, device_type=rule.get("device_type")):
    continue  # suppress — in maintenance window
```

Add this check alongside the existing `is_silenced()` check.

## Acceptance Criteria

- [ ] `is_in_maintenance()` added to evaluator.py
- [ ] Checks absolute time window (starts_at / ends_at)
- [ ] Checks recurring schedule (dow + hour range) if set
- [ ] Checks site_ids and device_types filters (None = all)
- [ ] Called before every `open_or_update_alert()` invocation
- [ ] `pytest -m unit -v` passes
