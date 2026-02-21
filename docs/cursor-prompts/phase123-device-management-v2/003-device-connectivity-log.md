# Task 003: Device Connectivity Log

## Goal

Track device connectivity state transitions (CONNECTED, DISCONNECTED, CONNECTION_LOST) in a new `device_connection_events` table. Events are logged when the evaluator detects status changes (ONLINE <-> STALE). A new API endpoint and frontend tab surface the event timeline.

## Context

The evaluator (`services/evaluator_iot/evaluator.py`) already detects status transitions. Around line 1086-1110, the upsert to `device_state` uses a `RETURNING` clause that exposes `previous_status` and `new_status`. When they differ (line 1104: `if previous_status and previous_status != new_status`), it currently logs an audit event. We will hook into this same location to INSERT a connection event.

Key existing code in evaluator.py (~line 1060-1110):

```python
row = await conn.fetchrow(
    """
    ... INSERT INTO device_state ...
    ON CONFLICT ... DO UPDATE SET ...
    RETURNING
      (SELECT status FROM existing) AS previous_status,
      status AS new_status,
      last_state_change_at
    """,
    ...
)
if row:
    previous_status = row["previous_status"]
    new_status = row["new_status"]
    if previous_status and previous_status != new_status:
        # audit log happens here
```

## 1. Database Migration

Create file: `db/migrations/082_device_connection_events.sql`

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS device_connection_events (
    id          BIGSERIAL,
    tenant_id   TEXT         NOT NULL,
    device_id   TEXT         NOT NULL,
    event_type  VARCHAR(20)  NOT NULL,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    details     JSONB        NOT NULL DEFAULT '{}',
    PRIMARY KEY (id)
);

-- Constrain event_type values
ALTER TABLE device_connection_events
    ADD CONSTRAINT chk_connection_event_type
    CHECK (event_type IN ('CONNECTED', 'DISCONNECTED', 'CONNECTION_LOST'));

-- Primary query pattern: device event timeline, newest first
CREATE INDEX IF NOT EXISTS idx_device_conn_events_lookup
    ON device_connection_events (tenant_id, device_id, timestamp DESC);

-- RLS
ALTER TABLE device_connection_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS device_connection_events_tenant_isolation ON device_connection_events;
CREATE POLICY device_connection_events_tenant_isolation ON device_connection_events
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

COMMENT ON TABLE device_connection_events IS
    'Append-only log of device connectivity state changes (CONNECTED/DISCONNECTED/CONNECTION_LOST).';

-- Optional: auto-purge old events after 90 days (if TimescaleDB retention policies are in use)
-- This is a regular table, not a hypertable, so use a simple background job or cron.
-- For now, rely on manual cleanup or add a retention migration later.

COMMIT;
```

## 2. Evaluator Changes

Edit file: `services/evaluator_iot/evaluator.py`

### 2a. Add connection event insert helper

Add this function near the other helper functions (after `close_alert` around line 200):

```python
async def log_connection_event(
    conn,
    tenant_id: str,
    device_id: str,
    event_type: str,
    details: dict | None = None,
) -> None:
    """
    Insert a device connection event.
    event_type: CONNECTED, DISCONNECTED, or CONNECTION_LOST
    """
    try:
        await conn.execute(
            """
            INSERT INTO device_connection_events (tenant_id, device_id, event_type, details)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            tenant_id,
            device_id,
            event_type,
            json.dumps(details or {}),
        )
    except Exception:
        logger.warning(
            "Failed to log connection event",
            extra={"tenant_id": tenant_id, "device_id": device_id, "event_type": event_type},
            exc_info=True,
        )
```

### 2b. Hook into the status transition detection

Find the code block around line 1101-1110 where `previous_status != new_status` is detected. Add the connection event logging **right after the existing audit log call**, inside the same `if` block:

```python
if row:
    previous_status = row["previous_status"]
    new_status = row["new_status"]
    if previous_status and previous_status != new_status:
        # Existing audit log code stays here...
        audit = get_audit_logger()
        if audit:
            audit.device_state_change(
                tenant_id,
                device_id,
                # ... existing params ...
            )

        # NEW: Log connection event
        if new_status == "ONLINE":
            await log_connection_event(
                conn,
                tenant_id,
                device_id,
                "CONNECTED",
                {
                    "previous_status": previous_status,
                    "trigger": "heartbeat_resumed",
                },
            )
        elif new_status == "STALE" and previous_status == "ONLINE":
            await log_connection_event(
                conn,
                tenant_id,
                device_id,
                "DISCONNECTED",
                {
                    "previous_status": previous_status,
                    "trigger": "heartbeat_timeout",
                    "stale_threshold_seconds": HEARTBEAT_STALE_SECONDS,
                },
            )
```

### 2c. Handle first-time device (no previous_status)

Also handle the case where `previous_status is None` (first time the device appears in device_state). Right after the existing status change detection block:

```python
    # First time seeing this device (INSERT, not UPDATE)
    if previous_status is None and new_status == "ONLINE":
        await log_connection_event(
            conn,
            tenant_id,
            device_id,
            "CONNECTED",
            {"previous_status": None, "trigger": "first_seen"},
        )
```

### 2d. Ensure the connection event table exists

Add to the evaluator's `ensure_schema` DDL string or use a guard. Since we have the migration, this is optional -- but to be safe, add a CREATE TABLE IF NOT EXISTS to the DDL constant. Alternatively, just rely on the migration being applied before the evaluator starts (which is the existing pattern).

## 3. Backend API Endpoint

Edit file: `services/ui_iot/routes/devices.py`

Add a new endpoint after the twin endpoints (around line 1047):

```python
@router.get("/devices/{device_id}/connections")
async def list_device_connections(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool=Depends(get_db_pool),
):
    """Paginated list of device connectivity events, newest first."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        # Verify device exists
        exists = await conn.fetchval(
            "SELECT 1 FROM device_state WHERE tenant_id = $1 AND device_id = $2",
            tenant_id,
            device_id,
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Device not found")

        rows = await conn.fetch(
            """
            SELECT id, event_type, timestamp, details
            FROM device_connection_events
            WHERE tenant_id = $1 AND device_id = $2
            ORDER BY timestamp DESC
            LIMIT $3 OFFSET $4
            """,
            tenant_id,
            device_id,
            limit,
            offset,
        )

        total_row = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM device_connection_events
            WHERE tenant_id = $1 AND device_id = $2
            """,
            tenant_id,
            device_id,
        )

    events = []
    for r in rows:
        e = dict(r)
        e["id"] = str(e["id"])
        if isinstance(e.get("details"), str):
            e["details"] = json.loads(e["details"])
        if e.get("timestamp"):
            e["timestamp"] = e["timestamp"].isoformat()
        events.append(e)

    return {
        "device_id": device_id,
        "events": events,
        "total": total_row or 0,
        "limit": limit,
        "offset": offset,
    }
```

Make sure `Query` is imported from fastapi at the top of the file:
```python
from fastapi import Query
```

## 4. Frontend

### 4a. API client function

Edit file: `frontend/src/services/api/devices.ts`

Add new types and function:

```typescript
export interface ConnectionEvent {
  id: string;
  event_type: "CONNECTED" | "DISCONNECTED" | "CONNECTION_LOST";
  timestamp: string;
  details: Record<string, unknown>;
}

export interface ConnectionEventsResponse {
  device_id: string;
  events: ConnectionEvent[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchDeviceConnections(
  deviceId: string,
  limit = 50,
  offset = 0,
): Promise<ConnectionEventsResponse> {
  return apiGet(
    `/customer/devices/${encodeURIComponent(deviceId)}/connections?limit=${limit}&offset=${offset}`,
  );
}
```

### 4b. New DeviceConnectivityPanel component

Create file: `frontend/src/features/devices/DeviceConnectivityPanel.tsx`

```tsx
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  fetchDeviceConnections,
  type ConnectionEvent,
  type ConnectionEventsResponse,
} from "@/services/api/devices";

interface DeviceConnectivityPanelProps {
  deviceId: string;
}

const EVENT_STYLES: Record<
  ConnectionEvent["event_type"],
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  CONNECTED: { label: "Connected", variant: "default" },
  DISCONNECTED: { label: "Disconnected", variant: "secondary" },
  CONNECTION_LOST: { label: "Connection Lost", variant: "destructive" },
};

export function DeviceConnectivityPanel({ deviceId }: DeviceConnectivityPanelProps) {
  const [data, setData] = useState<ConnectionEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = async (offset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchDeviceConnections(deviceId, 50, offset);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connectivity events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadEvents();
  }, [deviceId]);

  if (loading && !data) {
    return (
      <div className="rounded border border-border p-3 text-sm text-muted-foreground">
        Loading connectivity events...
      </div>
    );
  }

  return (
    <div className="rounded border border-border p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Connectivity Log</h4>
        <Button size="sm" variant="outline" onClick={() => void loadEvents()}>
          Refresh
        </Button>
      </div>

      {error && <div className="text-xs text-destructive">{error}</div>}

      {data && data.events.length === 0 && (
        <div className="text-sm text-muted-foreground">No connectivity events recorded yet.</div>
      )}

      {data && data.events.length > 0 && (
        <div className="space-y-2">
          {data.events.map((event) => {
            const style = EVENT_STYLES[event.event_type] ?? EVENT_STYLES.DISCONNECTED;
            const ts = new Date(event.timestamp);
            return (
              <div
                key={event.id}
                className="flex items-start gap-3 rounded border border-border p-2"
              >
                <Badge variant={style.variant} className="mt-0.5 shrink-0">
                  {style.label}
                </Badge>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-muted-foreground">
                    {ts.toLocaleString()}
                  </div>
                  {event.details && Object.keys(event.details).length > 0 && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {Object.entries(event.details)
                        .filter(([, v]) => v != null)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(" | ")}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {data && data.total > data.events.length + (data.offset ?? 0) && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => void loadEvents((data.offset ?? 0) + data.events.length)}
        >
          Load more
        </Button>
      )}

      {data && (
        <div className="text-xs text-muted-foreground">
          Showing {data.events.length} of {data.total} events
        </div>
      )}
    </div>
  );
}
```

### 4c. Add to DeviceDetailPage

Edit file: `frontend/src/features/devices/DeviceDetailPage.tsx`

1. Import the new panel:
   ```typescript
   import { DeviceConnectivityPanel } from "./DeviceConnectivityPanel";
   ```

2. Add it to the page layout, after the twin panel (around line 200-201):
   ```tsx
   {deviceId && <DeviceTwinPanel deviceId={deviceId} />}
   {deviceId && <DeviceConnectivityPanel deviceId={deviceId} />}
   {deviceId && <DeviceCommandPanel deviceId={deviceId} />}
   ```

## 5. Verification

```bash
# 1. Apply migration
docker compose exec iot-postgres psql -U iot -d iotcloud -f /migrations/082_device_connection_events.sql

# 2. Verify table exists
docker compose exec iot-postgres psql -U iot -d iotcloud -c "\d device_connection_events"

# 3. Restart evaluator
docker compose restart evaluator-iot

# 4. Simulate a device going online then offline:
# - Send telemetry for DEVICE-01 (it will go ONLINE)
# - Stop sending telemetry and wait HEARTBEAT_STALE_SECONDS (default 30s)
# - Send telemetry again

# 5. Query events via API
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/customer/devices/DEVICE-01/connections?limit=10 | jq .
# Expect: events array with CONNECTED/DISCONNECTED entries

# 6. Check evaluator logs for connection event logging
docker compose logs evaluator-iot --tail=50 | grep "connection"

# 7. Frontend: navigate to /devices/DEVICE-01, scroll to Connectivity Log panel
# Verify events appear with correct badges and timestamps
```
