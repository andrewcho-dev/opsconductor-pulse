# Phase 69: Subscription Expiry Notifications (Email)

## What Exists

- `subscriptions` table: `subscription_id`, `tenant_id`, `term_end TIMESTAMPTZ`, `status`, `grace_end`
- `subscription_notifications` table: `id`, `tenant_id`, `notification_type`, `scheduled_at`, `sent_at`, `channel`, `status`, `error`
- `services/subscription_worker/worker.py`:
  - `schedule_renewal_notifications()` — creates notification records at 90/60/30/14/7/1 days before term_end
  - `process_pending_notifications()` — currently sends via webhook or logs only (no email)
  - `process_grace_transitions()` — manages ACTIVE→GRACE→SUSPENDED status transitions
- `services/delivery_worker/email_sender.py` — full email sending via aiosmtplib
- No email delivery in subscription_worker

## What This Phase Adds

1. **Email delivery in subscription_worker** — when processing pending notifications, if the tenant has an active email integration, send via that integration. Otherwise use a direct SMTP send if `SMTP_*` env vars are configured.
2. **Email template** for expiry notifications: plain + HTML versions
3. **Operator endpoint**: GET /operator/subscriptions/expiring-notifications — list pending/sent notification records
4. **Frontend**: Operator notification status panel

## Architecture Decision

Rather than coupling subscription_worker to the delivery_worker pipeline (which requires creating delivery_jobs, routes, etc.), this phase implements **direct SMTP send** from subscription_worker using a simplified email function. The existing `SMTP_*` env vars from delivery_worker are reused.

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Email templates for expiry notifications |
| 002 | subscription_worker: direct SMTP send |
| 003 | Backend: GET /operator/subscriptions/expiring-notifications |
| 004 | Frontend: notification status panel |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/subscription_worker/worker.py` — prompts 001, 002
- `services/subscription_worker/requirements.txt` — prompt 002
- `services/ui_iot/routes/operator.py` — prompt 003
- `frontend/src/features/operator/` — prompt 004
