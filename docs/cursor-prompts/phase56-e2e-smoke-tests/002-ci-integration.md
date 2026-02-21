# Prompt 002 — CI Integration

Read `.github/workflows/` to understand existing CI structure.
Read `tests/e2e/conftest.py` for the `RUN_E2E` env var gate.

## Add Smoke Test Job to CI

In the appropriate GitHub Actions workflow file (or create `.github/workflows/smoke.yml`):

```yaml
name: Smoke Tests

on:
  push:
    branches: [main]
  workflow_dispatch:  # allow manual trigger

jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Start compose stack
        run: docker compose up -d --wait
        timeout-minutes: 5

      - name: Wait for services healthy
        run: |
          for i in $(seq 1 30); do
            curl -sf http://localhost:8000/healthz && break
            echo "Waiting... $i"
            sleep 2
          done

      - name: Install Playwright
        run: |
          pip install pytest-playwright pytest-asyncio
          playwright install chromium

      - name: Run smoke tests
        env:
          RUN_E2E: "true"
          UI_BASE_URL: "http://localhost:8000"
          KEYCLOAK_URL: "http://localhost:8080"
          E2E_BASE_URL: "http://localhost:8000"
        run: pytest -m "e2e and smoke" -v --timeout=30 tests/e2e/test_smoke.py

      - name: Dump logs on failure
        if: failure()
        run: docker compose logs --tail=100
```

## pytest.ini / pyproject.toml Marker Registration

Add `smoke` marker to `pytest.ini` or `pyproject.toml` markers section:

```ini
[pytest]
markers =
    smoke: Smoke tests — fast, non-destructive, safe for any environment
```

(Only add if `pytest.ini` or `pyproject.toml` already registers markers — check first.)

## Acceptance Criteria

- [ ] CI workflow exists for smoke tests
- [ ] `smoke` marker registered in pytest config
- [ ] Workflow triggers on push to main and manual dispatch
- [ ] Dumps compose logs on failure for debugging
