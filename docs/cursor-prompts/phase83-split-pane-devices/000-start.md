# Phase 83 — Split-Pane Device List + Detail

## Overview
Replace the current modal-heavy device workflow with a split-pane layout (AWS
console pattern): device list on the left, device detail on the right. Clicking
a device populates the right pane without navigating away from the list. The
device detail pane contains tabs for Overview, Telemetry, Alerts, Tokens, and
Uptime — all already built in previous phases, just reorganized.

No backend changes needed.

## Execution Order
1. 001-split-layout.md — Split-pane layout for DeviceListPage
2. 002-detail-pane.md — Device detail pane with tabs
3. 003-verify.md — Build check + checklist
