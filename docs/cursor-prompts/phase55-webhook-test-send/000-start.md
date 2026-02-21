# Phase 55: Webhook Delivery — Test Send + Delivery Log UI

## What Exists

- Full webhook delivery pipeline already exists:
  - `integrations` table with type='webhook', config_json (url, headers), enabled flag
  - `integration_routes` table for alert→integration matching
  - `delivery_jobs` table (PENDING/PROCESSING/COMPLETED/FAILED, attempts, last_error)
  - `delivery_attempts` table (per-attempt latency, http_status, ok/fail)
  - `services/delivery_worker/worker.py` sends webhooks with retry + backoff
  - `services/dispatcher/dispatcher.py` creates delivery_jobs from alerts
- Webhook integrations can be created via API but UI experience is basic

## What This Phase Adds

1. **Backend: POST /customer/integrations/{id}/test-send** — sends a synthetic test payload to the webhook URL immediately (bypasses dispatcher/queue), returns HTTP status + latency
2. **Backend: GET /customer/delivery-jobs** — paginated delivery job history with status/attempts/errors
3. **Frontend: "Send Test" button** on webhook integration detail page
4. **Frontend: Delivery Log page** — table of recent delivery jobs with status, attempts, last_error, expandable detail

## What NOT to Change

- The dispatcher / delivery_worker pipeline — do not modify
- delivery_jobs or delivery_attempts schema — no migration needed
- Existing integration CRUD — only add the test-send endpoint

## Execution Order

| Prompt | Description |
|--------|-------------|
| 001 | Backend: POST /customer/integrations/{id}/test-send |
| 002 | Backend: GET /customer/delivery-jobs |
| 003 | Frontend: Send Test button |
| 004 | Frontend: Delivery Log page |
| 005 | Unit tests |
| 006 | Verify |

## Key Files

- `services/ui_iot/routes/customer.py` — prompts 001, 002
- `services/delivery_worker/worker.py` — read for SSRF blocklist pattern (reuse in test-send)
- `frontend/src/features/integrations/` — prompt 003
- `frontend/src/features/delivery/` — new, prompt 004
