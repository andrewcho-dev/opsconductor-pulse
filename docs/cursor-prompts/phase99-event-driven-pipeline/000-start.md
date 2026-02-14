# Phase 99 — Event-Driven Evaluator via PostgreSQL LISTEN/NOTIFY

## Context

The dispatcher and WebSocket already use PostgreSQL LISTEN/NOTIFY with polling fallback.
The evaluator uses pure 5-second polling of the telemetry table — it has no NOTIFY path.

End-to-end alert latency today:
1. Device sends telemetry → ingest writes to timescale: ~1s
2. Evaluator polls telemetry every 5s: up to 5s wait
3. Evaluator writes to fleet_alert: ~0.1s
4. Dispatcher receives NOTIFY (already event-driven): ~0.1s
5. Delivery worker polls notification_jobs every 2s: up to 2s wait
6. **Total: up to ~8 seconds**

With NOTIFY on ingest write → evaluator LISTEN:
- Step 2 drops from "up to 5s" to "<0.5s"
- **Total: under 4 seconds**

## Fix

Add a PostgreSQL NOTIFY call in the ingest write path.
Update the evaluator to LISTEN for that notification and wake up immediately.
Keep the 5s poll as a fallback (already handles cases where NOTIFY is missed).

## Files to execute in order

| File | What it does |
|------|-------------|
| `001-ingest-notify.md` | Add NOTIFY to ingest telemetry write path |
| `002-evaluator-listen.md` | Update evaluator to LISTEN + wake on NOTIFY |
| `003-verify.md` | Measure latency improvement |
