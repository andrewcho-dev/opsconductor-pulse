# 006 — Fix CI/CD Pipelines

## Context

CI pipelines silently swallow failures and have stale references. This prompt fixes `.github/workflows/test.yml` and `.github/workflows/smoke.yml`.

---

## 6a — ESLint: remove `|| true`

**File**: `.github/workflows/test.yml`, line 77

### Before:
```yaml
      - name: Lint check
        working-directory: frontend
        run: npx eslint src/ --max-warnings=0 || true
```

### After:
```yaml
      - name: Lint check
        working-directory: frontend
        run: npx eslint src/ --max-warnings=0
```

---

## 6b — Remove stale frontend test artifact upload

**File**: `.github/workflows/test.yml`, lines 79-84

Delete this entire step (Vitest outputs JSON, not JUnit XML — the referenced `test-results/frontend.xml` is never created):

```yaml
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: frontend-test-results
          path: test-results/frontend.xml
```

Keep the next step (lines 86-91, `Upload frontend coverage`) — that one references the correct JSON file.

---

## 6c — Migration runner: remove `|| true` (two locations)

### Location 1: integration-tests job (lines 152-156)

**Before:**
```yaml
      - name: Run database migrations
        run: |
          for f in db/migrations/*.sql; do
            PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud_test -f "$f" || true
          done
```

**After:**
```yaml
      - name: Run database migrations
        run: |
          for f in db/migrations/*.sql; do
            PGPASSWORD=iot_dev psql -h localhost -U iot -d iotcloud_test -f "$f"
          done
```

### Location 2: benchmarks job (lines 347-351)

Same change — remove `|| true` from the `psql` line.

---

## 6d — E2E health check: use `/healthz`

**File**: `.github/workflows/test.yml`, line 217

### Before:
```yaml
            curl -sf http://localhost:8080/login && break
```

### After:
```yaml
            curl -sf http://localhost:8080/healthz && break
```

---

## 6e — E2E compose startup: use `--wait` and absolute path

**File**: `.github/workflows/test.yml`, lines 207-211

### Before:
```yaml
      - name: Start services
        run: |
          cd compose
          docker compose up -d
          cd ..
```

### After:
```yaml
      - name: Start services
        run: docker compose -f compose/docker-compose.yml up -d --wait
```

### Also fix cleanup step (lines 264-269):

**Before:**
```yaml
      - name: Cleanup
        if: always()
        run: |
          cd compose
          docker compose down -v
          cd ..
```

**After:**
```yaml
      - name: Cleanup
        if: always()
        run: docker compose -f compose/docker-compose.yml down -v
```

### Also fix the log collection step (lines 249-255):

**Before:**
```yaml
      - name: Collect container logs on failure
        if: failure()
        run: |
          cd compose
          docker compose logs ui > ../test-results/ui.log 2>&1
          docker compose logs keycloak > ../test-results/keycloak.log 2>&1
          cd ..
```

**After:**
```yaml
      - name: Collect container logs on failure
        if: failure()
        run: |
          docker compose -f compose/docker-compose.yml logs ui > test-results/ui.log 2>&1
          docker compose -f compose/docker-compose.yml logs keycloak > test-results/keycloak.log 2>&1
```

---

## 6f — Smoke workflow: add required env vars

**File**: `.github/workflows/smoke.yml`, lines 26-28

### Before:
```yaml
      - name: Start compose stack
        run: docker compose -f compose/docker-compose.yml up -d --wait
        timeout-minutes: 5
```

### After:
```yaml
      - name: Start compose stack
        run: docker compose -f compose/docker-compose.yml up -d --wait
        timeout-minutes: 5
        env:
          POSTGRES_PASSWORD: iot_dev
          PG_PASS: iot_dev
          KEYCLOAK_ADMIN_PASSWORD: admin_dev
          KEYCLOAK_CLIENT_SECRET: test-secret
          MQTT_ADMIN_PASSWORD: test-mqtt
```

---

## Commit

```bash
git add .github/workflows/test.yml .github/workflows/smoke.yml
git commit -m "fix: remove CI silent failures, fix E2E compose paths, add smoke env vars"
```

## Verification

```bash
# Only mypy should have || true
grep "|| true" .github/workflows/test.yml
# Should show only the mypy line (~line 292)

# Smoke has env vars
grep -A 5 "POSTGRES_PASSWORD" .github/workflows/smoke.yml

# No cd compose pattern remains
grep "cd compose" .github/workflows/test.yml
# Should return nothing
```
