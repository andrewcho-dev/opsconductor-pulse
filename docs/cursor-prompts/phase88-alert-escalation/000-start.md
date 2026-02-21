# Phase 88 — Alert Escalation Policies

## Goal
Allow tenants to define escalation policies: if an alert is not acknowledged
within N minutes it escalates to the next level (up to 5 levels), optionally
triggering a webhook or email at each level.

## Execution Order
1. 001-migration.md       — DB migration for escalation_policies + escalation_levels tables
2. 002-backend.md         — Backend CRUD endpoints + escalation worker
3. 003-frontend.md        — Escalation Policy management UI
4. 004-verify.md          — Build, test, commit, push
