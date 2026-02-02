# Task 006: Coverage Reporting

> **CURSOR: EXECUTE THIS TASK**
>
> This is an implementation task. Read the instructions below and implement them.
> Modify the files listed in "Files to Create/Modify" section.
> Follow the acceptance criteria to verify your work.
> Commit with the message in the "Commit" section when done.

---

## Context

We need to track test coverage to ensure adequate testing and prevent regressions. This includes coverage configuration, reporting, and enforcing minimum coverage thresholds.

**Read first**:
- `pytest.ini` (test configuration)
- `.github/workflows/test.yml` (CI pipeline)
- pytest-cov documentation

**Depends on**: Tasks 001-005

## Task

### 6.1 Configure pytest-cov

Update `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers --cov=services/ui_iot --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=70
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require database)
    e2e: End-to-end tests (require running services)
    slow: Slow tests (skip with -m "not slow")
filterwarnings =
    ignore::DeprecationWarning

[coverage:run]
source = services/ui_iot
omit =
    */tests/*
    */__pycache__/*
    */migrations/*
branch = True

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
show_missing = True
precision = 2

[coverage:html]
directory = htmlcov
```

### 6.2 Create .coveragerc file

Create `.coveragerc` in project root:

```ini
[run]
source = services/ui_iot
omit =
    */tests/*
    */__pycache__/*
    */migrations/*
    */.venv/*
branch = True
parallel = True

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
    @abc.abstractmethod
show_missing = True
precision = 2
fail_under = 70

[html]
directory = htmlcov
title = OpsConductor Pulse Coverage Report

[xml]
output = coverage.xml
```

### 6.3 Create coverage script

Create `scripts/coverage.sh`:

```bash
#!/bin/bash
set -e

# Run tests with coverage
pytest \
    --cov=services/ui_iot \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=xml \
    --cov-fail-under=70 \
    -m "not e2e" \
    "$@"

echo ""
echo "=========================================="
echo "Coverage report generated:"
echo "  - Terminal: above"
echo "  - HTML: htmlcov/index.html"
echo "  - XML: coverage.xml"
echo "=========================================="

# Open HTML report if on macOS/Linux with browser
if command -v open &> /dev/null; then
    echo "Opening HTML report..."
    open htmlcov/index.html
elif command -v xdg-open &> /dev/null; then
    echo "Opening HTML report..."
    xdg-open htmlcov/index.html
fi
```

### 6.4 Add gitignore entries

Add to `.gitignore`:

```
# Coverage
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
*.py,cover

# Test artifacts
.pytest_cache/
test-results/
```

### 6.5 Create coverage badge

Update CI workflow to generate coverage badge. Add to `.github/workflows/test.yml` after coverage upload:

```yaml
      - name: Generate coverage badge
        uses: schneegans/dynamic-badges-action@v1.7.0
        if: github.ref == 'refs/heads/main'
        with:
          auth: ${{ secrets.GIST_TOKEN }}
          gistID: YOUR_GIST_ID
          filename: coverage.json
          label: coverage
          message: ${{ steps.coverage.outputs.total }}%
          valColorRange: ${{ steps.coverage.outputs.total }}
          maxColorRange: 100
          minColorRange: 0
```

Or use Codecov badge (already in test.yml):

```markdown
[![codecov](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/OWNER/REPO)
```

### 6.6 Create minimum coverage requirements

Create `tests/coverage_requirements.md`:

```markdown
# Coverage Requirements

## Minimum Thresholds

| Component | Minimum Coverage |
|-----------|------------------|
| Overall | 70% |
| Critical paths | 90% |

## Critical Paths (require 90%+)

These modules handle security and tenant isolation:

- `services/ui_iot/middleware/auth.py`
- `services/ui_iot/middleware/tenant.py`
- `services/ui_iot/db/pool.py`
- `services/ui_iot/utils/url_validator.py`

## Exemptions

These files are excluded from coverage:

- `*/migrations/*` - Database migrations
- `*/tests/*` - Test files themselves
- `*/__pycache__/*` - Compiled Python

## Enforcement

- CI fails if coverage drops below 70%
- PRs must not decrease coverage
- New code must have tests
```

### 6.7 Add coverage check to pre-commit (optional)

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest
        entry: pytest -m unit --tb=short -q
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 6.8 Create coverage enforcement script

Create `scripts/check_coverage.py`:

```python
#!/usr/bin/env python3
"""Check coverage for critical modules."""

import subprocess
import sys
import xml.etree.ElementTree as ET

CRITICAL_MODULES = {
    "services/ui_iot/middleware/auth.py": 90,
    "services/ui_iot/middleware/tenant.py": 90,
    "services/ui_iot/db/pool.py": 85,
    "services/ui_iot/utils/url_validator.py": 90,
}

OVERALL_MINIMUM = 70


def get_coverage_from_xml(xml_path: str) -> dict:
    """Parse coverage.xml and return per-file coverage."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    coverage = {}
    for package in root.findall(".//package"):
        for cls in package.findall(".//class"):
            filename = cls.get("filename")
            line_rate = float(cls.get("line-rate", 0)) * 100
            coverage[filename] = line_rate

    return coverage


def main():
    # Run pytest with coverage
    result = subprocess.run(
        ["pytest", "-m", "not e2e", "--cov=services/ui_iot", "--cov-report=xml", "-q"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Tests failed!")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)

    # Parse coverage
    coverage = get_coverage_from_xml("coverage.xml")

    # Check critical modules
    failed = False
    for module, minimum in CRITICAL_MODULES.items():
        actual = coverage.get(module, 0)
        status = "✓" if actual >= minimum else "✗"
        print(f"{status} {module}: {actual:.1f}% (minimum: {minimum}%)")
        if actual < minimum:
            failed = True

    # Check overall
    tree = ET.parse("coverage.xml")
    root = tree.getroot()
    overall = float(root.get("line-rate", 0)) * 100
    status = "✓" if overall >= OVERALL_MINIMUM else "✗"
    print(f"\n{status} Overall: {overall:.1f}% (minimum: {OVERALL_MINIMUM}%)")

    if overall < OVERALL_MINIMUM:
        failed = True

    if failed:
        print("\n❌ Coverage requirements not met!")
        sys.exit(1)
    else:
        print("\n✅ All coverage requirements met!")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

## Files to Create/Modify

| Action | Path |
|--------|------|
| MODIFY | `pytest.ini` |
| CREATE | `.coveragerc` |
| CREATE | `scripts/coverage.sh` |
| MODIFY | `.gitignore` |
| CREATE | `tests/coverage_requirements.md` |
| CREATE | `.pre-commit-config.yaml` (optional) |
| CREATE | `scripts/check_coverage.py` |

## Acceptance Criteria

- [ ] `pytest --cov` generates coverage report
- [ ] HTML report generated in `htmlcov/`
- [ ] XML report generated for CI
- [ ] Coverage fails if below 70%
- [ ] Coverage files ignored in git
- [ ] Critical modules have higher thresholds
- [ ] Coverage script runs correctly

**Test**:
```bash
chmod +x scripts/coverage.sh
chmod +x scripts/check_coverage.py

# Run coverage
./scripts/coverage.sh

# Check critical modules
python scripts/check_coverage.py

# View HTML report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Commit

```
Add coverage reporting and enforcement

- pytest-cov configuration in pytest.ini
- .coveragerc with thresholds and exclusions
- Coverage script for local development
- Critical module coverage requirements (90%)
- Overall coverage minimum (70%)
- Pre-commit hooks for tests and linting
- Coverage check script for CI

Part of Phase 3.5: Testing Infrastructure
```
