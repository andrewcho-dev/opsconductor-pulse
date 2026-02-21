# Phase 88 — Verify, Commit, Push

## Step 1: Apply migration
```bash
psql "$DATABASE_URL" -f db/migrations/066_escalation_policies.sql
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

## Step 4: Backend smoke test
```bash
# List policies (expect 200 with empty list)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://localhost/customer/escalation-policies | jq .

# Create a policy
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Default Policy","is_default":true,"levels":[{"level_number":1,"delay_minutes":15,"notify_email":"ops@example.com"}]}' \
  https://localhost/customer/escalation-policies | jq .policy_id
```

## Step 5: Frontend smoke check
- Navigate to `/escalation-policies` — page renders with empty table
- Click "New Policy" — modal opens
- Add 2 levels, save — policy appears in table

## Step 6: Commit and push
```bash
git add -A
git commit -m "feat: phase 88 - alert escalation policies (migration, CRUD, worker, UI)"
git push origin main
git log --oneline -5
```
