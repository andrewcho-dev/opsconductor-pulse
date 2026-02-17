---
last-verified: 2026-02-17
sources:
  - services/ui_iot/routes/exports.py
  - services/ui_iot/reports/sla_report.py
  - services/ops_worker/workers/report_worker.py
  - services/ops_worker/workers/export_worker.py
phases: [62, 90, 142]
---

# Reporting

> SLA reporting and export workflows (CSV/JSON) with job tracking.

## Overview

Reporting provides:

- SLA summary metrics (online %, MTTR, top alerting devices)
- CSV/JSON exports for devices and alerts
- Export jobs with async processing, status tracking, and cleanup
- Report run history and scheduled generation

## How It Works

- Users request exports via API endpoints.
- Export workers generate files asynchronously and store results for download.
- SLA reports are generated on demand and also scheduled (daily per tenant) via the ops worker.

## Database Schema

Key tables (high-level):

- Export job tables: exports and export results/metadata
- `report_runs` (SLA report history)
- Supporting telemetry and fleet tables

## API Endpoints

See: [Customer Endpoints](../api/customer-endpoints.md).

- Exports: `/api/v1/customer/exports*` and `/api/v1/customer/export/*`
- Reports: `/api/v1/customer/reports/*`

## Frontend

Reporting UI:

- Reports page (SLA summary + export history)
- Export download handling

## Configuration

- Export storage paths/volumes in compose
- Worker scheduling intervals (ops worker)

## See Also

- [Operations: Database](../operations/database.md)
- [Operations: Runbook](../operations/runbook.md)
- [Service: ops-worker](../services/ops-worker.md)

