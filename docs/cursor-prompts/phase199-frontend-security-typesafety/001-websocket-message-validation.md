# Task 1: Add Runtime Validation for WebSocket Messages

## Context

`frontend/src/services/websocket/manager.ts:62-68` parses incoming WebSocket messages and casts them directly to `WsServerMessage` with no runtime validation. A message with an unexpected shape silently passes type checks (TypeScript is erased at runtime) and can cause crashes or state corruption downstream.

## Actions

1. Read `frontend/src/services/websocket/manager.ts` in full.

2. Find the `WsServerMessage` type definition (it may be in a separate types file — follow the import). Read it.

3. Create Zod schemas that mirror the `WsServerMessage` discriminated union. Place them in the same file or in a co-located `manager.schemas.ts` file:

```typescript
import { z } from "zod";

const WsAlertMessageSchema = z.object({
  type: z.literal("alerts"),
  alerts: z.array(z.unknown()),  // Tighten further once alert shape is known
});

const WsTelemetryMessageSchema = z.object({
  type: z.literal("telemetry"),
  device_id: z.string(),
  data: z.record(z.unknown()),
});

const WsConnectedMessageSchema = z.object({
  type: z.literal("connected"),
});

// Add other message types by reading the WsServerMessage union
const WsServerMessageSchema = z.discriminatedUnion("type", [
  WsAlertMessageSchema,
  WsTelemetryMessageSchema,
  WsConnectedMessageSchema,
  // ... add all types
]);
```

4. In `onmessage`, replace the direct cast with schema validation:

```typescript
this.ws.onmessage = (event) => {
  try {
    const raw = JSON.parse(event.data);
    const result = WsServerMessageSchema.safeParse(raw);
    if (!result.success) {
      console.error("WebSocketManager: unexpected message shape", result.error, raw);
      return;
    }
    this.handleMessage(result.data);
  } catch (err) {
    console.error("WebSocketManager: Failed to parse message", err);
  }
};
```

5. Do not change any message handling logic — only the parsing/validation step.

## Verification

```bash
grep -n 'as WsServerMessage\|as unknown as' frontend/src/services/websocket/manager.ts
# Must return zero results

grep -n 'safeParse\|WsServerMessageSchema' frontend/src/services/websocket/manager.ts
# Must show schema validation
```
