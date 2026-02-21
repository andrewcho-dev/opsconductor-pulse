# Phase 86 — Alert Volume Heatmap + Live Event Feed

## Overview
Two situational awareness panels added to the NOC page:
1. **Alert Volume Heatmap** — ECharts calendar heatmap showing alert fire density
   across 7 days × 24 hours (like GitHub's contribution graph but for alerts)
2. **Live Event Feed** — scrolling real-time stream of system events (errors,
   alert fires, tenant activity) — the "system heartbeat"

These panels are added to the NOCPage from Phase 84 as additional rows.
No backend changes needed — uses existing /operator/system/errors endpoint
and /customer/alerts data.

## Execution Order
1. 001-heatmap.md — Alert volume calendar heatmap
2. 002-event-feed.md — Live scrolling event feed
3. 003-wire.md — Add both panels to NOCPage
4. 004-verify.md — Build check + checklist
