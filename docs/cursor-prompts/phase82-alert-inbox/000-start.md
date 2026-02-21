# Phase 82 — Alert Inbox Redesign

## Overview
Redesign AlertListPage to work like an email inbox (inspired by PagerDuty and Datadog
alert management). Key improvements: severity-filtered tabs at top, bulk ack/close
actions, inline detail expansion (no navigation away), keyboard-friendly layout.
The alert list is the primary daily work surface for operators — it needs to feel
like a professional triage tool, not a data table.

No backend changes needed.

## Execution Order
1. 001-inbox-layout.md — Full AlertListPage inbox redesign
2. 002-inline-detail.md — Inline expandable alert detail row
3. 003-verify.md — Build check + checklist
