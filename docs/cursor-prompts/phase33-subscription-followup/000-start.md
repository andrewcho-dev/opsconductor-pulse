# Phase 33: Subscription System Follow-up

## Overview

Follow-up tasks to complete the subscription system after Phase 32 multi-subscription implementation.

## Prerequisites

- Phase 32 complete (multi-subscription schema, APIs, UI)
- All E2E tests passing
- Data migration completed

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | 001-subscription-detail-page.md | Operator subscription detail page |
| 2 | 002-notification-worker.md | Expiry notification scheduled job |
| 3 | 003-renewal-workflow.md | Renewal UI and backend |
| 4 | 004-deprecation-cleanup.md | Remove legacy tenant_subscription |

## Notes

- Tasks 1-3 can be done in any order
- Task 4 (deprecation cleanup) should be done LAST after confirming everything works
- Notification worker requires a scheduler (cron or pg_cron)
