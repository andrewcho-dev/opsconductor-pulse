# Phase 90 — Verify, Commit, Push

## Step 1: Apply migration
```bash
psql "$DATABASE_URL" -f db/migrations/067_report_runs.sql
```

## Step 2: Rebuild backend
```bash
docker compose build ui_iot && docker compose up -d ui_iot
```

## Step 3: Build frontend
```bash
cd frontend && npm run build 2>&1 | tail -20
```
Must exit 0.

## Step 4: Backend smoke tests

```bash
# SLA summary (expect JSON with online_pct, total_alerts, etc.)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/reports/sla-summary?days=30" | jq .

# Device CSV export (expect CSV header row)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/export/devices?format=csv" | head -3

# Alert CSV export
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/export/alerts?format=csv&days=7" | head -3
```

## Step 5: Frontend smoke check
- Navigate to `/reports` — page renders with 3 sections
- "Export Devices (CSV)" button triggers browser CSV download
- SLA Summary card shows online %, MTTR, etc.
- Report History table populates after exports

## Step 6: Commit and push
```bash
git add -A
git commit -m "feat: phase 90 - reporting (CSV exports, SLA summary, scheduled worker, report history)"
git push origin main
git log --oneline -5
```
