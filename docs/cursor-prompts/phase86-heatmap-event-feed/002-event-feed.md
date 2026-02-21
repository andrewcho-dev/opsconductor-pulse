# Prompt 002 — Live Scrolling Event Feed

Read `frontend/src/features/operator/SystemDashboard.tsx` errors section
to understand the existing error data format.

## Create `frontend/src/features/operator/noc/LiveEventFeed.tsx`

A scrolling real-time feed of system events — the "heartbeat" of the platform.

### Events to show (newest first):
1. **System errors** — from GET /operator/system/errors?hours=1
2. **Alert fires** — from GET /operator/alerts?limit=20&status=OPEN (recently opened)
3. **Tenant activity** — from GET /operator/tenants (last_active_at changes)

Combine and sort by timestamp descending. Show last 50 events max.

### Event row format:
```
[14:32:01] [ERROR]   delivery_failure    tenant: acme-corp  device: pump-a
[14:31:55] [ALERT]   CRITICAL threshold  tenant: beta-inc   device: sensor-1
[14:31:12] [INFO]    tenant active       tenant: gamma-llc  12 devices online
```

Color coding per event type:
- ERROR: red text `text-red-400`
- ALERT (CRITICAL/HIGH): orange text `text-orange-400`
- ALERT (MEDIUM/LOW): yellow text `text-yellow-400`
- INFO: gray text `text-gray-400`

### Implementation:
```typescript
interface FeedEvent {
  id: string;
  timestamp: string;
  type: 'error' | 'alert' | 'info';
  severity?: string;
  message: string;
  tenant?: string;
  device?: string;
}
```

Auto-scroll to top on new events.
New events flash briefly (animate-pulse for 2s then settle).

```typescript
// Auto-scroll
const feedRef = useRef<HTMLDivElement>(null);
useEffect(() => {
  feedRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
}, [events]);
```

### Layout:
- Dark card: `bg-gray-900 border-gray-700`
- Title: "Live Event Feed" with pulsing green dot indicator
- Font: monospace `font-mono text-xs`
- Scrollable div: `h-48 overflow-y-auto`
- Fetches every 10 seconds

### Header with live indicator:
```typescript
<div className="flex items-center gap-2">
  <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
  <span className="text-sm font-medium text-gray-300">Live Event Feed</span>
  <span className="text-xs text-gray-500 ml-auto">{events.length} events</span>
</div>
```

## Acceptance Criteria
- [ ] LiveEventFeed.tsx renders scrollable event list
- [ ] Events from errors + alerts combined and sorted by time
- [ ] Color coding by event type/severity
- [ ] Monospace font
- [ ] Auto-scrolls to newest events
- [ ] Pulsing green dot in header
- [ ] Refreshes every 10s
- [ ] `npm run build` passes
