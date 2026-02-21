---
phase: 212
title: Announcement Banner System — Stripe-style Dismissible Alerts
goal: Operator-controlled full-width banner at the top of the app for urgent notices, dismissible per user
---

# Phase 212 — Announcement Banner System

## Visual Target

Stripe sandbox banner style:
- Full-width banner at the very top of the viewport (above the header)
- Styled by severity: info (blue), warning (amber), critical (red)
- Dismissible — user clicks X, banner disappears, does not return for that announcement ID
- Dismissed state stored in localStorage keyed by announcement ID
- Only one banner shown at a time (highest priority / most recent active)
- Operator creates/manages banners from the operator console

## Data model

Announcement banner is distinct from the News broadcasts in Phase 211.
Announcements are urgent top-of-screen notices. Broadcasts are news items on the home page.

Reuse the same `broadcasts` table from Phase 211, but filter differently:
- Home page news: type IN ('info', 'warning', 'update'), active=true
- Announcement banner: a separate `is_banner` boolean column added to broadcasts table

Add a new migration to add `is_banner BOOLEAN NOT NULL DEFAULT false` to broadcasts.

## Execution Order
- 001-backend-banner-api.md
- 002-banner-component.md
- 003-operator-banner-management.md
- 004-update-docs.md
