# Phase 96 — Extract exports domain to routes/exports.py

## File to create
`services/ui_iot/routes/exports.py`

## Endpoints to move from customer.py

### Data exports
- `export_devices()` — GET /export/devices (line ~4971)
- `export_alerts()` — GET /export/alerts (line ~5045)

### Reports
- `sla_summary_report()` — GET /reports/sla-summary (line ~5119)
- `list_report_runs()` — GET /reports/runs (line ~5140)

### Audit log
- `audit_log()` — GET /audit-log (line ~4885)

### Delivery status (consider moving here or keeping in customer.py)
- `delivery_status()` — GET /delivery-status (line ~4868)

> Note: `delivery_status` is about delivery job status — it could reasonably stay in
> customer.py with subscriptions/delivery-jobs, or move here. Move it here since it's
> operational/reporting in nature.

## Structure of exports.py

```python
"""Data export, reports, audit log, and delivery status routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import csv
import io
# ... copy all imports needed by the moved functions

from dependencies import get_db_pool, require_customer, require_customer_admin

router = APIRouter(prefix="/customer", tags=["exports"])

# ── paste all export/report functions here ───────────────────────────────────
```

## After creating exports.py

1. **Delete** all moved functions from `customer.py`
2. **Remove** any imports in `customer.py` that are now only used by exports.py (e.g., `csv`, `io`, `StreamingResponse`)
3. Do NOT register in app.py yet — that happens in `005-register-routers.md`

## What remains in customer.py after all 4 extractions

After phases 001–004, customer.py should contain only:
- Sites: `list_sites()`, `site_summary()`
- Subscriptions: `list_subscriptions()`, `get_subscription()`, `subscription_audit_log()`, `renew_subscription()`
- Geocode: `geocode_address()`
- Delivery jobs: `list_delivery_jobs()`, `get_delivery_job_attempts()`
- Integrations: all the old integration CRUD (to be fully removed after phase 95)

Target size: ~1,000 lines (down from 5,154).
