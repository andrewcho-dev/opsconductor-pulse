# Commit and Push — Phases 75–78

## Step 1: Stage all changes
```bash
git add -A
```

## Step 2: Commit
```bash
git commit -m "Add phases 75–78: device API tokens, bulk CSV import, alert digest emails, uptime tracking

- Phase 75: migration 064 (device_api_tokens), GET/DELETE/POST rotate endpoints, DeviceApiTokensPanel, passlib bcrypt, 5 unit tests
- Phase 76: POST /devices/import (CSV, 500-row/1MB limits, per-row results), BulkImportPage, /devices/import route, 5 unit tests
- Phase 77: migration 065 (alert_digest_settings), GET/PUT digest settings, send_alert_digest() in subscription_worker, DigestSettingsCard, 5 unit tests
- Phase 78: GET /devices/{id}/uptime + /fleet/uptime-summary, UptimeBar/DeviceUptimePanel/UptimeSummaryWidget, 6 unit tests

702 unit tests passing, frontend build clean."
```

## Step 3: Push
```bash
git push origin main
```

## Step 4: Confirm
```bash
git log --oneline -5
```

Report the output of the final `git log` command.
