# Phase 96 — Extract metrics domain to routes/metrics.py

## File to create
`services/ui_iot/routes/metrics.py`

## Endpoints to move from customer.py

### Metric catalog
- `list_metric_catalog()` — GET /metrics/catalog (line ~2618)
- `create_metric_catalog_entry()` — POST /metrics/catalog (line ~2641)
- `delete_metric_catalog_entry()` — DELETE /metrics/catalog/{metric_name} (line ~2683)

### Normalized metrics
- `list_normalized_metrics()` — GET /normalized-metrics (line ~2707)
- `delete_normalized_metric()` — DELETE /normalized-metrics/{name} (line ~2815)

### Metric mappings
- `list_metric_mappings()` — GET /metric-mappings (line ~2840)
- `create_metric_mapping()` — POST /metric-mappings (line ~2875)
- `update_metric_mapping()` — PATCH /metric-mappings/{raw_metric} (line ~2926)
- `delete_metric_mapping()` — DELETE /metric-mappings/{raw_metric} (line ~2961)

## Structure of metrics.py

```python
"""Metric catalog, normalized metrics, and metric mapping routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
# ... copy all imports needed by the moved functions

from dependencies import get_db_pool, require_customer, require_customer_admin

router = APIRouter(prefix="/customer", tags=["metrics"])

# ── paste all metric functions here ──────────────────────────────────────────
```

## After creating metrics.py

1. **Delete** all moved functions from `customer.py`
2. **Remove** any imports in `customer.py` that are now only used by metrics.py
3. Do NOT register in app.py yet — that happens in `005-register-routers.md`
