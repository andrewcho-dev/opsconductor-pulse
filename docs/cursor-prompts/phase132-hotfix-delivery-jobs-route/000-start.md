# Phase 132 -- Hotfix: Add /delivery-jobs Backend Route

## Problem

The `DeliveryLogPage` frontend calls two endpoints that don't exist:
- `GET /api/v1/customer/delivery-jobs?status=X&limit=N&offset=N`
- `GET /api/v1/customer/delivery-jobs/{jobId}/attempts`

The old `delivery_jobs` and `delivery_attempts` tables were dropped in migration 071 when the notification pipeline was consolidated. The replacement tables are `notification_jobs` (migration 070) and `notification_log` (migration 070 added `job_id`, `success`, `error_msg` columns).

There is already a `GET /api/v1/customer/notification-jobs` route in `notifications.py:415` that queries `notification_jobs`, but the frontend expects a different path and response shape.

## Fix

Add two routes to `services/ui_iot/routes/exports.py` (which already handles delivery-status) that query the new tables but return responses matching the frontend's expected shape.

## Execution Order

| # | File | Commit message |
|---|------|----------------|
| 1 | `001-add-delivery-jobs-route.md` | `fix: add /delivery-jobs route backed by notification_jobs table` |

Single commit, single task.
