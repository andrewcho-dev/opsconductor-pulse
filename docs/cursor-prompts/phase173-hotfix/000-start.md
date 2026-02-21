# Phase 173 Hotfix: Restore Compatibility Views for Deprecated Metric Tables

## Problem

Migration 115 (`115_deprecate_legacy_tables.sql`) renamed `normalized_metrics` → `_deprecated_normalized_metrics` and `metric_mappings` → `_deprecated_metric_mappings`, but did NOT create backward-compatibility views for them.

This breaks `GET /api/v1/customer/metrics/reference` which still queries both tables by their old names → unhandled 500.

Migration 115 created compatibility views for `sensors` and `device_connections` but missed `normalized_metrics` and `metric_mappings`.

## Fix

Create migration `116_metric_compat_views.sql` that adds backward-compatibility views for the two renamed tables, matching the pattern used for `sensors` and `device_connections` in migration 115.

Also add a `try/except` to `get_metrics_reference` so any future breakage returns a clean error instead of an unhandled 500.

## Execution

1. `001-compat-views.md` — Create migration + fix endpoint error handling
