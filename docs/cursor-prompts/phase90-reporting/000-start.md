# Phase 90 — Reporting

## Goal
Add scheduled and on-demand reports: per-tenant SLA summary, CSV/JSON export
for devices and alerts, and a report history page.

## Execution Order
1. 001-migration.md          — DB migration for report_runs table
2. 002-backend-exports.md    — CSV/JSON export endpoints
3. 003-backend-scheduled.md  — SLA report function + scheduled worker
4. 004-frontend.md           — Reports page (exports + SLA card + history)
5. 005-verify.md             — Build, commit, push
