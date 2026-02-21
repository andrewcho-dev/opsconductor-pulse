# Phase 32: Multi-Subscription Architecture

## Overview

Refactor the subscription system so that:
- Each tenant can have multiple subscriptions (MAIN, ADDON, TRIAL, TEMPORARY)
- Each device is linked to exactly one subscription
- Subscriptions expire independently (only affecting their linked devices)
- Addon subscriptions are coterminous with their parent MAIN subscription

## Execution Order

| # | File | Description |
|---|------|-------------|
| 1 | `001-database-migration.md` | Create subscriptions table, add subscription_id to devices |
| 2 | `002-subscription-service.md` | Update service for multi-subscription logic |
| 3 | `003-ingest-guards.md` | Check device's subscription, not tenant's |
| 4 | `004-customer-api.md` | List subscriptions, view device assignments |
| 5 | `005-operator-api.md` | Create/manage subscriptions, assign devices |
| 6 | `006-frontend-operator-subscriptions.md` | Operator UI for managing multiple subscriptions |
| 7 | `007-frontend-device-assignment.md` | UI to assign devices to subscriptions |
| 8 | `008-frontend-customer-view.md` | Customer view of their subscriptions |
| 9 | `009-data-migration.md` | Migrate existing data to new schema |

## Schema Overview

### subscriptions table

```
subscription_id (PK)  - e.g., "SUB-2024-00001"
tenant_id (FK)        - owner tenant
subscription_type     - MAIN, ADDON, TRIAL, TEMPORARY
parent_subscription_id - for ADDON (links to MAIN)
device_limit          - max devices on this subscription
active_device_count   - denormalized count
term_start            - subscription start date
term_end              - subscription end date
status                - TRIAL, ACTIVE, GRACE, SUSPENDED, EXPIRED
plan_id               - optional plan reference
```

### device_registry modification

```
subscription_id (FK)  - which subscription this device belongs to
```

## Subscription Types

| Type | Description | Term |
|------|-------------|------|
| MAIN | Primary annual subscription | Independent |
| ADDON | Additional capacity | Coterminous with parent MAIN |
| TRIAL | Evaluation period | Short-term (14-30 days) |
| TEMPORARY | Project/event based | Custom term |

## Business Rules

1. Every device MUST have a subscription_id
2. One device = one active subscription at a time
3. ADDON.term_end is always synced with parent MAIN.term_end
4. When subscription expires, only its devices are affected
5. Devices can be moved between subscriptions (with audit)
6. Subscription IDs are globally unique, tenant-scoped display

## Verification

After completing all prompts:

```bash
# Create MAIN subscription
POST /operator/subscriptions
{"tenant_id": "tenant-a", "type": "MAIN", "device_limit": 50, "term_days": 365}

# Create ADDON subscription (coterminous)
POST /operator/subscriptions
{"tenant_id": "tenant-a", "type": "ADDON", "parent_id": "SUB-xxx", "device_limit": 10}

# Assign device to subscription
POST /operator/devices/{device_id}/subscription
{"subscription_id": "SUB-xxx"}

# Expire one subscription, verify only its devices affected
```
