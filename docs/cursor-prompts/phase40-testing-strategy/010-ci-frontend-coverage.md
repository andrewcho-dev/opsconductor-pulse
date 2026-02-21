# 010: Add Frontend Tests to CI Pipeline

## Why
Frontend tests are not in the CI pipeline. They run locally but not in GitHub Actions. This means broken frontend code can be merged to main without detection.

## What to Do

### Step 1: Add `test:ci` script to frontend/package.json

Read `frontend/package.json`. Add a script:
```json
"test:ci": "vitest run --reporter=junit --outputFile=../test-results/frontend.xml"
```

This runs tests once (not in watch mode) and outputs JUnit XML for CI reporting.

### Step 2: Add `frontend-tests` job to `.github/workflows/test.yml`

Read `.github/workflows/test.yml`. Add a new job between `unit-tests` and `integration-tests`:

```yaml
  frontend-tests:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run tests
        working-directory: frontend
        run: npm run test:ci

      - name: Run coverage
        working-directory: frontend
        run: npx vitest run --coverage --reporter=json --outputFile=../test-results/frontend-coverage.json

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: frontend-test-results
          path: test-results/frontend.xml

      - name: TypeScript type check
        working-directory: frontend
        run: npx tsc --noEmit

      - name: Lint check
        working-directory: frontend
        run: npx eslint src/ --max-warnings=0 || true
```

### Step 3: Add frontend-tests as a dependency for e2e-tests

In the `e2e-tests` job, add:
```yaml
  e2e-tests:
    needs: [unit-tests, frontend-tests]
```

This ensures frontend tests pass before E2E tests run.

### Step 4: Add frontend build check

Add a `frontend-build` job or step:
```yaml
      - name: Verify frontend builds
        working-directory: frontend
        run: npm run build
```

This catches TypeScript errors and build issues.

### Step 5: Vitest junit reporter

Vitest 4.0.18 has built-in junit support via `--reporter=junit`. No extra dependency needed.

If the `--reporter=junit` flag doesn't work, install the reporter:
```bash
cd frontend && npm install -D @vitest/junit-reporter
```

## Verify

Push to a branch and verify the GitHub Actions workflow runs the new `frontend-tests` job.

Locally:
```bash
cd frontend && npm run test:ci
```

Should output JUnit XML and exit 0.

## Current CI Structure (for reference)

The existing `.github/workflows/test.yml` has 5 jobs:
1. **unit-tests** — `pytest -m unit -v --tb=short --junitxml=test-results/unit.xml`
2. **integration-tests** — services: postgres:16, keycloak:24.0; runs coverage + `python scripts/check_coverage.py`
3. **e2e-tests** — Docker Compose full stack, Playwright Chromium
4. **lint** — ruff check + ruff format --check + mypy (non-blocking)
5. **benchmarks** — runs on main/push only after unit+integration pass

The new `frontend-tests` job should go between `unit-tests` and `integration-tests`.

## Reference Files
- `.github/workflows/test.yml` — current CI with 5 jobs
- `frontend/package.json` — current scripts: `test`, `test:ui`, `test:coverage`
- `frontend/vitest.config.ts` — jsdom env, setupTests.ts, coverage v8 provider
