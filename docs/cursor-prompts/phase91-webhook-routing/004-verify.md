# Phase 91 — Verify, Commit, Push

## Step 1: Apply migration
```bash
psql "$DATABASE_URL" -f db/migrations/068_notification_channels.sql
```

## Step 2: Dockerfile check ⚠️
Phase 91 adds `services/ui_iot/notifications/` — a new top-level package.
Open `services/ui_iot/Dockerfile` and confirm this line exists:
```
COPY notifications /app/notifications
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
# List channels (expect 200 + empty list)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://localhost/customer/notification-channels | jq .

# Create a Slack channel
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Slack","channel_type":"slack","config":{"webhook_url":"https://hooks.slack.com/test"},"is_enabled":true}' \
  https://localhost/customer/notification-channels | jq .channel_id

# Test the channel (will fail with network error since URL is fake — that's OK)
CHANNEL_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
  https://localhost/customer/notification-channels | jq '.[0].channel_id')
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "https://localhost/customer/notification-channels/${CHANNEL_ID}/test" | jq .
```

## Step 5: Frontend smoke check
- Navigate to `/notifications` — page renders with empty channels table
- Click "Add Channel" → modal opens with type selector
- Select "Slack" → webhook URL field appears
- Select "Webhook" → URL, method, headers, secret fields appear
- Save → channel appears in table with "Test" button

## Step 6: Commit and push
```bash
git add -A
git commit -m "feat: phase 91 - webhook routing (Slack, PagerDuty, Teams, HTTP + routing rules)"
git push origin main
git log --oneline -5
```
