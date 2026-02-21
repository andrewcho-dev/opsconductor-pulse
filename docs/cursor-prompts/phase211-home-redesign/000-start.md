---
phase: 211
title: Home Page Redesign — EMQX-inspired Layout
goal: Redesign the home page with a two-column layout featuring fleet summary, documentation links, and operator-broadcast news
---

# Phase 211 — Home Page Redesign

## Visual Target

EMQX Cloud Console home page style:
- Left/main column: fleet health summary (compact KPIs) + quick actions
- Right column: Documentation section + News/Broadcasts section
- Clean card-based layout with clear visual hierarchy
- No clutter — remove onboarding checklist from default view (keep only if user has 0 devices)

## Backend requirement
News/Broadcasts are operator-published announcements fetched from:
`GET /api/v1/customer/broadcasts` → returns list of active broadcast items

A broadcast item has: `id`, `title`, `body`, `created_at`, `type` (info/warning/update)

## Execution Order
- 001-backend-broadcasts-api.md
- 002-home-page-component.md
- 003-update-docs.md
