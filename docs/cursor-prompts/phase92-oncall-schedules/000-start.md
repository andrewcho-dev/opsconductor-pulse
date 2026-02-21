# Phase 92 — On-Call Schedules

## Goal
Allow tenants to define on-call rotation schedules (weekly layers, named
responders) and link schedules to escalation policy levels so notifications
go to whoever is currently on-call.

## Execution Order
1. 001-migration.md       — DB migration for oncall_schedules + oncall_layers + oncall_overrides
2. 002-backend.md         — Backend CRUD + current on-call resolver
3. 003-frontend.md        — Schedules page with calendar view + override modal
4. 004-verify.md          — Build, test, commit, push
