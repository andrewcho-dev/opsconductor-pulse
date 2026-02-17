---
last-verified: 2026-02-17
sources:
  - services/subscription_worker/worker.py
phases: [31, 32, 33, 69, 116, 142]
---

# subscription-worker

> Subscription lifecycle and renewal notification worker.

## Overview

`subscription_worker` is a scheduled job that manages subscription lifecycle:

- Sends renewal notifications at 90/60/30/14/7/1 days before expiry.
- Transitions subscription states:
  - ACTIVE → GRACE (after `term_end`)
  - GRACE → SUSPENDED (after `grace_end`)
- Reconciles device counts on a periodic schedule.

## Architecture

Runs a loop on `WORKER_INTERVAL_SECONDS`:

1. Acquire DB pool from `DATABASE_URL`.
2. Execute lifecycle tasks (notifications, transitions, reconciliation).
3. Sleeps until next tick.

Email delivery uses SMTP settings when configured.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | empty | DSN for PostgreSQL connection pool. |
| `NOTIFICATION_WEBHOOK_URL` | empty | Optional webhook to notify external systems. |
| `SMTP_HOST` | empty | SMTP host for email delivery (if set, enables SMTP notifications). |
| `SMTP_PORT` | `587` | SMTP port. |
| `SMTP_USER` | empty | SMTP username. |
| `SMTP_PASSWORD` | empty | SMTP password. |
| `SMTP_TLS` | `true` | Enable STARTTLS/TLS behavior. |
| `SMTP_FROM` | `noreply@pulse.local` | From address for outbound email. |
| `WORKER_INTERVAL_SECONDS` | `3600` | Main worker tick interval. |

## Health & Metrics

No HTTP server; runs as a background worker process.

## Dependencies

- PostgreSQL (subscription tables and audit)
- SMTP server (optional, for email notifications)

## Troubleshooting

- Emails not sending: verify `SMTP_HOST` and credentials; check logs for SMTP errors.
- Transitions not occurring: verify worker is running and `DATABASE_URL` connectivity is healthy.

## See Also

- [Billing](../features/billing.md)
- [Deployment](../operations/deployment.md)
- [Database](../operations/database.md)

