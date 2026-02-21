# Phase 134 -- Tenant Billing, Provisioning & Device Tiers

## Depends On

- Phase 131 (X.509 Certificates completed)
- All Phase 132/133 hotfixes applied

## Goal

Implement the complete customer billing lifecycle: a new customer pays on the marketing site → Stripe processes payment → webhook auto-provisions their tenant, Keycloak user, and subscription → customer logs in and starts assigning devices to tiers within their prepaid slot allocation. Existing subscription worker expiry/grace pipeline is fixed and wired to tenant billing emails. Operators get enriched tenant profiles and device tier management.

## Current State

### What EXISTS:
- `tenants` table: tenant_id, name, status, contact_email, contact_name, metadata, timestamps
- `subscriptions` table: multi-type (MAIN/ADDON/TRIAL/TEMPORARY), parent_subscription_id, device_limit, active_device_count, term dates, grace_end, status, plan_id
- `subscription_audit` table: full audit trail with event_type, actor_type, details
- `subscription_notifications` table: expiry notification scheduling + dedup
- `subscription_worker` service: schedules 90/60/30/14/7/1 day renewal notifications, ACTIVE→GRACE→SUSPENDED transitions, device count reconciliation, alert digest emails
- `services/keycloak_admin.py`: full Keycloak admin client with `create_user()`, `assign_realm_role()`, `send_password_reset_email()`, `add_user_to_organization()`
- Operator CRUD for tenants + subscriptions (`routes/operator.py`)
- Operator `create_subscription()` already co-terminates ADDON term_end to parent's term_end
- Three email sending paths: `email_sender.py`, `notifications/senders.py`, `subscription_worker/worker.py`

### What's BROKEN:
- `subscription_worker` SMTP env vars missing from docker-compose → expiry emails silently skipped
- Expiry emails sent to global `NOTIFICATION_EMAIL_TO` env var instead of tenant's billing/contact email
- No Stripe integration anywhere
- No auto-provisioning (tenants created manually by operators)

### What's MISSING:
- Stripe Checkout/Portal/Webhook integration
- Automatic tenant + Keycloak user creation on first payment
- Welcome email flow
- Customer-facing add-on purchase with co-termination proration
- Tenant profile enrichment (company address, industry, data residency, support tier)
- Device tiers (Basic/Standard/Premium device classes with slot allocations)
- Customer self-serve org settings page
- Entitlement enforcement on device creation / tier assignment
- Customer billing/subscription management UI

## Architecture

### End-to-End Customer Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                      MARKETING SITE (external)                  │
│                                                                 │
│  Customer selects plan → enters company info → enters admin     │
│  email → Stripe Checkout Session created with metadata:         │
│    - company_name, legal_name, industry, company_size           │
│    - address fields (or use Stripe's built-in billing address)  │
│    - admin_email (who gets the first login)                     │
│    - plan_id: "starter" | "pro" | "enterprise"                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Stripe processes payment
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                STRIPE → WEBHOOK → YOUR PLATFORM                 │
│                                                                 │
│  POST /webhook/stripe                                           │
│  Event: checkout.session.completed                              │
│    1. Extract customer + company metadata                       │
│    2. CREATE tenant record (with company profile)               │
│    3. CREATE subscription record (plan_id, device slots)        │
│    4. SYNC tier allocations from plan_tier_defaults              │
│    5. CREATE Keycloak user (admin_email, tenant_id attribute)   │
│    6. SEND welcome email (via Keycloak's send-actions-email)    │
│    7. AUDIT LOG: TENANT_PROVISIONED                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CUSTOMER FIRST LOGIN                        │
│                                                                 │
│  Customer receives welcome email → sets password → logs in      │
│  → Sees pre-configured tenant with:                             │
│    - Company profile populated from checkout metadata           │
│    - Subscription active with tier slot allocations              │
│    - Ready to register devices and assign to tiers              │
└─────────────────────────────────────────────────────────────────┘
```

### Mid-Term Add-On (Co-termination)

```
Customer has: Sub A (Pro, Jan 1 – Dec 31, 200 Basic + 50 Standard + 10 Premium)
Customer wants: +50 Standard slots

  → POST /api/v1/customer/billing/addon-checkout
    {
      "parent_subscription_id": "SUB-2025-0001",
      "additions": [{"tier_id": 2, "additional_slots": 50}],
    }
  → System calculates proration:
    - Remaining days: 184 (Jun 1 – Dec 31)
    - Prorated price: (184/365) × annual_addon_price
  → Creates Stripe Checkout Session with:
    - cancel_at = parent's term_end (Dec 31)
    - metadata: parent_subscription_id, additions
  → Webhook: checkout.session.completed
    - Creates ADDON subscription (parent_subscription_id = Sub A, term_end = Dec 31)
    - Adds 50 Standard slots to subscription_tier_allocations
```

### Renewal & Expiry Flow

```
Subscription Worker (runs hourly):

  Day -90: Schedule RENEWAL_90 notification
  Day -60: Schedule RENEWAL_60 notification
  Day -30: Schedule RENEWAL_30 notification
  Day -14: Schedule RENEWAL_14 notification
  Day -7:  Schedule RENEWAL_7 notification
  Day -1:  Schedule RENEWAL_1 notification

  Process pending notifications → send to tenant's billing_email

  Day 0 (term_end):
    - Auto-renew ON (Stripe-managed): Stripe charges card, webhook renews sub
      - Co-terminated add-ons also renew at full price for the new term
    - Auto-renew OFF: subscription → GRACE, grace_end = term_end + 14 days

  Day +14 (grace_end):
    - GRACE → SUSPENDED
    - Devices lose entitlements
```

### Stripe Webhook Events Handled

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Auto-provision tenant + subscription + Keycloak user (if new), or add subscription (if existing tenant) |
| `customer.subscription.updated` | Sync status + plan changes to subscriptions table |
| `customer.subscription.deleted` | Set subscription to EXPIRED |
| `invoice.payment_failed` | Set subscription to GRACE |
| `invoice.paid` | Confirm renewal, extend term_end |

### Marketing Site Metadata Contract

The marketing site must include these in the Stripe Checkout Session metadata:

```json
{
  "plan_id": "pro",
  "company_name": "Acme IoT Corp",
  "legal_name": "Acme IoT Corporation",
  "admin_email": "jane@acme-iot.com",
  "admin_first_name": "Jane",
  "admin_last_name": "Doe",
  "industry": "Manufacturing",
  "company_size": "51-200",
  "phone": "+1-555-0100"
}
```

Billing address comes from Stripe's built-in `customer_details.address` (line1, line2, city, state, postal_code, country). Customer email from `customer_details.email`.

## Execution Order

| # | File | Commit Scope |
|---|------|-------------|
| 1 | `001-billing-migrations.md` | DB migrations: enrich tenants, create device_tiers + subscription tier allocations, tenant self-read RLS |
| 2 | `002-stripe-service-and-billing-api.md` | Backend: stripe_service.py, billing router (config/checkout/portal/status), env vars |
| 3 | `003-webhook-auto-provisioning.md` | Backend: webhook handler, auto-create tenant + Keycloak user + welcome email on checkout |
| 4 | `004-addon-co-termination.md` | Backend: customer add-on checkout with co-termination proration |
| 5 | `005-subscription-worker-fixes.md` | Fix: wire SMTP env vars, send expiry emails to tenant billing_email, auto-renewal via Stripe |
| 6 | `006-tenant-profile-api.md` | Backend: customer org GET/PUT, operator enriched tenant CRUD |
| 7 | `007-device-tier-api.md` | Backend: operator device tier CRUD, customer tier read + assignment with slot tracking |
| 8 | `008-entitlement-enforcement.md` | Backend: plan limit checks on device/rule creation + tier assignment |
| 9 | `009-frontend-customer.md` | Frontend: org settings page, billing page, device tier assignment |
| 10 | `010-frontend-operator-and-seed.md` | Frontend: enriched tenant detail, device tier management, updated seed data |
| 11 | `011-operator-manual-controls.md` | Backend: operator plan CRUD, tier allocation CRUD, plan→tier sync, slot reconciliation, bypass assignment, resend welcome email |

Tasks 1-5 are the billing/provisioning core. Tasks 6-8 are the profile/tier API layer. Tasks 9-10 are frontend. Task 11 ensures full operator parity with every automated Stripe flow (for offline-payment customers).

**Important**: Plan names, limits, pricing, and device allocations are all database-driven via the `subscription_plans` and `plan_tier_defaults` tables. No plan definitions are hardcoded in Python code. All plan lookups query the database at runtime.

## Key Files Modified

### Backend
- `db/migrations/096_tenant_profile.sql` — enrich tenants table
- `db/migrations/097_device_tiers.sql` — device tiers + subscription tier allocations
- `services/ui_iot/services/stripe_service.py` — NEW: Stripe API wrapper
- `services/ui_iot/routes/billing.py` — NEW: customer billing + webhook endpoints
- `services/ui_iot/routes/organization.py` — NEW: customer org settings
- `services/ui_iot/routes/operator.py` — enriched tenant CRUD + device tier CRUD
- `services/ui_iot/routes/devices.py` — device tier assignment
- `services/ui_iot/middleware/entitlements.py` — NEW: plan limit enforcement
- `services/ui_iot/app.py` — register new routers
- `services/ui_iot/requirements.txt` — add `stripe`
- `services/subscription_worker/worker.py` — fix email targeting
- `compose/docker-compose.yml` — add Stripe + SMTP env vars
- `scripts/seed_demo_data.py` — enriched tenants, tier allocations

### Frontend
- `frontend/src/services/api/organization.ts` — NEW: org API client
- `frontend/src/services/api/billing.ts` — NEW: billing API client
- `frontend/src/features/settings/OrganizationPage.tsx` — NEW: customer org settings
- `frontend/src/features/settings/BillingPage.tsx` — NEW: customer billing page
- `frontend/src/features/operator/OperatorTenantDetailPage.tsx` — enriched detail
- `frontend/src/features/operator/EditTenantDialog.tsx` — more fields
- `frontend/src/features/operator/DeviceTiersPage.tsx` — NEW: tier management
- `frontend/src/features/devices/DeviceDetailPage.tsx` — tier assignment
- `frontend/src/services/api/tenants.ts` — extended interfaces
- `frontend/src/app/router.tsx` — new routes
- `frontend/src/components/layout/AppSidebar.tsx` — new nav items

## Environment Variables (New)

```
# Stripe (on ui service)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# SMTP (on subscription-worker — CURRENTLY MISSING)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@pulse.example.com
SMTP_PASSWORD=...
SMTP_FROM=noreply@pulse.example.com
SMTP_TLS=true
```

## Migration Numbering

Highest existing migration: `095_device_certificates.sql`

- `096_tenant_profile.sql`
- `097_device_tiers.sql`

## Database Roles & RLS

New RLS policies needed on `tenants` table for customer self-read/update:
```sql
CREATE POLICY tenants_self_read ON tenants
    FOR SELECT TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true));

CREATE POLICY tenants_self_update ON tenants
    FOR UPDATE TO pulse_app
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
```

`device_tiers` is platform-wide (no RLS, operator-only writes, pulse_app can SELECT).
`subscription_tier_allocations` uses operator-only direct access; customer reads through billing endpoints.
