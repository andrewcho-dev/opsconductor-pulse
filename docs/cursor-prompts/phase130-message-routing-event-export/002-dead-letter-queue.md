# Task 002 -- Dead Letter Queue

## Commit

```
feat(phase130): add dead letter queue with replay, purge, and operator UI
```

## What This Task Does

1. Creates a `dead_letter_messages` table for failed route deliveries.
2. Modifies the ingest worker to write to DLQ on delivery failure (from task 001).
3. Adds DLQ management API endpoints (list, replay, batch replay, discard, purge).
4. Adds a React frontend page for inspecting and managing DLQ entries.

---

## Step 1: Database Migration

Create file: `db/migrations/082_dead_letter_messages.sql`

```sql
-- Migration 082: Dead letter queue for failed message route deliveries
-- When a route delivery fails (webhook timeout, connection error, MQTT publish failure),
-- the original message is stored here for later inspection, replay, or discard.

CREATE TABLE IF NOT EXISTS dead_letter_messages (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    route_id            INTEGER REFERENCES message_routes(id) ON DELETE SET NULL,
    original_topic      VARCHAR(200) NOT NULL,
    payload             JSONB NOT NULL,
    destination_type    VARCHAR(20) NOT NULL,
    destination_config  JSONB NOT NULL DEFAULT '{}',
    error_message       TEXT,
    attempts            INTEGER NOT NULL DEFAULT 1,
    status              VARCHAR(20) NOT NULL DEFAULT 'FAILED'
                        CHECK (status IN ('FAILED', 'REPLAYED', 'DISCARDED')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    replayed_at         TIMESTAMPTZ
);

-- Primary query pattern: list by tenant + status, newest first
CREATE INDEX IF NOT EXISTS idx_dlq_tenant_status_created
    ON dead_letter_messages (tenant_id, status, created_at DESC);

-- For purge queries: find old FAILED entries
CREATE INDEX IF NOT EXISTS idx_dlq_status_created
    ON dead_letter_messages (status, created_at)
    WHERE status = 'FAILED';

-- For replay: look up by route
CREATE INDEX IF NOT EXISTS idx_dlq_route
    ON dead_letter_messages (route_id)
    WHERE route_id IS NOT NULL;

-- RLS
ALTER TABLE dead_letter_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE dead_letter_messages FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON dead_letter_messages
    FOR ALL TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON dead_letter_messages TO pulse_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON dead_letter_messages TO pulse_operator;
GRANT USAGE ON SEQUENCE dead_letter_messages_id_seq TO pulse_app;
GRANT USAGE ON SEQUENCE dead_letter_messages_id_seq TO pulse_operator;

COMMENT ON TABLE dead_letter_messages IS 'Failed message route deliveries held for inspection, replay, or discard';
COMMENT ON COLUMN dead_letter_messages.status IS 'FAILED = pending action, REPLAYED = successfully re-delivered, DISCARDED = manually dismissed';
```

---

## Step 2: Ingest Worker -- Write to DLQ on Failure

Modify the route delivery failure handler in `services/ingest_iot/ingest.py`.

In the `db_worker` method, replace the `route_delivery_failed` warning log (added in task 001) with DLQ insertion:

```python
except Exception as route_exc:
    # Write to dead letter queue
    try:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await _set_tenant_write_context(conn, tenant_id)
            await conn.execute(
                """
                INSERT INTO dead_letter_messages
                    (tenant_id, route_id, original_topic, payload,
                     destination_type, destination_config, error_message)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
                """,
                tenant_id,
                route["id"],
                topic,
                json.dumps(payload),
                route["destination_type"],
                json.dumps(route.get("destination_config") or {}),
                str(route_exc)[:2000],
            )
    except Exception as dlq_exc:
        logger.error(
            "dlq_write_failed",
            extra={"route_id": route["id"], "error": str(dlq_exc)},
        )
    logger.warning(
        "route_delivery_failed_dlq",
        extra={
            "route_id": route["id"],
            "error": str(route_exc),
            "destination": route["destination_type"],
        },
    )
```

---

## Step 3: DLQ API Routes

Add endpoints to `services/ui_iot/routes/message_routing.py` (same file from task 001).

### 3a. Pydantic Models

```python
class ReplayBatchRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)


class PurgeRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1, le=365)
```

### 3b. List DLQ Entries

```python
@router.get("/dead-letter")
async def list_dead_letter(
    status: Optional[str] = Query(None, description="Filter by status: FAILED, REPLAYED, DISCARDED"),
    route_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    pool=Depends(get_db_pool),
):
    tenant_id = get_tenant_id()

    conditions = ["d.tenant_id = $1"]
    params: list = [tenant_id]

    if status:
        if status.upper() not in ("FAILED", "REPLAYED", "DISCARDED"):
            raise HTTPException(400, "Invalid status filter")
        params.append(status.upper())
        conditions.append(f"d.status = ${len(params)}")

    if route_id is not None:
        params.append(route_id)
        conditions.append(f"d.route_id = ${len(params)}")

    where_clause = " AND ".join(conditions)
    params.extend([limit, offset])

    async with tenant_connection(pool, tenant_id) as conn:
        rows = await conn.fetch(
            f"""
            SELECT d.id, d.tenant_id, d.route_id, d.original_topic, d.payload,
                   d.destination_type, d.destination_config, d.error_message,
                   d.attempts, d.status, d.created_at, d.replayed_at,
                   mr.name AS route_name
            FROM dead_letter_messages d
            LEFT JOIN message_routes mr ON mr.id = d.route_id AND mr.tenant_id = d.tenant_id
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        count_params = params[:-2]  # Remove limit/offset
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM dead_letter_messages d WHERE {where_clause}",
            *count_params,
        )

    return {
        "messages": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
```

### 3c. Replay Single Message

```python
@router.post("/dead-letter/{dlq_id}/replay")
async def replay_dead_letter(dlq_id: int, pool=Depends(get_db_pool)):
    """Re-attempt delivery for a single dead letter message."""
    tenant_id = get_tenant_id()

    async with tenant_connection(pool, tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT id, route_id, original_topic, payload, destination_type,
                   destination_config, attempts, status
            FROM dead_letter_messages
            WHERE tenant_id = $1 AND id = $2
            """,
            tenant_id, dlq_id,
        )

    if not row:
        raise HTTPException(404, "Dead letter message not found")
    if row["status"] != "FAILED":
        raise HTTPException(400, f"Cannot replay message with status {row['status']}")

    # Attempt delivery
    config = row["destination_config"] or {}
    payload = row["payload"] or {}
    delivery_error = None

    try:
        if row["destination_type"] == "webhook":
            url = config.get("url")
            if not url:
                raise Exception("No URL in destination config")
            method = config.get("method", "POST").upper()
            headers = {"Content-Type": "application/json"}
            body_bytes = json.dumps(payload).encode()
            secret = config.get("secret")
            if secret:
                import hashlib
                import hmac as hmac_mod
                sig = hmac_mod.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                headers["X-Signature-SHA256"] = sig

            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.request(method, url, content=body_bytes, headers=headers)
                if resp.status_code >= 400:
                    raise Exception(f"Webhook returned HTTP {resp.status_code}")

        elif row["destination_type"] == "mqtt_republish":
            # Cannot easily republish from UI service -- mark as failed with note
            raise Exception("MQTT republish replay not supported from API; message must be manually re-sent")

    except Exception as exc:
        delivery_error = str(exc)

    async with tenant_connection(pool, tenant_id) as conn:
        if delivery_error:
            # Increment attempts, update error
            await conn.execute(
                """
                UPDATE dead_letter_messages
                SET attempts = attempts + 1,
                    error_message = $3
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id, dlq_id, delivery_error[:2000],
            )
            raise HTTPException(502, f"Replay failed: {delivery_error}")
        else:
            # Mark as replayed
            await conn.execute(
                """
                UPDATE dead_letter_messages
                SET status = 'REPLAYED',
                    replayed_at = NOW(),
                    attempts = attempts + 1
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id, dlq_id,
            )

    return {"id": dlq_id, "status": "REPLAYED", "message": "Message replayed successfully"}
```

### 3d. Batch Replay

```python
@router.post("/dead-letter/replay-batch")
async def replay_dead_letter_batch(body: ReplayBatchRequest, pool=Depends(get_db_pool)):
    """Replay multiple dead letter messages."""
    tenant_id = get_tenant_id()
    results = []

    for dlq_id in body.ids:
        try:
            # Reuse the single replay logic but inline a simplified version
            async with tenant_connection(pool, tenant_id) as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, route_id, original_topic, payload, destination_type,
                           destination_config, attempts, status
                    FROM dead_letter_messages
                    WHERE tenant_id = $1 AND id = $2 AND status = 'FAILED'
                    """,
                    tenant_id, dlq_id,
                )

            if not row:
                results.append({"id": dlq_id, "status": "SKIPPED", "error": "Not found or not in FAILED status"})
                continue

            config = row["destination_config"] or {}
            payload = row["payload"] or {}
            delivery_error = None

            try:
                if row["destination_type"] == "webhook":
                    url = config.get("url")
                    if not url:
                        raise Exception("No URL in destination config")
                    method = config.get("method", "POST").upper()
                    headers = {"Content-Type": "application/json"}
                    body_bytes = json.dumps(payload).encode()

                    import httpx
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.request(method, url, content=body_bytes, headers=headers)
                        if resp.status_code >= 400:
                            raise Exception(f"HTTP {resp.status_code}")
                else:
                    raise Exception(f"Replay not supported for {row['destination_type']}")
            except Exception as exc:
                delivery_error = str(exc)

            async with tenant_connection(pool, tenant_id) as conn:
                if delivery_error:
                    await conn.execute(
                        """
                        UPDATE dead_letter_messages
                        SET attempts = attempts + 1, error_message = $3
                        WHERE tenant_id = $1 AND id = $2
                        """,
                        tenant_id, dlq_id, delivery_error[:2000],
                    )
                    results.append({"id": dlq_id, "status": "FAILED", "error": delivery_error})
                else:
                    await conn.execute(
                        """
                        UPDATE dead_letter_messages
                        SET status = 'REPLAYED', replayed_at = NOW(), attempts = attempts + 1
                        WHERE tenant_id = $1 AND id = $2
                        """,
                        tenant_id, dlq_id,
                    )
                    results.append({"id": dlq_id, "status": "REPLAYED"})

        except Exception as exc:
            results.append({"id": dlq_id, "status": "ERROR", "error": str(exc)})

    return {
        "results": results,
        "total": len(results),
        "replayed": sum(1 for r in results if r["status"] == "REPLAYED"),
        "failed": sum(1 for r in results if r["status"] in ("FAILED", "ERROR")),
    }
```

### 3e. Discard Single Message

```python
@router.delete("/dead-letter/{dlq_id}")
async def discard_dead_letter(dlq_id: int, pool=Depends(get_db_pool)):
    """Mark a dead letter message as DISCARDED."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        res = await conn.execute(
            """
            UPDATE dead_letter_messages
            SET status = 'DISCARDED'
            WHERE tenant_id = $1 AND id = $2 AND status = 'FAILED'
            """,
            tenant_id, dlq_id,
        )
    if res.endswith("0"):
        raise HTTPException(404, "Dead letter message not found or already processed")
    return {"id": dlq_id, "status": "DISCARDED"}
```

### 3f. Purge Old Failed Messages

```python
@router.delete("/dead-letter/purge")
async def purge_dead_letter(
    older_than_days: int = Query(default=30, ge=1, le=365),
    pool=Depends(get_db_pool),
):
    """Purge (hard delete) all FAILED messages older than N days."""
    tenant_id = get_tenant_id()
    async with tenant_connection(pool, tenant_id) as conn:
        result = await conn.execute(
            """
            DELETE FROM dead_letter_messages
            WHERE tenant_id = $1
              AND status = 'FAILED'
              AND created_at < NOW() - INTERVAL '1 day' * $2
            """,
            tenant_id, older_than_days,
        )
    # Parse "DELETE N" result
    deleted = 0
    try:
        deleted = int(result.split()[-1])
    except (ValueError, IndexError):
        pass
    return {"purged": deleted, "older_than_days": older_than_days}
```

**Important**: Make sure the purge endpoint (`DELETE /dead-letter/purge`) is registered **before** the discard endpoint (`DELETE /dead-letter/{dlq_id}`) in the router, otherwise FastAPI will try to parse "purge" as an integer `dlq_id`.

---

## Step 4: Frontend -- Dead Letter Page

### 4a. API Service

Create file: `frontend/src/services/api/deadLetter.ts`

```typescript
import { apiFetch } from "../apiFetch";

export interface DeadLetterMessage {
  id: number;
  tenant_id: string;
  route_id: number | null;
  route_name: string | null;
  original_topic: string;
  payload: Record<string, unknown>;
  destination_type: string;
  destination_config: Record<string, unknown>;
  error_message: string | null;
  attempts: number;
  status: "FAILED" | "REPLAYED" | "DISCARDED";
  created_at: string;
  replayed_at: string | null;
}

export interface DeadLetterListResponse {
  messages: DeadLetterMessage[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchDeadLetterMessages(params: {
  status?: string;
  route_id?: number;
  limit?: number;
  offset?: number;
}): Promise<DeadLetterListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.route_id) query.set("route_id", String(params.route_id));
  if (params.limit) query.set("limit", String(params.limit));
  if (params.offset) query.set("offset", String(params.offset));
  return apiFetch(`/customer/dead-letter?${query.toString()}`);
}

export async function replayDeadLetter(id: number): Promise<{ id: number; status: string }> {
  return apiFetch(`/customer/dead-letter/${id}/replay`, { method: "POST" });
}

export async function replayDeadLetterBatch(ids: number[]): Promise<{
  results: Array<{ id: number; status: string; error?: string }>;
  total: number;
  replayed: number;
  failed: number;
}> {
  return apiFetch("/customer/dead-letter/replay-batch", {
    method: "POST",
    body: JSON.stringify({ ids }),
  });
}

export async function discardDeadLetter(id: number): Promise<{ id: number; status: string }> {
  return apiFetch(`/customer/dead-letter/${id}`, { method: "DELETE" });
}

export async function purgeDeadLetter(olderThanDays: number): Promise<{
  purged: number;
  older_than_days: number;
}> {
  return apiFetch(`/customer/dead-letter/purge?older_than_days=${olderThanDays}`, {
    method: "DELETE",
  });
}
```

### 4b. Dead Letter Page Component

Create file: `frontend/src/features/messaging/DeadLetterPage.tsx`

Build this page following the same pattern as `frontend/src/features/delivery/DeliveryLogPage.tsx`:

```tsx
import { Fragment, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  fetchDeadLetterMessages,
  replayDeadLetter,
  replayDeadLetterBatch,
  discardDeadLetter,
  purgeDeadLetter,
} from "@/services/api/deadLetter";
import type { DeadLetterMessage } from "@/services/api/deadLetter";

const LIMIT = 50;

function statusVariant(status: string): "secondary" | "destructive" | "default" {
  if (status === "FAILED") return "destructive";
  if (status === "REPLAYED") return "default";
  return "secondary";
}

export default function DeadLetterPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("FAILED");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const { data, isLoading, error } = useQuery({
    queryKey: ["dead-letter", statusFilter, offset],
    queryFn: () =>
      fetchDeadLetterMessages({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        limit: LIMIT,
        offset,
      }),
  });

  const replayMutation = useMutation({
    mutationFn: replayDeadLetter,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });

  const batchReplayMutation = useMutation({
    mutationFn: (ids: number[]) => replayDeadLetterBatch(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dead-letter"] });
      setSelected(new Set());
    },
  });

  const discardMutation = useMutation({
    mutationFn: discardDeadLetter,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });

  const purgeMutation = useMutation({
    mutationFn: () => purgeDeadLetter(30),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });

  const messages = data?.messages ?? [];
  const total = data?.total ?? 0;

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === messages.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(messages.filter((m) => m.status === "FAILED").map((m) => m.id)));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dead Letter Queue"
        description={`${total} messages`}
      />

      <div className="flex items-center gap-2 flex-wrap">
        <Select
          value={statusFilter}
          onValueChange={(v) => { setStatusFilter(v); setOffset(0); }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All</SelectItem>
            <SelectItem value="FAILED">Failed</SelectItem>
            <SelectItem value="REPLAYED">Replayed</SelectItem>
            <SelectItem value="DISCARDED">Discarded</SelectItem>
          </SelectContent>
        </Select>

        {selected.size > 0 && (
          <>
            <Button
              size="sm"
              onClick={() => batchReplayMutation.mutate([...selected])}
              disabled={batchReplayMutation.isPending}
            >
              Replay Selected ({selected.size})
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                [...selected].forEach((id) => discardMutation.mutate(id));
                setSelected(new Set());
              }}
            >
              Discard Selected
            </Button>
          </>
        )}

        <div className="ml-auto">
          <Button
            size="sm"
            variant="destructive"
            onClick={() => {
              if (confirm("Purge all FAILED messages older than 30 days?")) {
                purgeMutation.mutate();
              }
            }}
            disabled={purgeMutation.isPending}
          >
            Purge Old
          </Button>
        </div>
      </div>

      {/* Render table with columns: checkbox, timestamp, route name, topic, error, status, actions */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8">
              <Checkbox
                checked={selected.size > 0 && selected.size === messages.filter(m => m.status === "FAILED").length}
                onCheckedChange={toggleAll}
              />
            </TableHead>
            <TableHead>Timestamp</TableHead>
            <TableHead>Route</TableHead>
            <TableHead>Topic</TableHead>
            <TableHead>Error</TableHead>
            <TableHead>Attempts</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
          ) : messages.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                No dead letter messages
              </TableCell>
            </TableRow>
          ) : (
            messages.map((msg) => (
              <TableRow key={msg.id}>
                <TableCell>
                  {msg.status === "FAILED" && (
                    <Checkbox
                      checked={selected.has(msg.id)}
                      onCheckedChange={() => toggleSelect(msg.id)}
                    />
                  )}
                </TableCell>
                <TableCell className="whitespace-nowrap text-sm">
                  {new Date(msg.created_at).toLocaleString()}
                </TableCell>
                <TableCell className="text-sm">
                  {msg.route_name ?? `Route #${msg.route_id ?? "?"}`}
                </TableCell>
                <TableCell className="text-sm font-mono max-w-[200px] truncate">
                  {msg.original_topic}
                </TableCell>
                <TableCell className="text-sm max-w-[300px] truncate text-destructive">
                  {msg.error_message}
                </TableCell>
                <TableCell className="text-sm">{msg.attempts}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(msg.status)}>{msg.status}</Badge>
                </TableCell>
                <TableCell>
                  {msg.status === "FAILED" && (
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => replayMutation.mutate(msg.id)}
                        disabled={replayMutation.isPending}
                      >
                        Replay
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => discardMutation.mutate(msg.id)}
                        disabled={discardMutation.isPending}
                      >
                        Discard
                      </Button>
                    </div>
                  )}
                  {msg.status === "REPLAYED" && msg.replayed_at && (
                    <span className="text-xs text-muted-foreground">
                      {new Date(msg.replayed_at).toLocaleString()}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Showing {offset + 1}-{Math.min(offset + LIMIT, total)} of {total}
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={offset + LIMIT >= total}
            onClick={() => setOffset(offset + LIMIT)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
```

### 4c. Register Route in Router

Edit `frontend/src/app/router.tsx`:

1. Add import at the top:

```typescript
import DeadLetterPage from "@/features/messaging/DeadLetterPage";
```

2. Add route in the customer children array (after the `delivery-log` route, around line 105):

```typescript
{ path: "dead-letter", element: <DeadLetterPage /> },
```

### 4d. Add Sidebar Link

Find the sidebar navigation component (likely in `frontend/src/components/layout/AppShell.tsx` or a separate nav component) and add a "Dead Letter Queue" link under the messaging/integrations section:

```typescript
{ label: "Dead Letter Queue", href: "/dead-letter", icon: AlertTriangleIcon }
```

---

## Step 5: API Service Helper (if not existing)

If `frontend/src/services/apiFetch.ts` does not exist, check the existing pattern in `frontend/src/services/api/delivery.ts` and follow the same import/fetch pattern. The `apiFetch` function should:

- Add Authorization header from stored token
- Add Content-Type: application/json for POST/PUT/DELETE
- Add X-CSRF-Token header
- Return parsed JSON response
- Throw on non-OK responses

---

## Verification

```bash
# Apply migration
psql -h localhost -U iot -d iotcloud -f db/migrations/082_dead_letter_messages.sql

# Verify table exists
psql -h localhost -U iot -d iotcloud -c "\d dead_letter_messages"

# Create a route pointing to a broken URL
curl -s -X POST http://localhost:8080/customer/message-routes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{
    "name": "Broken webhook",
    "topic_filter": "tenant/+/device/+/telemetry",
    "destination_type": "webhook",
    "destination_config": {"url": "http://192.0.2.1:9999/nowhere"},
    "is_enabled": true
  }'

# Send telemetry to trigger the route
mosquitto_pub -h localhost -p 1883 \
  -t "tenant/TENANT1/device/DEV-001/telemetry" \
  -m '{"ts":"2026-02-16T00:00:00Z","site_id":"SITE-1","provision_token":"test","metrics":{"temperature":95}}'

# List DLQ entries (should show the failed delivery)
curl -s http://localhost:8080/customer/dead-letter \
  -H "Authorization: Bearer $TOKEN" | jq .

# Fix the route URL
curl -s -X PUT http://localhost:8080/customer/message-routes/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"destination_config": {"url": "https://httpbin.org/post"}}'

# Replay the failed message
curl -s -X POST http://localhost:8080/customer/dead-letter/1/replay \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" | jq .

# Verify status changed to REPLAYED
curl -s "http://localhost:8080/customer/dead-letter?status=REPLAYED" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Test batch replay
curl -s -X POST http://localhost:8080/customer/dead-letter/replay-batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"ids": [1, 2, 3]}' | jq .

# Test purge
curl -s -X DELETE "http://localhost:8080/customer/dead-letter/purge?older_than_days=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-CSRF-Token: $CSRF" | jq .

# Frontend: navigate to /app/dead-letter and verify the table renders
```
