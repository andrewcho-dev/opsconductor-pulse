# Task 011: Fix Quarantine Query Type Error and WebSocket Operator Access

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

Two remaining issues after the operator routing fix:

1. **`/operator/quarantine` returns 500**: The `fetch_quarantine_events` query passes `minutes` as an int, but the SQL uses `$1::text` which makes asyncpg expect a string parameter. Error: `invalid input for query argument $1: 60 (expected str, got int)`.

2. **WebSocket rejects operators with 403**: The WebSocket handler in `api_v2.py` line 379 has a hardcoded check: `if not tenant_id or role not in ("customer_admin", "customer_viewer")`. Operators have empty `tenant_id` and role `"operator"`, so they're rejected.

**Read first**:
- `services/ui_iot/db/queries.py` — `fetch_quarantine_events` function (~line 505)
- `services/ui_iot/routes/api_v2.py` — WebSocket handler (~line 377-381)

---

## Task

### 11.1 Fix quarantine query type mismatch

**File**: `services/ui_iot/db/queries.py`

In the `fetch_quarantine_events` function (~line 510), change the parameter from `minutes` (int) to `str(minutes)` (string), since asyncpg needs a string for the `$1::text` cast.

Change:
```python
        minutes,
        limit,
```

To:
```python
        str(minutes),
        limit,
```

### 11.2 Fix WebSocket to allow operator connections

**File**: `services/ui_iot/routes/api_v2.py`

The WebSocket endpoint rejects operators because it checks for customer roles only. Operators should be allowed to connect (they won't subscribe to tenant-specific data, but the connection shouldn't fail).

Change the role check at ~line 377-381 from:

```python
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "")
    if not tenant_id or role not in ("customer_admin", "customer_viewer"):
        await websocket.close(code=4003, reason="Unauthorized")
        return
```

To:

```python
    tenant_id = payload.get("tenant_id")
    role = payload.get("role", "")
    valid_roles = ("customer_admin", "customer_viewer", "operator", "operator_admin")
    if role not in valid_roles:
        await websocket.close(code=4003, reason="Unauthorized")
        return
    # Operators have no tenant_id — use a placeholder for the WS connection
    if not tenant_id:
        tenant_id = "__operator__"
```

This allows operators to connect. The `__operator__` tenant_id placeholder means the WebSocket push loop's `tenant_connection` calls will return empty results for operators (which is fine — operator pages don't rely on the WebSocket for data).

### 11.3 Rebuild and deploy

```bash
cd /home/opsconductor/simcloud/compose && docker compose up --build -d
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/db/queries.py` | Fix `minutes` parameter type in `fetch_quarantine_events` |
| MODIFY | `services/ui_iot/routes/api_v2.py` | Allow operator roles in WebSocket handler |

---

## Test

### Step 1: Backend tests still pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Deploy

```bash
cd /home/opsconductor/simcloud/compose && docker compose up --build -d
```

### Step 3: Verify quarantine endpoint

```bash
# Get an operator token
TOKEN=$(curl -sk -X POST "https://192.168.10.53/realms/pulse/protocol/openid-connect/token" \
  -d "client_id=pulse-ui" -d "grant_type=password" -d "username=operator1" -d "password=operator1" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -sk -H "Authorization: Bearer $TOKEN" "https://192.168.10.53/operator/quarantine?minutes=60&limit=20" | python3 -m json.tool | head -5
```

Should return JSON with `minutes`, `events`, `limit` — not 500.

---

## Commit

```
Fix quarantine query type error and WebSocket operator access

The fetch_quarantine_events query passed minutes as int but asyncpg
expected str for the $1::text cast. WebSocket handler now accepts
operator roles alongside customer roles.
```
