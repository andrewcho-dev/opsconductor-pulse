# Prompt 002 — Frontend: useFleetSummaryWS Hook

Read `frontend/src/hooks/use-fleet-summary.ts` (existing REST polling hook).
Read how the frontend WebSocket is used elsewhere (look for useWebSocket or ws usage in `frontend/src/`).

## Create `frontend/src/hooks/use-fleet-summary-ws.ts`

```typescript
import { useEffect, useRef, useState, useCallback } from 'react';

export interface FleetSummary {
  online: number;
  stale: number;
  offline: number;
  total: number;
  active_alerts: number;
}

export interface UseFleetSummaryWSResult {
  summary: FleetSummary | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;  // manual REST fallback
}

/**
 * useFleetSummaryWS
 *
 * Subscribes to the fleet_summary channel over WebSocket.
 * Falls back to REST polling (GET /customer/devices/summary) if:
 * - WebSocket not available
 * - WS disconnects and does not reconnect within 5 seconds
 *
 * Reconnects automatically on disconnect (max 5 retries with exponential backoff).
 */
export function useFleetSummaryWS(): UseFleetSummaryWSResult {
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const MAX_RETRIES = 5;

  const connect = useCallback(() => {
    // Get auth token (use existing pattern from codebase)
    const token = getAuthToken();  // replace with actual auth token getter
    if (!token) return;

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/v2/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
      retriesRef.current = 0;
      ws.send(JSON.stringify({ action: 'subscribe', type: 'fleet' }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'fleet_summary') {
          setSummary(msg.data);
          setIsLoading(false);
        }
      } catch {}
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (retriesRef.current < MAX_RETRIES) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 30000);
        retriesRef.current++;
        setTimeout(connect, delay);
      } else {
        setError('WebSocket disconnected');
      }
    };

    ws.onerror = () => setError('WebSocket error');
  }, []);

  const refetch = useCallback(async () => {
    // REST fallback
    try {
      const res = await fetch('/customer/devices/summary', {
        headers: { Authorization: `Bearer ${getAuthToken()}` }
      });
      const data = await res.json();
      setSummary(data);
      setIsLoading(false);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    connect();
    // Fallback REST poll every 30s in case WS misses an event
    const interval = setInterval(refetch, 30000);
    return () => {
      wsRef.current?.close();
      clearInterval(interval);
    };
  }, [connect, refetch]);

  return { summary, isConnected, isLoading, error, refetch };
}
```

Note: Replace `getAuthToken()` with whatever pattern the codebase uses to get the JWT token for API calls.

## Acceptance Criteria

- [ ] `use-fleet-summary-ws.ts` exists
- [ ] Sends `{"action": "subscribe", "type": "fleet"}` on connect
- [ ] Updates summary on `fleet_summary` messages
- [ ] Auto-reconnects with exponential backoff (max 5 retries)
- [ ] REST fallback poll every 30s
- [ ] `npm run build` passes
