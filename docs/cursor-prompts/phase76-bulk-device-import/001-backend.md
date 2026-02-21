# Prompt 001 — Backend: Bulk Device CSV Import

Read `services/ui_iot/routes/customer.py` fully.

## Add endpoint: POST /customer/devices/import

Accepts: `multipart/form-data` with a single `file` field (CSV).

CSV format (first row = header, required columns: `name`, `device_type`; optional: `site_id`, `tags`):
```
name,device_type,site_id,tags
sensor-a,temperature,site-uuid-1,"floor1,zone2"
pump-b,pressure,,
```

Processing:
1. Parse CSV with Python `csv.DictReader` (in-memory, limit 500 rows max — return 400 if exceeded)
2. Validate each row: `name` required, `device_type` must be one of the allowed types
3. For valid rows: INSERT into device_registry (same logic as POST /devices), generate client_id + password using `secrets`, INSERT into device_api_tokens
4. For invalid rows: collect error message, skip insert
5. Return summary:

```json
{
  "total": 10,
  "imported": 8,
  "failed": 2,
  "results": [
    {"row": 1, "name": "sensor-a", "status": "ok", "device_id": "uuid"},
    {"row": 3, "name": "", "status": "error", "message": "name is required"}
  ]
}
```

Use `from fastapi import UploadFile, File`.
Max file size: 1 MB (return 413 if exceeded via `await file.read()` size check).

## Acceptance Criteria
- [ ] POST /customer/devices/import in customer.py
- [ ] Parses CSV, validates rows, returns per-row results
- [ ] 500 row limit enforced
- [ ] 1 MB size limit enforced
