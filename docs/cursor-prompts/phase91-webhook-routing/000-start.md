# Phase 91 — Webhook Routing

## Goal
Allow tenants to configure outbound notification channels (Slack, PagerDuty,
Microsoft Teams, generic HTTP webhook) and route alerts to them based on
severity and/or alert type filters.

## Execution Order
1. 001-migration.md       — DB migration for notification_channels + routing_rules tables
2. 002-backend.md         — Backend CRUD + notification dispatcher
3. 003-frontend.md        — Channels page + routing rules UI
4. 004-verify.md          — Build, test, commit, push
