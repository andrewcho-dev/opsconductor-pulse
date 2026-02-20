-- Migration 116: Backward-compat views for deprecated metric tables
-- Phase 173 migration 115 renamed these tables but forgot compatibility views.
-- The metrics/reference endpoint and other code still query by old names.

BEGIN;

-- ============================================================
-- normalized_metrics: view over the renamed table
-- ============================================================

CREATE OR REPLACE VIEW normalized_metrics AS
SELECT
    id,
    tenant_id,
    normalized_name,
    display_unit,
    description,
    expected_min,
    expected_max,
    created_at,
    updated_at
FROM _deprecated_normalized_metrics;

GRANT SELECT ON normalized_metrics TO pulse_app;

-- ============================================================
-- metric_mappings: view over the renamed table
-- ============================================================

CREATE OR REPLACE VIEW metric_mappings AS
SELECT
    id,
    tenant_id,
    raw_metric,
    normalized_name,
    multiplier,
    offset_value,
    created_at
FROM _deprecated_metric_mappings;

GRANT SELECT ON metric_mappings TO pulse_app;

COMMIT;
