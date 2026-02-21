# Phase 31: Subscription & Entitlement System

## Overview

Implement a subscription-based device licensing system with:
- Device limit enforcement (hard block on create if over limit)
- Subscription lifecycle states (TRIAL → ACTIVE → GRACE → SUSPENDED → EXPIRED)
- Auto-provision checks at ingest layer
- 14-day grace period after expiration
- Renewal notifications at 90, 60, 30, 14, 7, 1 days before expiry
- Dedicated subscription audit log

## Execution Order

Execute these prompts in order:

| # | File | Description |
|---|------|-------------|
| 1 | `001-database-migration.md` | Create tenant_subscription, subscription_audit, subscription_notifications tables |
| 2 | `002-subscription-service.md` | Backend service layer for subscription logic |
| 3 | `003-device-crud-limits.md` | Add limit checks to device creation |
| 4 | `004-ingest-guards.md` | Add subscription checks to ingest service |
| 5 | `005-notification-worker.md` | Background worker for state transitions and notifications |
| 6 | `006-customer-api.md` | Customer-facing subscription endpoints |
| 7 | `007-operator-api.md` | Operator subscription management endpoints |
| 8 | `008-frontend-banner.md` | Subscription status banner component |
| 9 | `009-frontend-subscription-page.md` | Customer subscription page |
| 10 | `010-device-selection-modal.md` | Device selection for downgrade |
| 11 | `011-device-list-limit-display.md` | Device list page limit display |
| 12 | `012-renew-button-mailto.md` | Temporary mailto for Renew Now buttons |
| 13 | `013-operator-subscription-card.md` | Operator UI subscription card on tenant detail |
| 14 | `014-operator-subscription-dialog.md` | Operator edit subscription dialog |
| 15 | `015-backend-audit-notes.md` | Backend support for notes/transaction refs |
| 16 | `016-e2e-verification.md` | Playwright E2E tests for subscription UI |

## Business Rules

| Policy | Decision |
|--------|----------|
| Subscription term | Annual, paid in advance |
| Device limit enforcement | Hard block on create if over limit |
| Auto-provision from telemetry | Allowed, but checks device limit |
| Lapsed subscription - ingest | Continue for grace period only |
| Grace period | 14 days |
| Data retention after deactivation | 1 year |
| Renewal notifications | 90, 60, 30, 14, 7, 1 days before expiry |

## Subscription Lifecycle States

```
TRIAL → ACTIVE → (renewal) → ACTIVE
                     ↓ (no payment)
                   GRACE (14 days)
                     ↓ (still no payment)
                   SUSPENDED (UI blocked, ingest blocked)
                     ↓ (90 days no payment)
                   EXPIRED (data retained 1 year, then purged)
```

## Verification

After completing all prompts:

```bash
# Run migration
docker compose exec postgres psql -U iot -d iotcloud \
  -f /docker-entrypoint-initdb.d/029_subscription_entitlements.sql

# Test device limit
# 1. Create subscription with device_limit=5
# 2. Create 5 devices → success
# 3. Create 6th device → 403 "Device limit reached"

# Test grace period
# Update term_end to past → run worker → status changes to GRACE

# Test suspended ingest
# Set status=SUSPENDED → send telemetry → rejected
```
