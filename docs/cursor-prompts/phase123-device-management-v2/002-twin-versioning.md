# Task 002: Twin Optimistic Concurrency (ETag / If-Match)

## Goal

Prevent lost updates on device twin desired state by implementing HTTP optimistic concurrency control. The `GET /twin` endpoint returns an `ETag` header with the current `desired_version`. The `PATCH /twin/desired` endpoint requires an `If-Match` header and returns 409 Conflict if the version has changed.

## Context

The `device_state` table already has `desired_version INTEGER NOT NULL DEFAULT 0` (from migration 076). The current `PATCH /twin/desired` endpoint unconditionally increments this version. We need to make it conditional.

Key files:
- `services/ui_iot/routes/devices.py` -- lines 949-1047 (twin endpoints)
- `frontend/src/features/devices/DeviceTwinPanel.tsx` -- twin UI
- `frontend/src/services/api/devices.ts` -- `getDeviceTwin`, `updateDesiredState`
- `frontend/src/services/api/client.ts` -- `apiGet`, `apiPatch` wrappers

## 1. No Migration Required

The `desired_version` column already exists. No schema changes needed.

## 2. Backend Changes

Edit file: `services/ui_iot/routes/devices.py`

### 2a. Modify GET /devices/{device_id}/twin (line ~949)

Add the `Response` dependency and set an ETag header on the response:

```python
from fastapi import Response as FastAPIResponse

@router.get("/devices/{device_id}/twin", response_model=TwinResponse)
async def get_device_twin(device_id: str, response: FastAPIResponse, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT
              device_id,
              desired_state,
              reported_state,
              desired_version,
              reported_version,
              shadow_updated_at,
              last_seen_at AS last_seen
            FROM device_state
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    desired = _jsonb_to_dict(row["desired_state"])
    reported = _jsonb_to_dict(row["reported_state"])
    shadow_updated_at = row["shadow_updated_at"]

    # Set ETag header with current desired_version
    response.headers["ETag"] = f'"{row["desired_version"]}"'

    return {
        "device_id": device_id,
        "desired": desired,
        "reported": reported,
        "delta": compute_delta(desired, reported),
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
        "sync_status": sync_status(
            row["desired_version"],
            row["reported_version"],
            row["last_seen"],
        ),
        "shadow_updated_at": shadow_updated_at.isoformat() if shadow_updated_at else None,
    }
```

**Important**: Import `Response as FastAPIResponse` at the top of the file to avoid conflict with the existing `Response` import from starlette. Check existing imports -- if `from starlette.responses import Response` is already imported, alias the FastAPI one or use `from fastapi import Response` directly if no conflict.

### 2b. Modify PATCH /devices/{device_id}/twin/desired (line ~990)

Add `If-Match` header check with conditional UPDATE:

```python
@router.patch("/devices/{device_id}/twin/desired")
async def update_desired_state(
    device_id: str,
    body: TwinDesiredUpdate,
    request: Request,
    response: FastAPIResponse,
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()

    # Parse If-Match header
    if_match = request.headers.get("If-Match")
    if if_match is None:
        raise HTTPException(
            status_code=428,
            detail="If-Match header required. GET the twin first to obtain the current ETag.",
        )

    # Strip quotes: ETag format is "123" -> 123
    try:
        expected_version = int(if_match.strip('"'))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="If-Match header must contain a valid version number (e.g., \"42\")",
        )

    async with tenant_connection(pool, tenant_id) as conn:
        # Conditional update: only succeeds if desired_version matches
        row = await conn.fetchrow(
            """
            UPDATE device_state
            SET desired_state = $1::jsonb,
                desired_version = desired_version + 1,
                shadow_updated_at = NOW()
            WHERE tenant_id = $2
              AND device_id = $3
              AND desired_version = $4
            RETURNING device_id, desired_state, desired_version
            """,
            json.dumps(body.desired),
            tenant_id,
            device_id,
            expected_version,
        )

    if row is None:
        # Check if device exists at all
        async with tenant_connection(pool, tenant_id) as conn:
            exists = await conn.fetchval(
                "SELECT desired_version FROM device_state WHERE tenant_id = $1 AND device_id = $2",
                tenant_id,
                device_id,
            )
        if exists is None:
            raise HTTPException(status_code=404, detail="Device not found")

        # Device exists but version mismatch -> 409 Conflict
        raise HTTPException(
            status_code=409,
            detail=f"Version conflict. Expected version {expected_version} but current version is {exists}. Refresh and retry.",
        )

    await _publish_shadow_desired(
        tenant_id,
        device_id,
        _jsonb_to_dict(row["desired_state"]),
        row["desired_version"],
    )

    # Return new ETag
    response.headers["ETag"] = f'"{row["desired_version"]}"'

    return {
        "device_id": device_id,
        "desired": _jsonb_to_dict(row["desired_state"]),
        "desired_version": row["desired_version"],
    }
```

### 2c. Also set ETag on GET /devices/{device_id}/twin/delta (line ~1024)

Add `response: FastAPIResponse` parameter and set:

```python
response.headers["ETag"] = f'"{row["desired_version"]}"'
```

## 3. Frontend Changes

### 3a. Update API client

Edit file: `frontend/src/services/api/devices.ts`

The `getDeviceTwin` function needs to capture the ETag from the response header. Since the current `apiGet` wrapper discards headers, you have two options:

**Option A (recommended)**: Extend the `TwinDocument` interface to include the etag and parse it from a custom header added by the backend. Instead, modify `getDeviceTwin` to use `fetch` directly:

```typescript
export async function getDeviceTwin(deviceId: string): Promise<TwinDocument & { etag: string }> {
  const token = keycloak.token;
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`/customer/devices/${encodeURIComponent(deviceId)}/twin`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to load twin: ${res.status}`);
  }
  const data = await res.json() as TwinDocument;
  const etag = res.headers.get("ETag") ?? `"${data.desired_version}"`;
  return { ...data, etag };
}
```

Modify `updateDesiredState` to accept and send the version:

```typescript
export async function updateDesiredState(
  deviceId: string,
  desired: TwinDesired,
  etag: string,
): Promise<{ device_id: string; desired: TwinDesired; desired_version: number }> {
  const token = keycloak.token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "If-Match": etag,
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(
    `/customer/devices/${encodeURIComponent(deviceId)}/twin/desired`,
    {
      method: "PATCH",
      headers,
      body: JSON.stringify({ desired }),
    },
  );
  if (res.status === 409) {
    throw new ConflictError("Another user modified this twin. Refresh to see latest.");
  }
  if (res.status === 428) {
    throw new Error("Version header required. Please refresh the twin first.");
  }
  if (!res.ok) {
    throw new Error(`Failed to update twin: ${res.status}`);
  }
  return res.json();
}

// Custom error class for conflict detection
export class ConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConflictError";
  }
}
```

### 3b. Update DeviceTwinPanel.tsx

Edit file: `frontend/src/features/devices/DeviceTwinPanel.tsx`

Key changes:

1. **Track ETag in state**:
   ```typescript
   const [etag, setEtag] = useState<string>("");
   ```

2. **In loadTwin**, capture the etag:
   ```typescript
   const data = await getDeviceTwin(deviceId);
   setTwin(data);
   setEtag(data.etag);
   setDesiredDraft(JSON.stringify(data.desired, null, 2));
   ```

3. **In handleSave**, send the etag and handle 409:
   ```typescript
   const handleSave = async () => {
     setSaving(true);
     setError(null);
     try {
       const parsed = JSON.parse(desiredDraft) as Record<string, unknown>;
       await updateDesiredState(deviceId, parsed, etag);
       setEditing(false);
       await loadTwin(); // This refreshes the etag
     } catch (err) {
       if (err instanceof ConflictError) {
         setError("Another user modified this twin. Refresh to see latest.");
         // Auto-refresh to get latest version
         await loadTwin();
         return;
       }
       const message = err instanceof Error ? err.message : "Failed to save desired state";
       setError(message);
     } finally {
       setSaving(false);
     }
   };
   ```

4. **Import ConflictError**:
   ```typescript
   import { getDeviceTwin, type TwinDocument, updateDesiredState, ConflictError } from "@/services/api/devices";
   ```

5. **Optional toast**: If the project uses a toast library (e.g., sonner), show a toast on conflict instead of inline error. Check if `sonner` or `react-hot-toast` is already in `package.json`.

## 4. Verification

```bash
# 1. Get current twin and note the ETag header
curl -si -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin
# Look for: ETag: "0" (or current version)

# 2. Update with correct version
curl -si -H "Authorization: Bearer $TOKEN" \
  -H "If-Match: \"0\"" \
  -X PATCH http://localhost:8000/customer/devices/DEVICE-01/twin/desired \
  -H "Content-Type: application/json" \
  -d '{"desired": {"led": "on"}}'
# Expect: 200 OK, ETag: "1"

# 3. Try same update with stale version
curl -si -H "Authorization: Bearer $TOKEN" \
  -H "If-Match: \"0\"" \
  -X PATCH http://localhost:8000/customer/devices/DEVICE-01/twin/desired \
  -H "Content-Type: application/json" \
  -d '{"desired": {"led": "off"}}'
# Expect: 409 Conflict

# 4. Try without If-Match
curl -si -H "Authorization: Bearer $TOKEN" \
  -X PATCH http://localhost:8000/customer/devices/DEVICE-01/twin/desired \
  -H "Content-Type: application/json" \
  -d '{"desired": {"led": "off"}}'
# Expect: 428 Precondition Required

# 5. Frontend: open twin panel, edit desired, save -- verify version increments in UI
# Open twin in two tabs, save in one, try saving in the other -- expect conflict toast
```
