# Rebuild and Redeploy Frontend

The fix for the 422 (limit 500→200) is committed but the browser is still
serving the old compiled bundle. Rebuild and redeploy.

## Step 1: Rebuild frontend
```bash
cd frontend && npm run build
```

## Step 2: Copy build artifacts to served location
Check how the SPA is served. Look for one of these patterns:

```bash
# Option A: Docker volume / nginx serving dist/
ls frontend/dist/

# Option B: Served from a specific static path
grep -r "dist\|static\|build" docker-compose.yml | grep -i volume
```

Then either:
```bash
# If served via nginx container that mounts dist/:
docker compose restart nginx
# or
docker compose restart ui_iot  # if ui_iot serves static files directly
```

## Step 3: Hard refresh browser
In the browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac) to bypass cache.

## Step 4: Verify
Check browser network tab — the new JS bundle filename will have changed
(different hash, e.g. `index-XXXXXXXX.js`).

Confirm `GET /customer/alerts?status=OPEN&limit=200` (not 500) in network tab.
