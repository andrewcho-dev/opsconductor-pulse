# Prompt 005 — Verify Phase 66

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Backend WebSocket
- [ ] `fleet_subscription` field on WSConnection
- [ ] `subscribe_fleet()` / `unsubscribe_fleet()` / `broadcast_fleet_summary()` on ConnectionManager
- [ ] WS handler accepts `{"action": "subscribe", "type": "fleet"}`
- [ ] LISTEN/NOTIFY triggers broadcast to fleet subscribers
- [ ] Message shape: `{"type": "fleet_summary", "data": {online, stale, offline, total, active_alerts}}`

### Frontend
- [ ] `use-fleet-summary-ws.ts` exists
- [ ] Sends fleet subscribe message on connect
- [ ] Auto-reconnects with backoff
- [ ] FleetSummaryWidget uses WS hook
- [ ] "● Live" badge when connected
- [ ] "○ Polling" badge when not connected

### Unit Tests
- [ ] test_fleet_ws.py with 6 tests

## Report

Output PASS / FAIL per criterion.
