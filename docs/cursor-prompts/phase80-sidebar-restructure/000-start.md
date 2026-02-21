# Phase 80 — Sidebar Restructure: Grouped Collapsible Navigation

## Overview
Restructure AppSidebar to use collapsible section groups matching the pattern of
AWS IoT, Azure IoT Central, and Grafana. Replace the flat nav list with 5 logical
groups: Overview, Fleet, Monitoring, Data, and Settings. Add a live open-alert count
badge to the Monitoring group header. Add collapsible expand/collapse per group.

No backend changes. No route changes. Frontend only.

## Execution Order
1. 001-sidebar.md — Restructure AppSidebar with grouped collapsible sections
2. 002-alert-badge.md — Live alert count badge on Monitoring section
3. 003-verify.md — Build check + checklist
