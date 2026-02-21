# Task 4: Make MyPy Blocking in CI

## Context

`.github/workflows/test.yml` line ~344 runs:
```yaml
run: mypy services/ || true
```

The `|| true` means type errors are reported but never fail the build. This renders MyPy meaningless as a quality gate — developers see warnings but have no incentive to fix them.

## Actions

1. Read `.github/workflows/test.yml` in full.

2. Run MyPy locally (or review its output if available) to understand the current state:
   ```bash
   mypy services/ 2>&1 | tail -20
   ```
   This tells you how many errors exist today.

3. If the error count is large (>50), do NOT just remove `|| true` — that would immediately break the build for unrelated work. Instead:

   **Option A (preferred if error count is manageable, <50):**
   - Remove `|| true`.
   - Fix any errors that are blocking.

   **Option B (if error count is large):**
   - Create a `mypy-baseline.txt` by running:
     ```bash
     mypy services/ 2>&1 > mypy-baseline.txt
     ```
   - Add a CI step that:
     1. Runs mypy and captures output.
     2. Compares new errors against baseline.
     3. Fails if the error count increases above baseline.
   - This prevents regression without requiring all existing errors to be fixed first.

4. If Option B: Add a script `scripts/check_mypy_baseline.py` that:
   - Runs `mypy services/`
   - Reads `mypy-baseline.txt`
   - Counts new errors not in baseline
   - Exits non-zero if new errors were introduced

5. Update `test.yml` to use the baseline checker instead of `|| true`.

6. Add `mypy-baseline.txt` to version control so it's tracked.

## Verification

```bash
# No || true on mypy
grep 'mypy' .github/workflows/test.yml | grep '|| true'
# Must return zero results
```
