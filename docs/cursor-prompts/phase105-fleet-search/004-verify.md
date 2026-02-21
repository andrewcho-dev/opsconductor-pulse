# Phase 105 — Verify Fleet Search

## Step 1: Indexes applied

```bash
docker exec iot-postgres psql -U iot iotcloud -c \
  "SELECT indexname FROM pg_indexes WHERE tablename = 'device_state' ORDER BY indexname;"
```

Expected: `idx_device_state_search_vector`, `idx_device_state_tags_gin`,
`idx_device_state_site_id`, `idx_device_state_status` all present.

## Step 2: Search by name returns results

```bash
# Replace "sensor" with a substring of an actual device name in your DB
curl -s "http://localhost:8000/customer/devices?search=sensor" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'devices returned: {len(d) if isinstance(d,list) else d.get(\"total\",\"?\")}')
```

## Step 3: Status filter

```bash
curl -s "http://localhost:8000/customer/devices?status=online" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -10
```

All returned devices should have `"status": "online"`.

## Step 4: Combined filter

```bash
curl -s "http://localhost:8000/customer/devices?status=online&search=temp" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -10
```

## Step 5: Empty search returns all (up to limit)

```bash
curl -s "http://localhost:8000/customer/devices?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -10
```

## Step 6: Frontend build

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

## Step 7: Commit

```bash
git add \
  db/migrations/075_device_search_indexes.sql \
  services/ui_iot/routes/devices.py \
  frontend/src/

git commit -m "feat: fleet device search — server-side filtering + search indexes

- Migration 075: GIN indexes on tags, tsvector search on name+device_id,
  btree indexes on status and site_id
- GET /customer/devices: search, status, site_id, tag, limit, offset params
- Frontend: search bar + status filter above device table with debounce"

git push origin main
git log --oneline -3
```

## Definition of Done

- [ ] Migration 075 applied: all 4 indexes exist
- [ ] `GET /customer/devices?search=<term>` returns matching devices only
- [ ] `GET /customer/devices?status=online` returns only online devices
- [ ] Frontend shows search bar above device table
- [ ] Clearing filters restores full list
- [ ] Frontend build passes
