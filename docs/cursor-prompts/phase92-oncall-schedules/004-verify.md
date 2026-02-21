# Phase 92 — Verify, Commit, Push

## Step 1: Apply migration
```bash
psql "$DATABASE_URL" -f db/migrations/069_oncall_schedules.sql
```

## Step 2: Dockerfile check ⚠️
Phase 92 adds `services/ui_iot/oncall/` — a new top-level package.
Open `services/ui_iot/Dockerfile` and confirm this line exists:
```
COPY oncall /app/oncall
```
If it is missing, add it alongside the other `COPY` lines before `RUN pip install`.
Missing this causes `ModuleNotFoundError` on container startup.

## Step 3: Rebuild backend
```bash
docker compose build ui && docker compose up -d ui
```

## Step 3: Build frontend
```bash
cd frontend && npm run build 2>&1 | tail -20
```
Must exit 0.

## Step 4: Backend smoke tests
```bash
# List schedules (expect 200 + empty list)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://localhost/customer/oncall-schedules | jq .

# Create a schedule with one layer
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Engineering Primary",
    "timezone": "UTC",
    "layers": [{
      "name": "Primary",
      "rotation_type": "weekly",
      "handoff_day": 1,
      "handoff_hour": 9,
      "responders": ["alice@example.com", "bob@example.com"]
    }]
  }' \
  https://localhost/customer/oncall-schedules | jq .schedule_id

# Get current on-call
SCHED_ID=1  # replace with actual id from above
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/oncall-schedules/${SCHED_ID}/current" | jq .

# Get 14-day timeline
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/oncall-schedules/${SCHED_ID}/timeline?days=14" | jq '.slots | length'
```

## Step 5: Frontend smoke check
- Navigate to `/oncall` — page renders with empty schedule list
- Click "New Schedule" — modal opens with timezone selector + layer builder
- Add 2 responders to a layer → arrows reorder them
- Save → schedule card appears with "Now on-call: alice@..."
- Click "View" → timeline renders with colored shift blocks
- Add Override → amber block appears in timeline

## Step 6: Commit and push
```bash
git add -A
git commit -m "feat: phase 92 - on-call schedules (rotation layers, overrides, timeline, escalation link)"
git push origin main
git log --oneline -5
```
