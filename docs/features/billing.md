---
last-verified: 2026-02-20
sources:
  - services/ui_iot/routes/billing.py
  - services/subscription_worker/worker.py
phases: [31, 32, 33, 69, 116, 134, 142, 205, 209, 212]
---

# Billing

> Subscriptions, entitlements, device limits, and renewal lifecycle.

## Overview

Billing governs tenant entitlements and subscription lifecycle:

- Subscription types: MAIN, ADDON, TRIAL, TEMPORARY
- Status transitions: TRIAL → ACTIVE → GRACE → SUSPENDED → EXPIRED
- Device limit enforcement at provisioning and assignment time
- Renewal notifications and audit history

## How It Works

### Subscription lifecycle

The subscription worker:

- Sends renewal notifications ahead of `term_end`.
- Moves subscriptions to GRACE when `term_end` passes.
- Moves subscriptions to SUSPENDED after a grace window (default 14 days).

### Entitlements and UI

Customer billing endpoints expose:

- Configuration and entitlements
- Current billing/subscription status
- Checkout and portal session creation (when Stripe is enabled)

## Database Schema

Key tables (high-level):

- `subscriptions` (status + term windows)
- Tier allocation and usage tables (device tier slots, assignments)
- Subscription audit history tables

## API Endpoints

See: [Customer Endpoints](../api/customer-endpoints.md).

- `/api/v1/customer/billing/*`
- `/api/v1/customer/subscriptions*`

## Frontend

Billing UI is implemented under settings/subscription feature pages.

## Configuration

Common knobs:

- Stripe configuration (billing routes)
- Worker tick interval and SMTP settings for renewal emails

## Webhook Security Model

Billing webhook processing uses a strict model:

- Stripe signatures are verified on raw request payload bytes.
- Duplicate event delivery is ignored through `stripe_events` idempotency tracking, enforced atomically via `INSERT ... ON CONFLICT DO NOTHING RETURNING event_id` (no separate SELECT, no race window).
- Only known billing webhook event types are processed.
- State-changing updates use authoritative Stripe subscription fetches where required.
- Event logging avoids sensitive payment/card details.

## See Also

- [Service: subscription-worker](../services/subscription-worker.md)
- [Deployment](../operations/deployment.md)
- [Customer Endpoints](../api/customer-endpoints.md)

