# Task 004: Improved Twin Delta (Structured Diff)

## Goal

Replace the flat delta map (keys in desired whose values differ from reported) with a structured diff that categorizes changes as added, removed, changed, or unchanged. Update the API response and render a color-coded side-by-side diff in the frontend twin panel.

## Context

Current implementation in `services/shared/twin.py`:

```python
def compute_delta(desired: dict, reported: dict) -> dict:
    """Return desired keys whose values differ from reported."""
    delta: dict = {}
    for key, desired_val in desired.items():
        if reported.get(key) != desired_val:
            delta[key] = desired_val
    return delta
```

This only shows keys in desired that are different from reported. It does not show:
- Keys in reported but NOT in desired (removals)
- Whether a difference is "added" vs "changed"
- The old value for changed keys
- Count of unchanged keys

Current API responses:
- `GET /devices/{id}/twin` returns `delta: dict[str, Any]` (flat)
- `GET /devices/{id}/twin/delta` returns `delta: dict[str, Any]` with `in_sync: bool`

## 1. Update shared/twin.py

Edit file: `services/shared/twin.py`

### 1a. Add new structured delta function

Keep the existing `compute_delta` function for backward compatibility but add a new function:

```python
def compute_structured_delta(desired: dict, reported: dict) -> dict:
    """
    Return a structured diff between desired and reported states.

    Returns:
        {
            "added": {"key": desired_value, ...},       # in desired, not in reported
            "removed": {"key": reported_value, ...},     # in reported, not in desired
            "changed": {                                 # in both, but different values
                "key": {"old_value": reported_val, "new_value": desired_val},
                ...
            },
            "unchanged_count": int,                      # number of matching keys
        }
    """
    desired_keys = set(desired.keys())
    reported_keys = set(reported.keys())

    added_keys = desired_keys - reported_keys
    removed_keys = reported_keys - desired_keys
    common_keys = desired_keys & reported_keys

    added = {k: desired[k] for k in sorted(added_keys)}
    removed = {k: reported[k] for k in sorted(removed_keys)}

    changed = {}
    unchanged_count = 0
    for k in sorted(common_keys):
        if desired[k] != reported[k]:
            changed[k] = {
                "old_value": reported[k],
                "new_value": desired[k],
            }
        else:
            unchanged_count += 1

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged_count,
    }
```

### 1b. Add unit tests

If a test file exists for `shared/twin.py`, add these test cases. If not, consider creating `services/shared/test_twin.py`:

```python
from shared.twin import compute_structured_delta

def test_structured_delta_added():
    desired = {"led": "on", "fan": "high"}
    reported = {"led": "on"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {"fan": "high"}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1

def test_structured_delta_removed():
    desired = {"led": "on"}
    reported = {"led": "on", "fan": "high"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {"fan": "high"}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1

def test_structured_delta_changed():
    desired = {"led": "on", "brightness": 80}
    reported = {"led": "off", "brightness": 50}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {
        "led": {"old_value": "off", "new_value": "on"},
        "brightness": {"old_value": 50, "new_value": 80},
    }
    assert result["unchanged_count"] == 0

def test_structured_delta_all_synced():
    desired = {"led": "on"}
    reported = {"led": "on"}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 1

def test_structured_delta_empty():
    result = compute_structured_delta({}, {})
    assert result["added"] == {}
    assert result["removed"] == {}
    assert result["changed"] == {}
    assert result["unchanged_count"] == 0

def test_structured_delta_complex():
    desired = {"led": "on", "temp_target": 22, "new_key": True}
    reported = {"led": "off", "temp_target": 22, "old_key": False}
    result = compute_structured_delta(desired, reported)
    assert result["added"] == {"new_key": True}
    assert result["removed"] == {"old_key": False}
    assert result["changed"] == {"led": {"old_value": "off", "new_value": "on"}}
    assert result["unchanged_count"] == 1
```

## 2. Backend API Changes

Edit file: `services/ui_iot/routes/devices.py`

### 2a. Import the new function

At the top where `compute_delta` is imported (line ~9):

```python
from shared.twin import compute_delta, compute_structured_delta, sync_status
```

### 2b. Update GET /devices/{device_id}/twin/delta (line ~1024)

Replace the existing endpoint to return the structured delta format:

```python
@router.get("/devices/{device_id}/twin/delta")
async def get_twin_delta(device_id: str, pool=Depends(get_db_pool)):
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT desired_state, reported_state, desired_version, reported_version
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
    structured = compute_structured_delta(desired, reported)

    return {
        "device_id": device_id,
        "added": structured["added"],
        "removed": structured["removed"],
        "changed": structured["changed"],
        "unchanged_count": structured["unchanged_count"],
        "in_sync": (
            len(structured["added"]) == 0
            and len(structured["removed"]) == 0
            and len(structured["changed"]) == 0
        ),
        "desired_version": row["desired_version"],
        "reported_version": row["reported_version"],
        # Keep legacy flat delta for backward compatibility
        "delta": compute_delta(desired, reported),
    }
```

### 2c. Optionally enhance GET /devices/{device_id}/twin

You can also add the structured delta to the main twin response. Add to the return dict of `get_device_twin` (line ~974):

```python
    structured_delta = compute_structured_delta(desired, reported)
    return {
        "device_id": device_id,
        "desired": desired,
        "reported": reported,
        "delta": compute_delta(desired, reported),  # keep for backward compat
        "structured_delta": structured_delta,        # new field
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

Update the `TwinResponse` model to include the new field:

```python
class StructuredDelta(BaseModel):
    added: dict[str, Any] = {}
    removed: dict[str, Any] = {}
    changed: dict[str, Any] = {}
    unchanged_count: int = 0

class TwinResponse(BaseModel):
    device_id: str
    desired: dict[str, Any]
    reported: dict[str, Any]
    delta: dict[str, Any]
    structured_delta: StructuredDelta | None = None
    desired_version: int
    reported_version: int
    sync_status: str
    shadow_updated_at: str | None
```

## 3. Frontend Changes

### 3a. Update TypeScript types

Edit file: `frontend/src/services/api/devices.ts`

Add the new types and extend `TwinDocument`:

```typescript
export interface StructuredDelta {
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  changed: Record<string, { old_value: unknown; new_value: unknown }>;
  unchanged_count: number;
}

// Update existing TwinDocument interface
export interface TwinDocument {
  device_id: string;
  desired: TwinDesired;
  reported: Record<string, unknown>;
  delta: Record<string, unknown>;
  structured_delta?: StructuredDelta;
  desired_version: number;
  reported_version: number;
  sync_status: "synced" | "pending" | "stale";
  shadow_updated_at: string | null;
}
```

### 3b. Update DeviceTwinPanel.tsx with diff view

Edit file: `frontend/src/features/devices/DeviceTwinPanel.tsx`

Replace the simple "Out of sync" banner with a structured diff view. Key changes:

1. **Replace the delta banner** (lines ~83-87) with a detailed diff section:

```tsx
{twin.structured_delta && (
  <DeltaDiffView delta={twin.structured_delta} />
)}
```

2. **Add the DeltaDiffView component** either inline or as a separate file. Inline approach inside the same file:

```tsx
function DeltaDiffView({ delta }: { delta: StructuredDelta }) {
  const hasChanges =
    Object.keys(delta.added).length > 0 ||
    Object.keys(delta.removed).length > 0 ||
    Object.keys(delta.changed).length > 0;

  if (!hasChanges) {
    return (
      <div className="rounded border border-green-300 bg-green-50 px-2 py-1 text-xs text-green-800">
        Twin is in sync ({delta.unchanged_count} key{delta.unchanged_count !== 1 ? "s" : ""} matching)
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Added keys: in desired but not in reported */}
      {Object.keys(delta.added).length > 0 && (
        <div className="rounded border border-green-300 bg-green-50 p-2">
          <div className="text-xs font-semibold text-green-800 mb-1">
            Added ({Object.keys(delta.added).length})
          </div>
          {Object.entries(delta.added).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2 text-xs text-green-900">
              <span className="font-mono font-medium">{key}</span>
              <span className="text-green-600">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Removed keys: in reported but not in desired */}
      {Object.keys(delta.removed).length > 0 && (
        <div className="rounded border border-red-300 bg-red-50 p-2">
          <div className="text-xs font-semibold text-red-800 mb-1">
            Removed ({Object.keys(delta.removed).length})
          </div>
          {Object.entries(delta.removed).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2 text-xs text-red-900">
              <span className="font-mono font-medium">{key}</span>
              <span className="text-red-600 line-through">{JSON.stringify(value)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Changed keys: in both but different values */}
      {Object.keys(delta.changed).length > 0 && (
        <div className="rounded border border-amber-300 bg-amber-50 p-2">
          <div className="text-xs font-semibold text-amber-800 mb-1">
            Changed ({Object.keys(delta.changed).length})
          </div>
          {Object.entries(delta.changed).map(([key, change]) => {
            const typed = change as { old_value: unknown; new_value: unknown };
            return (
              <div key={key} className="flex items-center gap-2 text-xs text-amber-900">
                <span className="font-mono font-medium">{key}</span>
                <span className="text-red-600 line-through">
                  {JSON.stringify(typed.old_value)}
                </span>
                <span className="text-muted-foreground">&rarr;</span>
                <span className="text-green-700">
                  {JSON.stringify(typed.new_value)}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Unchanged count */}
      {delta.unchanged_count > 0 && (
        <div className="text-xs text-muted-foreground">
          {delta.unchanged_count} key{delta.unchanged_count !== 1 ? "s" : ""} unchanged
        </div>
      )}
    </div>
  );
}
```

3. **Import the StructuredDelta type**:
```typescript
import {
  getDeviceTwin,
  type TwinDocument,
  type StructuredDelta,
  updateDesiredState,
  ConflictError,
} from "@/services/api/devices";
```

4. **Keep the old delta banner as fallback** if `structured_delta` is not present (backward compatibility):
```tsx
{twin.structured_delta ? (
  <DeltaDiffView delta={twin.structured_delta} />
) : (
  deltaKeys.length > 0 && (
    <div className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
      Out of sync: {deltaKeys.join(", ")}
    </div>
  )
)}
```

## 4. Verification

```bash
# 1. Set up different desired vs reported states
# First, set desired state
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "If-Match: \"0\"" \
  -X PATCH http://localhost:8000/customer/devices/DEVICE-01/twin/desired \
  -H "Content-Type: application/json" \
  -d '{"desired": {"led": "on", "brightness": 80, "new_config": true}}'

# Device would report a subset with different values (simulated by shadow/reported MQTT)

# 2. Get structured delta
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin/delta | jq .
# Expect:
# {
#   "added": { "new_config": true },
#   "removed": { ... },
#   "changed": { "led": { "old_value": "off", "new_value": "on" } },
#   "unchanged_count": 0,
#   "in_sync": false,
#   ...
# }

# 3. Get twin with structured_delta
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin | jq '.structured_delta'

# 4. Verify backward compatibility -- old "delta" field still present
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/twin | jq '.delta'

# 5. Run unit tests
cd services && python -m pytest shared/test_twin.py -v

# 6. Frontend: open /devices/DEVICE-01, scroll to twin panel
# Verify:
#   - Green section for added keys
#   - Red section for removed keys
#   - Amber section for changed keys with old->new values
#   - "N keys unchanged" text
#   - When synced: green "Twin is in sync" message
```
