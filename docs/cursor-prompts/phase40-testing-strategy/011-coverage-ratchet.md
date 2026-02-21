# 011: Coverage Ratchet — Thresholds + Enforcement

## Why
Coverage thresholds exist in `.coveragerc` (fail_under=60) and `scripts/check_coverage.py` (critical module thresholds) but are effectively disabled. `pytest.ini` has a comment saying "TODO: re-enable at 50%." Without enforcement, coverage will erode again. We need a ratchet mechanism: coverage can go up, never down.

## What to Do

### Step 1: Fix pytest.ini coverage conflict

Read `pytest.ini`. The current `addopts` line is:
```ini
addopts = -v --tb=short --strict-markers --cov=services/ui_iot --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=0
```

Remove `--cov-fail-under=0` from this line. This lets `.coveragerc`'s `fail_under` take effect as the single source of truth.

Updated `addopts` should be:
```ini
addopts = -v --tb=short --strict-markers --cov=services/ui_iot --cov-report=term-missing --cov-report=html --cov-report=xml
```

### Step 2: Update .coveragerc threshold

Read `.coveragerc`. Set:
```ini
fail_under = 50
```

Start at 50% (achievable after prompts 003-008 add ~157 tests). Ratchet up to 60% once stable, then 70%.

### Step 3: Expand critical module thresholds in check_coverage.py

Read `scripts/check_coverage.py`. The current `CRITICAL_MODULES` has these exact thresholds:
- `services/ui_iot/middleware/auth.py`: 85%
- `services/ui_iot/middleware/tenant.py`: 85%
- `services/ui_iot/db/pool.py`: 85%
- `services/ui_iot/utils/url_validator.py`: 80%
- `services/ui_iot/utils/snmp_validator.py`: 75%
- `services/ui_iot/utils/email_validator.py`: 70%

Update `CRITICAL_MODULES` to add newly tested modules:

```python
CRITICAL_MODULES = {
    # Existing (keep as-is)
    "services/ui_iot/middleware/auth.py": 85,
    "services/ui_iot/middleware/tenant.py": 85,
    "services/ui_iot/db/pool.py": 85,
    "services/ui_iot/utils/url_validator.py": 80,
    "services/ui_iot/utils/snmp_validator.py": 75,
    "services/ui_iot/utils/email_validator.py": 70,
    # New critical modules (add)
    "services/ui_iot/routes/customer.py": 50,
    "services/ui_iot/routes/operator.py": 40,
    "services/ui_iot/routes/system.py": 40,
    "services/ui_iot/routes/users.py": 40,
    "services/ui_iot/routes/ingest.py": 50,
    "services/ui_iot/services/alert_dispatcher.py": 50,
    "services/ui_iot/services/snmp_sender.py": 50,
    "services/ui_iot/services/keycloak_admin.py": 40,
    "services/ui_iot/services/subscription.py": 40,
}

OVERALL_MINIMUM = 50
```

Start thresholds conservatively. They should reflect what the new tests actually achieve (run coverage to check, then set thresholds 5% below actuals so they catch regressions without blocking normal work).

### Step 4: Add coverage ratchet script

Create `scripts/coverage_ratchet.py`:

This script:
1. Reads the current coverage from `coverage.xml`
2. Reads the last recorded coverage from `.coverage_baseline.json`
3. If any module's coverage decreased by more than 1%, fails
4. If overall coverage decreased, fails
5. On success, updates `.coverage_baseline.json` with current values

```python
#!/usr/bin/env python3
"""Coverage ratchet: prevent coverage from decreasing."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASELINE_FILE = Path(".coverage_baseline.json")
COVERAGE_XML = Path("coverage.xml")
TOLERANCE = 1.0  # Allow 1% fluctuation


def get_current_coverage() -> dict:
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()
    result = {"_overall": float(root.get("line-rate", 0)) * 100}
    for pkg in root.findall(".//package"):
        for cls in pkg.findall(".//class"):
            fn = cls.get("filename", "")
            result[fn] = float(cls.get("line-rate", 0)) * 100
    return result


def main():
    if not COVERAGE_XML.exists():
        print("No coverage.xml found. Run tests with coverage first.")
        sys.exit(1)

    current = get_current_coverage()

    if not BASELINE_FILE.exists():
        print("No baseline found. Creating initial baseline.")
        BASELINE_FILE.write_text(json.dumps(current, indent=2))
        sys.exit(0)

    baseline = json.loads(BASELINE_FILE.read_text())
    regressions = []

    for module, old_cov in baseline.items():
        new_cov = current.get(module, 0)
        if old_cov - new_cov > TOLERANCE:
            regressions.append(f"  {module}: {old_cov:.1f}% → {new_cov:.1f}% (dropped {old_cov - new_cov:.1f}%)")

    if regressions:
        print("Coverage regressions detected:")
        for r in regressions:
            print(r)
        print(f"\nBaseline: {BASELINE_FILE}")
        print("Fix the regressions or update the baseline with: python scripts/coverage_ratchet.py --update")
        sys.exit(1)

    # Update baseline with new (potentially higher) values
    if "--update" in sys.argv:
        BASELINE_FILE.write_text(json.dumps(current, indent=2))
        print(f"Baseline updated: {BASELINE_FILE}")
    else:
        # Auto-ratchet: if coverage increased, update baseline
        updated = False
        for module, new_cov in current.items():
            old_cov = baseline.get(module, 0)
            if new_cov > old_cov:
                baseline[module] = new_cov
                updated = True
        if updated:
            BASELINE_FILE.write_text(json.dumps(baseline, indent=2))

    overall = current.get("_overall", 0)
    print(f"Coverage check passed. Overall: {overall:.1f}%")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 5: Add ratchet to CI

In `.github/workflows/test.yml`, in the `integration-tests` job, after "Enforce coverage thresholds":

```yaml
      - name: Coverage ratchet check
        run: python scripts/coverage_ratchet.py
```

### Step 6: Add to pre-commit

Read `.pre-commit-config.yaml`. Current hooks:
1. `pytest-check` — runs `pytest -m unit --tb=short -q` on all commits
2. `ruff` — linter with `--fix`
3. `ruff-format` — formatter check

Add a frontend test hook to the `repo: local` section:

```yaml
      - id: frontend-tests
        name: Frontend tests
        entry: bash -c 'cd frontend && npm run test -- --run --reporter=dot'
        language: system
        pass_filenames: false
        files: '^frontend/src/.*\.(ts|tsx)$'
        stages: [commit]
```

This runs frontend tests only when frontend source files change.

### Step 7: Add .coverage_baseline.json to .gitignore exceptions

Add `.coverage_baseline.json` to version control (NOT gitignored). This is the shared baseline that all developers and CI use.

Generate the initial baseline:
```bash
pytest -m "not e2e" --cov=services/ui_iot --cov-report=xml -q
python scripts/coverage_ratchet.py --update
```

### Step 8: Add frontend coverage thresholds

Read `frontend/vitest.config.ts`. Add coverage thresholds:

```typescript
coverage: {
  provider: "v8",
  reporter: ["text", "json", "html"],
  exclude: ["node_modules/", "src/setupTests.ts"],
  thresholds: {
    statements: 20,
    branches: 15,
    functions: 20,
    lines: 20,
  },
},
```

Start low (20%). Ratchet up as tests are added. These thresholds will fail `vitest run --coverage` if not met.

## Verify

```bash
# Backend coverage check
pytest -m "not e2e" --cov=services/ui_iot --cov-report=xml -q
python scripts/check_coverage.py
python scripts/coverage_ratchet.py

# Frontend coverage check
cd frontend && npx vitest run --coverage && cd ..

# Pre-commit check
pre-commit run --all-files
```

## Reference Files
- `pytest.ini` — test config
- `.coveragerc` — coverage config
- `scripts/check_coverage.py` — critical module thresholds
- `.github/workflows/test.yml` — CI pipeline
- `.pre-commit-config.yaml` — pre-commit hooks
- `frontend/vitest.config.ts` — frontend test config
