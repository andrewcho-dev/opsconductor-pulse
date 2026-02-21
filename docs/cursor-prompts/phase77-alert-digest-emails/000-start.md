# Phase 77 — Alert Digest Emails

## Overview
Send a scheduled email digest to tenant users summarizing open and recent alerts. The digest runs as a daily job inside `subscription_worker`. Tenant operators can configure digest frequency (daily/weekly/disabled) via a settings endpoint.

## Execution Order
1. 001-migration.md — migration 064 (or 065 if 064 taken): alert_digest_settings table
2. 002-backend.md — digest settings endpoint + digest_job logic
3. 003-frontend.md — DigestSettingsCard in notification preferences
4. 004-unit-tests.md — 5 unit tests
5. 005-verify.md — checklist

Note: Check highest migration number in `db/migrations/` before naming the new migration file.
