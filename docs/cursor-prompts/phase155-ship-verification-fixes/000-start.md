# Phase 155 — Ship Verification Fixes

## Overview

Fixes discovered during ship verification of Phases 150–154 (sensor management + carrier integration) and Phase 156 (subscription package architecture).

## Execution Order

1. `001-sensor-list-select-fix.md` — Fix SensorListPage crash from empty SelectItem values ✅
2. `002-carrier-permissions-seed.md` — ~~Superseded by Phase 156 migration 107~~
3. `003-fix-legacy-subscriptions-route.md` — Fix 500 on /customer/subscriptions (queries dropped table) ✅
4. `004-fix-basename-double-prefix.md` — Fix /app/app/ double prefix in navigation links ✅
5. `005-operator-frontend-new-model.md` — Rewrite operator subscription/tier UI for Phase 156 model (3 parts)
