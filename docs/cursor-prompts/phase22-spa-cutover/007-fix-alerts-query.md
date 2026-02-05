# Task 007: Fix fleet_alert Query — Remove Non-Existent `updated_at` Column

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Modify only the files listed in "Files to Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.

---

## Context

The `/api/v2/alerts` endpoint returns 500 Internal Server Error. The backend log shows:

```
asyncpg.exceptions.UndefinedColumnError: column "updated_at" does not exist
HINT:  Perhaps you meant to reference the column "fleet_alert.created_at".
```

The `fleet_alert` table was created without an `updated_at` column (see `evaluator.py` CREATE TABLE). The `fetch_alerts_v2` and `fetch_alert_v2` queries in `queries.py` incorrectly include `updated_at` in their SELECT list. The frontend `Alert` TypeScript interface does NOT include `updated_at`, so no frontend changes are needed.

**Read first**:
- `services/ui_iot/db/queries.py` — lines 749-784 (the two broken queries)
- `services/evaluator_iot/evaluator.py` — lines 35-49 (fleet_alert CREATE TABLE, no `updated_at`)

---

## Task

### 7.1 Remove `updated_at` from `fetch_alerts_v2` query

**File**: `services/ui_iot/db/queries.py`

In the `fetch_alerts_v2` function (~line 749), change the SELECT from:

```python
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, updated_at, closed_at
        FROM fleet_alert
```

To:

```python
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, closed_at
        FROM fleet_alert
```

### 7.2 Remove `updated_at` from `fetch_alert_v2` query

**File**: `services/ui_iot/db/queries.py`

In the `fetch_alert_v2` function (~line 773), change the SELECT from:

```python
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, updated_at, closed_at
        FROM fleet_alert
```

To:

```python
        SELECT id AS alert_id, tenant_id, device_id, site_id, alert_type,
               fingerprint, severity, confidence, summary, details,
               status, created_at, closed_at
        FROM fleet_alert
```

---

## Files to Modify

| Action | Path | What changes |
|--------|------|--------------|
| MODIFY | `services/ui_iot/db/queries.py` | Remove `updated_at` from two fleet_alert SELECT queries |

---

## Test

### Step 1: Verify backend tests still pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

### Step 2: Rebuild and deploy

```bash
cd /home/opsconductor/simcloud/compose && docker compose up --build -d
```

Wait 10 seconds, then verify the alerts endpoint works:

```bash
curl -sk https://192.168.10.53/api/v2/alerts?status=OPEN&limit=10 -o /dev/null -w "%{http_code}"
```

Should return `401` (unauthorized — not 500). A 401 means the query itself works; the endpoint requires authentication.

### Step 3: Verify with an authenticated request (optional)

If you want to confirm the full response, get a token first:

```bash
TOKEN=$(curl -sk -X POST "https://192.168.10.53/realms/pulse/protocol/openid-connect/token" \
  -d "client_id=pulse-ui" -d "grant_type=password" -d "username=admin" -d "password=admin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -sk -H "Authorization: Bearer $TOKEN" "https://192.168.10.53/api/v2/alerts?status=OPEN&limit=10" | python3 -m json.tool | head -20
```

Should return a JSON response with `alerts` array (possibly empty) — not a 500 error.

---

## Commit

```
Fix fleet_alert query — remove non-existent updated_at column

The fetch_alerts_v2 and fetch_alert_v2 queries selected updated_at
from fleet_alert, but that column was never added to the table schema.
Removed the column reference to fix 500 errors on /api/v2/alerts.
```
